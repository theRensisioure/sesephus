// sesefus-record — minimal C++ record widget daemon
// Speed needs: human scale (ingest Voice Recorder m4a, prefix lookup). Not HPC.
// SHA-256 full + prefix fractions (8/16/32 hex) for expedited retrieval + dedupe.
// Active index: on disk the moment a file is hashed. No alarms.

#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <bcrypt.h>

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "ws2_32.lib")

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
// config
// ---------------------------------------------------------------------------
static const int kPort = 8778;
static const char* kStatusActive = "active";

static fs::path exe_dir() {
  wchar_t buf[MAX_PATH];
  DWORD n = GetModuleFileNameW(nullptr, buf, MAX_PATH);
  if (!n || n >= MAX_PATH) return fs::current_path();
  return fs::path(buf).parent_path();
}

static fs::path default_sound_dir() {
  wchar_t profile[MAX_PATH];
  DWORD n = GetEnvironmentVariableW(L"USERPROFILE", profile, MAX_PATH);
  if (!n) return fs::path();
  return fs::path(profile) / L"Documents" / L"Sound Recordings";
}

static fs::path data_dir() {
  // Prefer %LOCALAPPDATA%\SesefusRecord for writable index
  wchar_t local[MAX_PATH];
  if (GetEnvironmentVariableW(L"LOCALAPPDATA", local, MAX_PATH)) {
    fs::path p = fs::path(local) / L"SesefusRecord";
    std::error_code ec;
    fs::create_directories(p, ec);
    return p;
  }
  fs::path p = exe_dir() / "data";
  std::error_code ec;
  fs::create_directories(p, ec);
  return p;
}

// ---------------------------------------------------------------------------
// sha256 via BCrypt
// ---------------------------------------------------------------------------
static std::string to_hex(const unsigned char* data, size_t len) {
  static const char* kHex = "0123456789abcdef";
  std::string out;
  out.resize(len * 2);
  for (size_t i = 0; i < len; ++i) {
    out[i * 2] = kHex[(data[i] >> 4) & 0xF];
    out[i * 2 + 1] = kHex[data[i] & 0xF];
  }
  return out;
}

static bool sha256_file(const fs::path& path, std::string& out_hex) {
  BCRYPT_ALG_HANDLE alg = nullptr;
  BCRYPT_HASH_HANDLE hash = nullptr;
  NTSTATUS st =
      BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0);
  if (st < 0) return false;

  DWORD obj_len = 0, cb = 0, hash_len = 0;
  st = BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&obj_len, sizeof(obj_len),
                         &cb, 0);
  if (st < 0) {
    BCryptCloseAlgorithmProvider(alg, 0);
    return false;
  }
  st = BCryptGetProperty(alg, BCRYPT_HASH_LENGTH, (PUCHAR)&hash_len, sizeof(hash_len),
                         &cb, 0);
  if (st < 0) {
    BCryptCloseAlgorithmProvider(alg, 0);
    return false;
  }

  std::vector<UCHAR> obj(obj_len);
  std::vector<UCHAR> digest(hash_len);
  st = BCryptCreateHash(alg, &hash, obj.data(), obj_len, nullptr, 0, 0);
  if (st < 0) {
    BCryptCloseAlgorithmProvider(alg, 0);
    return false;
  }

  std::ifstream in(path, std::ios::binary);
  if (!in) {
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);
    return false;
  }
  char buf[1 << 16];
  while (in) {
    in.read(buf, sizeof(buf));
    std::streamsize got = in.gcount();
    if (got > 0) {
      st = BCryptHashData(hash, (PUCHAR)buf, (ULONG)got, 0);
      if (st < 0) {
        BCryptDestroyHash(hash);
        BCryptCloseAlgorithmProvider(alg, 0);
        return false;
      }
    }
  }

  st = BCryptFinishHash(hash, digest.data(), hash_len, 0);
  BCryptDestroyHash(hash);
  BCryptCloseAlgorithmProvider(alg, 0);
  if (st < 0) return false;

  out_hex = to_hex(digest.data(), digest.size());
  return true;
}

// ---------------------------------------------------------------------------
// active index
// ---------------------------------------------------------------------------
struct Rec {
  std::string id;
  std::string sha256;
  std::string sha8;
  std::string sha16;
  std::string sha32;
  uint64_t size = 0;
  int64_t mtime = 0;
  std::string path;
  std::string status;
  std::string ingested_at;
};

struct Index {
  std::mutex mu;
  std::vector<Rec> rows;
  std::unordered_map<std::string, size_t> by_sha;
  std::unordered_map<std::string, size_t> by_sha8;
  std::unordered_map<std::string, size_t> by_sha16;
  std::unordered_map<std::string, size_t> by_sha32;
  fs::path store_path;

  void reindex() {
    by_sha.clear();
    by_sha8.clear();
    by_sha16.clear();
    by_sha32.clear();
    for (size_t i = 0; i < rows.size(); ++i) {
      by_sha[rows[i].sha256] = i;
      by_sha8[rows[i].sha8] = i;
      by_sha16[rows[i].sha16] = i;
      by_sha32[rows[i].sha32] = i;
    }
  }

  static std::string now_iso() {
    using namespace std::chrono;
    auto t = system_clock::now();
    std::time_t tt = system_clock::to_time_t(t);
    std::tm tm{};
    localtime_s(&tm, &tt);
    char buf[32];
    std::snprintf(buf, sizeof(buf), "%04d-%02d-%02dT%02d:%02d:%02d", tm.tm_year + 1900,
                  tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
    return buf;
  }

  bool load(const fs::path& p) {
    store_path = p;
    rows.clear();
    std::ifstream in(p);
    if (!in) {
      reindex();
      return true; // empty ok
    }
    std::string line;
    while (std::getline(in, line)) {
      if (line.empty() || line[0] == '#') continue;
      // id|sha256|sha8|sha16|sha32|size|mtime|status|ingested|path
      Rec r;
      std::stringstream ss(line);
      std::string size_s, mtime_s;
      if (!std::getline(ss, r.id, '|')) continue;
      if (!std::getline(ss, r.sha256, '|')) continue;
      if (!std::getline(ss, r.sha8, '|')) continue;
      if (!std::getline(ss, r.sha16, '|')) continue;
      if (!std::getline(ss, r.sha32, '|')) continue;
      if (!std::getline(ss, size_s, '|')) continue;
      if (!std::getline(ss, mtime_s, '|')) continue;
      if (!std::getline(ss, r.status, '|')) continue;
      if (!std::getline(ss, r.ingested_at, '|')) continue;
      std::getline(ss, r.path); // rest
      try {
        r.size = std::stoull(size_s);
        r.mtime = std::stoll(mtime_s);
      } catch (...) {
        continue;
      }
      rows.push_back(std::move(r));
    }
    reindex();
    return true;
  }

  bool save() const {
    std::ofstream out(store_path, std::ios::trunc);
    if (!out) return false;
    out << "# sesefus-record active index | grain=file sha prefixes for lookup\n";
    for (const auto& r : rows) {
      out << r.id << '|' << r.sha256 << '|' << r.sha8 << '|' << r.sha16 << '|'
          << r.sha32 << '|' << r.size << '|' << r.mtime << '|' << r.status << '|'
          << r.ingested_at << '|' << r.path << '\n';
    }
    return true;
  }

  // returns true if new or updated
  bool upsert_file(const fs::path& file) {
    std::error_code ec;
    if (!fs::is_regular_file(file, ec)) return false;
    auto ext = file.extension().string();
    for (char& c : ext) c = (char)tolower((unsigned char)c);
    if (ext != ".m4a" && ext != ".wav" && ext != ".mp3" && ext != ".ogg") return false;

    uint64_t size = (uint64_t)fs::file_size(file, ec);
    if (ec) return false;
    // file_clock ticks are enough for change-detect (not wall calendar)
    auto ftime = fs::last_write_time(file, ec);
    int64_t mtime = 0;
    if (!ec) {
      mtime = (int64_t)ftime.time_since_epoch().count();
    }

    std::string path_utf8 = file.string();
    // cheap skip: same path+size+mtime already hashed
    for (auto& r : rows) {
      if (r.path == path_utf8 && r.size == size && r.mtime == mtime) {
        return false;
      }
    }

    std::string sha;
    if (!sha256_file(file, sha) || sha.size() < 32) return false;

    Rec r;
    r.sha256 = sha;
    r.sha8 = sha.substr(0, 8);
    r.sha16 = sha.substr(0, 16);
    r.sha32 = sha.substr(0, 32);
    r.size = size;
    r.mtime = mtime;
    r.path = path_utf8;
    r.status = kStatusActive;
    r.ingested_at = now_iso();
    r.id = r.sha8 + "-" + std::to_string(size);

    auto it = by_sha.find(sha);
    if (it != by_sha.end()) {
      // same content: refresh path/status, stay active
      rows[it->second] = r;
    } else {
      rows.push_back(r);
    }
    reindex();
    save();
    return true;
  }

  int scan_dir(const fs::path& dir) {
    int n = 0;
    std::error_code ec;
    if (!fs::exists(dir, ec)) return 0;
    for (auto& ent : fs::directory_iterator(dir, ec)) {
      if (ec) break;
      if (!ent.is_regular_file(ec)) continue;
      if (upsert_file(ent.path())) ++n;
    }
    return n;
  }

  std::vector<const Rec*> lookup_prefix(const std::string& q) const {
    std::vector<const Rec*> out;
    std::string key = q;
    for (char& c : key) c = (char)tolower((unsigned char)c);
    // strip non-hex
    std::string hex;
    for (char c : key) {
      if ((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')) hex.push_back(c);
    }
    if (hex.empty()) return out;

    auto try_map = [&](const std::unordered_map<std::string, size_t>& m, const std::string& k) {
      auto it = m.find(k);
      if (it != m.end()) out.push_back(&rows[it->second]);
    };

    if (hex.size() >= 32) try_map(by_sha32, hex.substr(0, 32));
    if (hex.size() >= 16) try_map(by_sha16, hex.substr(0, 16));
    if (hex.size() >= 8) try_map(by_sha8, hex.substr(0, 8));

    // also scan prefix match on full sha if partial
    if (out.empty() && hex.size() >= 4) {
      for (const auto& r : rows) {
        if (r.sha256.compare(0, hex.size(), hex) == 0) out.push_back(&r);
      }
    }
    // dedupe
    std::sort(out.begin(), out.end());
    out.erase(std::unique(out.begin(), out.end()), out.end());
    return out;
  }
};

static Index g_index;
static fs::path g_sound_dir;
static std::mutex g_log_mu;

static void log_line(const std::string& s) {
  std::lock_guard<std::mutex> lock(g_log_mu);
  std::cout << s << std::endl;
}

// ---------------------------------------------------------------------------
// minimal HTTP
// ---------------------------------------------------------------------------
static std::string json_escape(const std::string& s) {
  std::string o;
  o.reserve(s.size() + 8);
  for (char c : s) {
    switch (c) {
      case '\\': o += "\\\\"; break;
      case '"': o += "\\\""; break;
      case '\n': o += "\\n"; break;
      case '\r': o += "\\r"; break;
      case '\t': o += "\\t"; break;
      default:
        if ((unsigned char)c < 0x20) {
          char b[8];
          std::snprintf(b, sizeof(b), "\\u%04x", (unsigned char)c);
          o += b;
        } else {
          o += c;
        }
    }
  }
  return o;
}

static std::string rec_json(const Rec& r) {
  std::ostringstream o;
  o << "{"
    << "\"id\":\"" << json_escape(r.id) << "\","
    << "\"sha256\":\"" << r.sha256 << "\","
    << "\"sha8\":\"" << r.sha8 << "\","
    << "\"sha16\":\"" << r.sha16 << "\","
    << "\"sha32\":\"" << r.sha32 << "\","
    << "\"size\":" << r.size << ","
    << "\"mtime\":" << r.mtime << ","
    << "\"status\":\"" << json_escape(r.status) << "\","
    << "\"ingested_at\":\"" << json_escape(r.ingested_at) << "\","
    << "\"path\":\"" << json_escape(r.path) << "\","
    << "\"name\":\"" << json_escape(fs::path(r.path).filename().string()) << "\""
    << "}";
  return o.str();
}

static std::string read_file_bin(const fs::path& p) {
  std::ifstream in(p, std::ios::binary);
  if (!in) return {};
  std::ostringstream ss;
  ss << in.rdbuf();
  return ss.str();
}

static void http_send(SOCKET c, int code, const char* ctype, const std::string& body) {
  std::ostringstream h;
  h << "HTTP/1.1 " << code << " OK\r\n"
    << "Content-Type: " << ctype << "\r\n"
    << "Content-Length: " << body.size() << "\r\n"
    << "Cache-Control: no-store\r\n"
    << "Access-Control-Allow-Origin: *\r\n"
    << "Connection: close\r\n\r\n";
  std::string hdr = h.str();
  send(c, hdr.data(), (int)hdr.size(), 0);
  if (!body.empty()) send(c, body.data(), (int)body.size(), 0);
}

static std::string url_decode(const std::string& s) {
  std::string o;
  for (size_t i = 0; i < s.size(); ++i) {
    if (s[i] == '%' && i + 2 < s.size()) {
      unsigned int v = 0;
      if (sscanf_s(s.c_str() + i + 1, "%2x", &v) == 1)
        o.push_back((char)v);
      i += 2;
    } else if (s[i] == '+') {
      o.push_back(' ');
    } else {
      o.push_back(s[i]);
    }
  }
  return o;
}

static std::string query_param(const std::string& q, const char* key) {
  std::string k = std::string(key) + "=";
  size_t p = q.find(k);
  if (p == std::string::npos) return {};
  p += k.size();
  size_t e = q.find('&', p);
  return url_decode(q.substr(p, e == std::string::npos ? std::string::npos : e - p));
}

static void handle_client(SOCKET c, const fs::path& ui_path) {
  char buf[8192];
  int n = recv(c, buf, sizeof(buf) - 1, 0);
  if (n <= 0) {
    closesocket(c);
    return;
  }
  buf[n] = 0;
  std::string req(buf);
  std::string method, target;
  {
    std::istringstream is(req);
    is >> method >> target;
  }
  std::string path = target;
  std::string query;
  auto qpos = target.find('?');
  if (qpos != std::string::npos) {
    path = target.substr(0, qpos);
    query = target.substr(qpos + 1);
  }

  if (method == "GET" && (path == "/" || path == "/index.html")) {
    std::string html = read_file_bin(ui_path);
    if (html.empty()) {
      http_send(c, 500, "text/plain", "ui missing");
    } else {
      http_send(c, 200, "text/html; charset=utf-8", html);
    }
  } else if (method == "GET" && path == "/api/status") {
    std::lock_guard<std::mutex> lock(g_index.mu);
    std::ostringstream o;
    o << "{\"ok\":true,"
      << "\"contract\":\"sesefus-record-cpp-v0\","
      << "\"port\":" << kPort << ","
      << "\"sound_dir\":\"" << json_escape(g_sound_dir.string()) << "\","
      << "\"index_path\":\"" << json_escape(g_index.store_path.string()) << "\","
      << "\"active_count\":" << g_index.rows.size() << ","
      << "\"note\":\"speed=human-scale; sha prefixes for lookup not HPC\""
      << "}";
    http_send(c, 200, "application/json; charset=utf-8", o.str());
  } else if (method == "GET" && path == "/api/recent") {
    std::lock_guard<std::mutex> lock(g_index.mu);
    std::ostringstream o;
    o << "{\"ok\":true,\"rows\":[";
    // newest first by mtime
    std::vector<size_t> order(g_index.rows.size());
    for (size_t i = 0; i < order.size(); ++i) order[i] = i;
    std::sort(order.begin(), order.end(), [&](size_t a, size_t b) {
      return g_index.rows[a].mtime > g_index.rows[b].mtime;
    });
    for (size_t i = 0; i < order.size(); ++i) {
      if (i) o << ',';
      o << rec_json(g_index.rows[order[i]]);
    }
    o << "]}";
    http_send(c, 200, "application/json; charset=utf-8", o.str());
  } else if (method == "GET" && path == "/api/by-prefix") {
    std::string q = query_param(query, "q");
    std::lock_guard<std::mutex> lock(g_index.mu);
    auto hits = g_index.lookup_prefix(q);
    std::ostringstream o;
    o << "{\"ok\":true,\"q\":\"" << json_escape(q) << "\",\"rows\":[";
    for (size_t i = 0; i < hits.size(); ++i) {
      if (i) o << ',';
      o << rec_json(*hits[i]);
    }
    o << "]}";
    http_send(c, 200, "application/json; charset=utf-8", o.str());
  } else if (method == "POST" && (path == "/api/scan" || path == "/api/ingest")) {
    int added = 0;
    {
      std::lock_guard<std::mutex> lock(g_index.mu);
      added = g_index.scan_dir(g_sound_dir);
    }
    std::ostringstream o;
    o << "{\"ok\":true,\"added_or_updated\":" << added << ",\"active_count\":"
      << g_index.rows.size() << "}";
    http_send(c, 200, "application/json; charset=utf-8", o.str());
  } else {
    http_send(c, 404, "text/plain", "not found");
  }
  closesocket(c);
}

static bool run_server(const fs::path& ui_path) {
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return false;

  SOCKET s = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
  if (s == INVALID_SOCKET) {
    WSACleanup();
    return false;
  }
  BOOL yes = 1;
  setsockopt(s, SOL_SOCKET, SO_REUSEADDR, (const char*)&yes, sizeof(yes));

  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons((u_short)kPort);
  inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);

  if (bind(s, (sockaddr*)&addr, sizeof(addr)) != 0) {
    log_line("bind failed — is port 8778 busy?");
    closesocket(s);
    WSACleanup();
    return false;
  }
  listen(s, 8);
  log_line(std::string("sesefus-record http://127.0.0.1:") + std::to_string(kPort) + "/");

  for (;;) {
    SOCKET c = accept(s, nullptr, nullptr);
    if (c == INVALID_SOCKET) continue;
    // sequential is fine at human scale
    handle_client(c, ui_path);
  }
}

// ---------------------------------------------------------------------------
// main
// ---------------------------------------------------------------------------
static void usage() {
  std::cout
      << "sesefus-record — C++ record widget daemon (no alarms)\n"
      << "  sesefus-record              scan + serve widget :8778\n"
      << "  sesefus-record scan         scan Sound Recordings only\n"
      << "  sesefus-record lookup HEX   prefix lookup (sha8/16/32)\n"
      << "  sesefus-record status\n";
}

int main(int argc, char** argv) {
  std::string cmd = (argc >= 2) ? argv[1] : "serve";

  g_sound_dir = default_sound_dir();
  fs::path idx = data_dir() / "active-index.txt";
  g_index.load(idx);

  fs::path ui = exe_dir() / "ui" / "index.html";
  if (!fs::exists(ui)) {
    // dev: relative to src layout
    ui = exe_dir() / ".." / "ui" / "index.html";
  }
  if (!fs::exists(ui)) {
    ui = fs::path("ui") / "index.html";
  }

  if (cmd == "-h" || cmd == "--help" || cmd == "help") {
    usage();
    return 0;
  }

  if (cmd == "status") {
    std::cout << "sound_dir=" << g_sound_dir.string() << "\n"
              << "index=" << idx.string() << "\n"
              << "active_count=" << g_index.rows.size() << "\n"
              << "speed_note=human-scale C++; prefixes for lookup not nanoseconds\n";
    return 0;
  }

  if (cmd == "scan") {
    int n = g_index.scan_dir(g_sound_dir);
    std::cout << "{\"ok\":true,\"added_or_updated\":" << n
              << ",\"active_count\":" << g_index.rows.size() << "}\n";
    return 0;
  }

  if (cmd == "lookup") {
    if (argc < 3) {
      std::cerr << "usage: sesefus-record lookup <hex-prefix>\n";
      return 1;
    }
    auto hits = g_index.lookup_prefix(argv[2]);
    std::cout << "{\"ok\":true,\"rows\":[";
    for (size_t i = 0; i < hits.size(); ++i) {
      if (i) std::cout << ',';
      std::cout << rec_json(*hits[i]);
    }
    std::cout << "]}\n";
    return 0;
  }

  // default: scan then serve
  int n = g_index.scan_dir(g_sound_dir);
  log_line(std::string("ingest: +") + std::to_string(n) +
           "  active=" + std::to_string(g_index.rows.size()) +
           "  dir=" + g_sound_dir.string());
  if (!fs::exists(ui)) {
    log_line("WARN ui missing: " + ui.string());
  }
  if (!run_server(ui)) return 1;
  return 0;
}
