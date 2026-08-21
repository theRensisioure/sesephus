#!/usr/bin/env python3
"""Skills window — list skill dirs, open them. Port 8788. Not the scanner."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from providers import (  # noqa: E402
    DEFAULT_FILE,
    add_provider,
    allowed_bases,
    enabled_providers,
    load_registry,
    path_allowed,
    resolve_root,
)
from scan import catalog  # noqa: E402

UI = HERE / "ui.html"
FONTS = HERE / "fonts"
DEFAULT_PORT = 8788
PID_FILE = HERE / ".serve.pid"


def _json(handler: BaseHTTPRequestHandler, code: int, obj: dict) -> None:
    body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _bytes(handler: BaseHTTPRequestHandler, code: int, body: bytes, ctype: str) -> None:
    handler.send_response(code)
    handler.send_header("Content-Type", ctype)
    handler.send_header("Content-Length", str(len(body)))
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


def open_dir(path: Path) -> dict:
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
        return {"ok": True, "path": str(path)}
    opener = "open" if sys.platform == "darwin" else "xdg-open"
    subprocess.Popen([opener, str(path)])
    return {"ok": True, "path": str(path)}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self) -> None:
        u = urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            if not UI.is_file():
                return _json(self, 500, {"ok": False, "error": "ui.html missing"})
            return _bytes(self, 200, UI.read_bytes(), "text/html; charset=utf-8")
        if path.startswith("/fonts/"):
            name = Path(path).name
            fp = (FONTS / name).resolve()
            try:
                fp.relative_to(FONTS.resolve())
            except ValueError:
                return _json(self, 404, {"ok": False, "error": "no"})
            if not fp.is_file() or not name.endswith(".ttf"):
                return _json(self, 404, {"ok": False, "error": "no font"})
            return _bytes(self, 200, fp.read_bytes(), "font/ttf")
        if path == "/api/catalog":
            reg = load_registry()
            data = catalog(reg, resolve_root, enabled_providers)
            data["item"] = "skills-window"
            data["app"] = str(HERE)
            data["registry"] = str(DEFAULT_FILE)
            return _json(self, 200, data)
        if path == "/api/health":
            return _json(self, 200, {"ok": True, "item": "skills-window", "port": DEFAULT_PORT})
        return _json(self, 404, {"ok": False, "error": "not found"})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        body = _read_json(self)
        if u.path == "/api/open":
            raw = str(body.get("path") or "").strip()
            if not raw:
                return _json(self, 400, {"ok": False, "error": "need path"})
            target = Path(raw)
            reg = load_registry()
            bases = allowed_bases(reg)
            # also allow opening the registry file's folder (wire-in door)
            bases.append(HERE.resolve())
            if not path_allowed(target, bases):
                return _json(self, 403, {"ok": False, "error": "path is not a wired skill dir"})
            try:
                return _json(self, 200, open_dir(target.resolve()))
            except OSError as e:
                return _json(self, 500, {"ok": False, "error": str(e)})
        if u.path == "/api/providers":
            try:
                add_provider(body, DEFAULT_FILE)
            except ValueError as e:
                return _json(self, 400, {"ok": False, "error": str(e)})
            reg = load_registry()
            data = catalog(reg, resolve_root, enabled_providers)
            data["ok"] = True
            data["added"] = str(body.get("id") or "")
            data["app"] = str(HERE)
            data["registry"] = str(DEFAULT_FILE)
            return _json(self, 200, data)
        return _json(self, 404, {"ok": False, "error": "not found"})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"skills-window http://127.0.0.1:{args.port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
