#!/usr/bin/env python3
"""Sesefus alarm-daemon UI — BYO designated recorder + schedule (not scanner)."""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capture_config import (  # noqa: E402
    build_probe_rows,
    designate,
    designated_fields,
    filter_candidates,
    load_config,
    save_config,
    set_probed,
)
from hop_prefs import load_prefs, save_prefs  # noqa: E402
from inbox import land_new_from_designated, poll_inbox, spawn_cook  # noqa: E402
from launcher import enrich_audacity, launch_designated, present_check  # noqa: E402

HOME = Path(os.environ.get("USERPROFILE") or Path.home())
JOURNAL = HOME / "test-write" / "journal"
ARRAY_PATH = HOME / "jwrangle" / "durable-archive" / "you" / "raw-transcription" / "ARRAY.json"
MACROHARD_DIR = HOME / "jwrangle" / "tools" / "macrohard"
ALARMS = HERE / "alarms.json"
UI = HERE / "ui.html"
PID_FILE = HERE / ".ui-serve.pid"
DAEMON_PID = HERE / ".daemon.pid"
DEFAULT_PORT = 8777


def _ensure_macrohard() -> None:
    p = str(MACROHARD_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


def _fail_inputs(msg: object) -> dict:
    err = " ".join(str(msg).split())[:200] or "sounddevice is not installed"
    return {
        "ok": False,
        "error": err,
        "inputs": [],
        "picked": None,
        "keys_used": False,
        "network": False,
    }


def list_inputs(devices=None, hostapis=None, prefer: str = "", backend=None) -> dict:
    """Legal shared WASAPI/DirectSound inputs. Copy-call macrohard; no fake device."""
    _ensure_macrohard()
    try:
        from macrohard import legal_inputs, score_and_pick, slug_device_id
    except ImportError as e:
        return _fail_inputs(f"macrohard is not importable: {e}")

    if devices is None or hostapis is None:
        try:
            if backend is False:
                raise ImportError("sounddevice is not installed")
            if callable(backend):
                devices, hostapis = backend()
            else:
                import sounddevice as sd

                if devices is None:
                    devices = sd.query_devices()
                if hostapis is None:
                    hostapis = sd.query_hostapis()
        except ImportError:
            return _fail_inputs("sounddevice is not installed")
        except Exception as e:
            return _fail_inputs(e)

    rows_raw = legal_inputs(devices, hostapis)
    prefer_s = str(prefer or "").strip()
    if prefer_s and not any(prefer_s.lower() in str(r.get("name") or "").lower() for r in rows_raw):
        for r in rows_raw:
            slug = slug_device_id(r["name"], "")
            if slug == prefer_s.lower() or prefer_s.lower() in slug:
                prefer_s = r["name"]
                break
    rows = []
    for r in rows_raw:
        rows.append(
            {
                "index": r["index"],
                "name": r["name"],
                "hostapi": r["hostapi"],
                "device_id": slug_device_id(r["name"], prefer_s),
                "channels": r["channels"],
                "samplerate": r["samplerate"],
            }
        )
    picked = score_and_pick(rows_raw, prefer_s)
    return {
        "ok": True,
        "inputs": rows,
        "picked": picked,
        "keys_used": False,
        "network": False,
    }


def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    n = int(handler.headers.get("Content-Length") or 0)
    if n <= 0:
        return {}
    raw = handler.rfile.read(n)
    try:
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_alarms() -> list:
    if not ALARMS.is_file():
        return []
    try:
        data = json.loads(ALARMS.read_text(encoding="utf-8"))
        return list(data.get("windows") or [])
    except (OSError, json.JSONDecodeError):
        return []


def daemon_running() -> dict:
    if not DAEMON_PID.is_file():
        return {"running": False}
    try:
        pid = int(DAEMON_PID.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return {"running": False}
    alive = False
    if os.name == "nt":
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            alive = str(pid) in (r.stdout or "")
        except (OSError, subprocess.TimeoutExpired):
            alive = False
    else:
        try:
            os.kill(pid, 0)
            alive = True
        except OSError:
            alive = False
    return {"running": alive, "pid": pid if alive else None}


def probe_rows(q: str = "") -> list:
    rows = build_probe_rows(present_check=present_check)
    rows = [enrich_audacity(r) for r in rows]
    cfg = set_probed(load_config(), rows)
    save_config(cfg)
    return filter_candidates(rows, q)


def plate_latest() -> dict:
    """Last ARRAY pair + a short text bite. ARRAY is the database."""
    if not ARRAY_PATH.is_file():
        return {"ok": True, "count": 0, "pair": None, "dtypes": {}}
    try:
        data = json.loads(ARRAY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "ARRAY unreadable", "count": 0, "pair": None}
    audio = list(data.get("audio") or [])
    text = list(data.get("text") or [])
    if not audio:
        return {
            "ok": True,
            "count": int(data.get("count") or 0),
            "pair": None,
            "dtypes": data.get("dtypes") or {},
        }
    a = audio[-1]
    t = text[-1] if text else {}
    snippet = ""
    tp = Path(str(t.get("path") or ""))
    if tp.is_file():
        try:
            snippet = tp.read_text(encoding="utf-8")[:420].strip()
        except OSError:
            snippet = ""
    return {
        "ok": True,
        "count": int(data.get("count") or len(audio)),
        "dtypes": data.get("dtypes") or {},
        "pair": {
            "id": a.get("id"),
            "os_name": a.get("os_name"),
            "dtype": t.get("dtype") or a.get("dtype") or "",
            "hop": t.get("hop") or a.get("hop") or {},
            "chars": t.get("chars"),
            "snippet": snippet,
            "raw": str(t.get("path") or ""),
        },
    }


def review_rows() -> list:
    rows = []
    if JOURNAL.is_dir():
        for d in sorted(JOURNAL.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            meta = {}
            mp = d / "meta.json"
            if mp.is_file():
                try:
                    meta = json.loads(mp.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass
            rows.append({"stamp": d.name, "source": "journal", "path": str(d), "meta": meta})
    return rows


def start_daemon() -> dict:
    cur = daemon_running()
    if cur.get("running"):
        return {"ok": True, "already": True, **cur}
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
    log = HERE / "daemon.log"
    logf = open(log, "a", encoding="utf-8")
    logf.write(f"\n==== start {datetime.now().isoformat(timespec='seconds')} ====\n")
    logf.flush()
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "daemon.py"), "--poll", "20"],
        cwd=str(HERE),
        stdout=logf,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )
    DAEMON_PID.write_text(str(proc.pid) + "\n", encoding="utf-8")
    return {"ok": True, "pid": proc.pid, "log": str(log)}


def stop_daemon() -> dict:
    cur = daemon_running()
    if not cur.get("running"):
        if DAEMON_PID.is_file():
            try:
                DAEMON_PID.unlink()
            except OSError:
                pass
        return {"ok": True, "running": False}
    pid = cur["pid"]
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
    except OSError as e:
        return {"ok": False, "error": str(e)}
    try:
        DAEMON_PID.unlink(missing_ok=True)
    except TypeError:
        if DAEMON_PID.is_file():
            DAEMON_PID.unlink()
    return {"ok": True, "stopped": pid}


def daemon_once() -> dict:
    r = subprocess.run(
        [sys.executable, str(HERE / "daemon.py"), "--once", "--dry-run-launch"],
        capture_output=True,
        text=True,
        cwd=str(HERE),
    )
    return {
        "ok": r.returncode == 0,
        "stdout": (r.stdout or "")[:1200],
        "stderr": (r.stderr or "")[:400],
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        qs = parse_qs(u.query or "")
        if path == "/":
            body = UI.read_bytes() if UI.is_file() else b"missing ui"
            self.send_response(200 if UI.is_file() else 500)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if path == "/api/status":
            cfg = load_config()
            cap = designated_fields(cfg)
            _json(
                self,
                200,
                {
                    "ok": True,
                    "product": "sesefus-alarm-daemon",
                    "roots": {"journal": str(JOURNAL), "capture": str(JOURNAL)},
                    "capture": cap,
                    "alarms": load_alarms(),
                    "daemon": daemon_running(),
                    "prefs": load_prefs(),
                    "plate": plate_latest(),
                    "inbox": poll_inbox(prefs=load_prefs()),
                    "port": getattr(self.server, "server_port", DEFAULT_PORT),
                    "note": "BYO recorder + alarms — not virtual mixer / not in-house mic primary",
                },
            )
            return
        if path == "/api/capture/probe":
            q = (qs.get("q") or [""])[0]
            _json(self, 200, {"ok": True, "rows": probe_rows(q)})
            return
        if path == "/api/capture/inputs":
            prefer = (qs.get("device") or qs.get("prefer") or [""])[0]
            _json(self, 200, list_inputs(prefer=prefer))
            return
        if path == "/api/capture/meter":
            device = (qs.get("device") or [""])[0]
            from mic_meter import sample_meter

            _json(self, 200, sample_meter(device))
            return
        if path == "/api/review":
            _json(self, 200, {"ok": True, "rows": review_rows()})
            return
        if path == "/api/alarms":
            _json(self, 200, {"ok": True, "windows": load_alarms()})
            return
        if path == "/api/hop/prefs":
            _json(self, 200, {"ok": True, "prefs": load_prefs()})
            return
        if path == "/api/plate/latest":
            _json(self, 200, plate_latest())
            return
        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        path = u.path.rstrip("/") or "/"
        payload = _read_json(self)
        if path == "/api/record/open" or path == "/api/record":
            # Primary Record: open designated external app (not browser mic)
            dry = bool(payload.get("dry_run"))
            try:
                result = launch_designated(cfg=load_config(), dry_run=dry)
                _json(self, 200, result)
            except Exception as e:
                _json(self, 400, {"ok": False, "error": str(e)})
            return
        if path == "/api/capture/designate":
            cfg = load_config()
            cand = {
                "id": payload.get("id") or "custom",
                "label": payload.get("label") or "Custom",
                "command": payload.get("command") or "",
                "inbox": payload.get("inbox") or "",
                "glob": payload.get("glob") or "*.m4a",
            }
            cfg = designate(cfg, candidate=cand)
            save_config(cfg)
            _json(self, 200, {"ok": True, "capture": designated_fields(cfg)})
            return
        if path == "/api/hop/prefs":
            _json(self, 200, {"ok": True, "prefs": save_prefs(payload)})
            return
        if path == "/api/inbox/land":
            # persistent seen file + journal meta rebuild (only new takes)
            result = land_new_from_designated(
                cfg=load_config(),
                journal_root=JOURNAL,
                seen=None,
                persist_seen=True,
                min_age_sec=2.0,
            )
            prefs = load_prefs()
            cooking: list[str] = []
            if result.get("ok") and prefs.get("auto_cook") and result.get("landed"):
                stamps = [
                    Path(str(row.get("path") or "")).name
                    for row in (result.get("landed") or [])
                ]
                cooking = spawn_cook(stamps)
            result["cooking"] = cooking
            _json(self, 200 if result.get("ok") else 400, result)
            return
        if path == "/api/hop/cook":
            stamp = str(payload.get("journal") or "").strip()
            if not stamp:
                rows = review_rows()
                stamp = rows[-1]["stamp"] if rows else ""
            if not stamp:
                _json(self, 400, {"ok": False, "error": "no journal stamp to cook"})
                return
            proc = subprocess.Popen(
                [sys.executable, str(HERE / "hop_to_array.py"), "--journal", stamp],
                cwd=str(HERE),
                stdin=subprocess.DEVNULL,
            )
            _json(self, 200, {"ok": True, "journal": stamp, "pid": proc.pid, "cooking": True})
            return
        if path == "/api/daemon/start":
            _json(self, 200, start_daemon())
            return
        if path == "/api/daemon/stop":
            _json(self, 200, stop_daemon())
            return
        if path == "/api/daemon/once":
            _json(self, 200, daemon_once())
            return
        if path == "/api/alarms/fire":
            aid = str(payload.get("id") or "").strip()
            if not aid:
                _json(self, 400, {"ok": False, "error": "missing alarm id"})
                return
            dry = bool(payload.get("dry_run"))
            prefs = load_prefs()
            cmd = [sys.executable, str(HERE / "hop.py"), "--fire", aid]
            if dry:
                cmd.append("--dry-run")
            if prefs.get("show_cue_page"):
                cmd.append("--show-page")
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HERE))
            _json(
                self,
                200 if r.returncode == 0 else 400,
                {
                    "ok": r.returncode == 0,
                    "id": aid,
                    "dry_run": dry,
                    "stdout": (r.stdout or "")[:1600],
                    "stderr": (r.stderr or "")[:400],
                },
            )
            return
        self.send_error(404)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--bind", default="127.0.0.1")
    args = ap.parse_args()
    JOURNAL.mkdir(parents=True, exist_ok=True)
    # ensure capture config exists
    if not (HERE / "capture-config.json").is_file():
        from capture_config import default_config, save_config as sc

        sc(default_config())
    httpd = ThreadingHTTPServer((args.bind, args.port), Handler)
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    print(
        f"Sesefus alarm-daemon UI http://{args.bind}:{args.port}/  pid={os.getpid()}",
        flush=True,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            PID_FILE.unlink(missing_ok=True)
        except TypeError:
            if PID_FILE.is_file():
                PID_FILE.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
