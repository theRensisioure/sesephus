const std = @import("std");
const builtin = @import("builtin");

pub const Role = enum { host, client };

pub const Config = struct {
    role: Role = .client,
    last_host: []const u8 = "127.0.0.1",
    last_port: u16 = 5000,
    embed_local_client: bool = false,
    configured_at: []const u8 = "",

    pub fn deinit(self: *Config, allocator: std.mem.Allocator) void {
        if (self.last_host.len > 0 and !std.mem.eql(u8, self.last_host, "127.0.0.1")) {
            allocator.free(self.last_host);
        }
        if (self.configured_at.len > 0) {
            allocator.free(self.configured_at);
        }
    }
};

const StoredConfig = struct {
    role: ?[]const u8 = null,
    last_host: ?[]const u8 = null,
    last_port: ?u16 = null,
    embed_local_client: ?bool = null,
    configured_at: ?[]const u8 = null,
};

const is_windows = builtin.os.tag == .windows;
const sep = if (is_windows) "\\" else "/";
// Must match ssfs/drive-mapping.json coldArchive.letter + paths.archiveRoot on
// Windows. On POSIX there is no cold-archive drive, so use a writable absolute
// path; the resolveWritableDir/fallback logic still applies as designed.
const primary_config_dir = if (is_windows) "E:\\Archive\\sesefhus\\config" else "/var/tmp/sesefus/config";

fn primaryConfigDir(io: std.Io) ![]const u8 {
    return try resolveWritableDir(io, primary_config_dir);
}

fn fallbackConfigDir(allocator: std.mem.Allocator) ![]const u8 {
    return try allocator.dupe(u8, ".sesefus" ++ sep ++ "config");
}

fn resolveWritableDir(io: std.Io, path: []const u8) ![]const u8 {
    const dirname = std.fs.path.dirname(path) orelse path;
    if (dirname.len > 0) {
        std.Io.Dir.cwd().createDirPath(io, dirname) catch {};
    }
    const probe = try std.fmt.allocPrint(std.heap.page_allocator, "{s}" ++ sep ++ "sesefus_probe.tmp", .{dirname});
    defer std.heap.page_allocator.free(probe);
    _ = std.Io.Dir.createFileAbsolute(io, probe, .{ .read = true }) catch {
        return error.PathInaccessible;
    };
    std.Io.Dir.deleteFileAbsolute(io, probe) catch {};
    return path;
}

pub fn configPath(allocator: std.mem.Allocator, io: std.Io) ![]const u8 {
    const primary = primaryConfigDir(io) catch {
        return fallbackConfigDir(allocator);
    };
    return try std.fmt.allocPrint(allocator, "{s}" ++ sep ++ "runtime.json", .{primary});
}

pub fn load(allocator: std.mem.Allocator, io: std.Io) !?Config {
    // Read path is probe-free: loading config must never write outside the
    // project (resolveWritableDir creates dirs + a probe file, so it is only
    // used when saving). It must still agree with save()/deleteConfig(),
    // which pick the primary only when it is writable — so open the primary
    // read_write (no truncate, nothing written) as a side-effect-free
    // writability check. A readable-but-unwritable primary (e.g. E: mounted
    // read-only) is skipped instead of permanently shadowing the fallback
    // file that saves actually write. Then try the cwd fallback.
    const file = std.Io.Dir.openFileAbsolute(io, primary_config_dir ++ sep ++ "runtime.json", .{ .mode = .read_write }) catch blk: {
        const fallback_dir = try fallbackConfigDir(allocator);
        defer allocator.free(fallback_dir);
        const fallback_path = try std.fmt.allocPrint(allocator, "{s}" ++ sep ++ "runtime.json", .{fallback_dir});
        defer allocator.free(fallback_path);
        break :blk std.Io.Dir.cwd().openFile(io, fallback_path, .{ .mode = .read_only }) catch return null;
    };
    defer file.close(io);

    var read_buf: [4096]u8 = undefined;
    var reader = file.reader(io, &read_buf);
    const data = try reader.interface.allocRemaining(allocator, .unlimited);
    defer allocator.free(data);

    const parsed = try std.json.parseFromSlice(StoredConfig, allocator, data, .{ .ignore_unknown_fields = true });
    defer parsed.deinit();

    var cfg = Config{};
    if (parsed.value.role) |r| {
        if (std.mem.eql(u8, r, "host")) cfg.role = .host;
    }
    if (parsed.value.last_host) |h| {
        cfg.last_host = try allocator.dupe(u8, h);
    }
    if (parsed.value.last_port) |p| cfg.last_port = p;
    if (parsed.value.embed_local_client) |e| cfg.embed_local_client = e;
    if (parsed.value.configured_at) |t| {
        cfg.configured_at = try allocator.dupe(u8, t);
    }
    return cfg;
}

pub fn save(cfg: Config, allocator: std.mem.Allocator, io: std.Io) !void {
    const config_dir_owned = try fallbackConfigDir(allocator);
    defer allocator.free(config_dir_owned);

    const config_dir = primaryConfigDir(io) catch config_dir_owned;
    std.Io.Dir.cwd().createDirPath(io, config_dir) catch {};

    const path = try std.fmt.allocPrint(allocator, "{s}" ++ sep ++ "runtime.json", .{config_dir});
    defer allocator.free(path);

    const role_str: []const u8 = if (cfg.role == .host) "host" else "client";
    var body = std.ArrayList(u8).empty;
    defer body.deinit(allocator);
    var aw: std.Io.Writer.Allocating = .fromArrayList(allocator, &body);
    try aw.writer.print(
        \\{{"role":"{s}","last_host":"{s}","last_port":{d},"embed_local_client":{s},"configured_at":"{s}"}}
    , .{
        role_str,
        cfg.last_host,
        cfg.last_port,
        if (cfg.embed_local_client) "true" else "false",
        if (cfg.configured_at.len > 0) cfg.configured_at else "unset",
    });
    body = aw.toArrayList();

    const file = try std.Io.Dir.createFileAbsolute(io, path, .{ .truncate = true });
    defer file.close(io);
    try file.writeStreamingAll(io, body.items);
}

pub fn promptAndSave(allocator: std.mem.Allocator, io: std.Io) !Config {
    const stdout = std.Io.File.stdout();
    try stdout.writeStreamingAll(io, "\nFirst run — select Sesefus role:\n  [H] Host daemon (vault + alarms)\n  [C] Client (scan LAN for hosts)\nChoice [H/C] (default C): ");

    const stdin = std.Io.File.stdin();
    var buf: [64]u8 = undefined;
    var reader = stdin.reader(io, &buf);
    const line = (try reader.interface.takeDelimiter('\n')) orelse "";

    var cfg = Config{
        .role = .client,
        .last_host = "127.0.0.1",
        .last_port = 5000,
        .embed_local_client = false,
        .configured_at = "first-run",
    };

    const trimmed = std.mem.trim(u8, line, "\r\n ");
    if (trimmed.len > 0 and (trimmed[0] == 'H' or trimmed[0] == 'h')) {
        cfg.role = .host;
        cfg.embed_local_client = true;
    }

    try save(cfg, allocator, io);
    return cfg;
}

pub fn deleteConfig(allocator: std.mem.Allocator, io: std.Io) void {
    const path = configPath(allocator, io) catch return;
    defer allocator.free(path);
    std.Io.Dir.deleteFileAbsolute(io, path) catch {};
}