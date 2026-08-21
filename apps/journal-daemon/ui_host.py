#!/usr/bin/env python3
"""Open Sesefus journal UI in its own window (Brave/Edge app mode or browser).

Mirrors Artifact Scanner's "own window" idea without pywebview requirement.
Serve on :8777 (not scanner :8765).
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PORT = 8777
DATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Sesefus"
LOG = DATA / "last-launch.log"
SERVE_PID = HERE / ".ui-serve.pid"


def _url(port: int) -> str:
    return f"http://127.0.0.1:{port}/"


def log(msg: str) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    line = msg.rstrip() + "\n"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    print(line, end="", flush=True)


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def url_ok(port: int) -> bool:
    try:
        with urllib.request.urlopen(_url(port), timeout=2) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ensure_serve(port: int) -> None:
    if port_open(port) and url_ok(port):
        log(f"serve already live {_url(port)}")
        return
    log(f"starting ui_serve.py on {port}")
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
    out = DATA / "ui-serve.log"
    DATA.mkdir(parents=True, exist_ok=True)
    logf = open(out, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "ui_serve.py"), "--port", str(port)],
        cwd=str(HERE),
        stdout=logf,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )
    SERVE_PID.write_text(str(proc.pid) + "\n", encoding="utf-8")
    for _ in range(40):
        if url_ok(port):
            log(f"serve ready pid={proc.pid}")
            return
        time.sleep(0.15)
    log("WARN serve not ready in time - still opening window")


def find_browser(port: int) -> tuple[str, list[str]] | None:
    """Return (kind, argv prefix) for app-mode window."""
    candidates = []
    local = Path(os.environ.get("LOCALAPPDATA") or "")
    pf = Path(os.environ.get("ProgramFiles") or r"C:\Program Files")
    pf86 = Path(os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)")
    for base, name in (
        (pf / "BraveSoftware" / "Brave-Browser" / "Application", "brave.exe"),
        (local / "BraveSoftware" / "Brave-Browser" / "Application", "brave.exe"),
        (pf86 / "Microsoft" / "Edge" / "Application", "msedge.exe"),
        (pf / "Microsoft" / "Edge" / "Application", "msedge.exe"),
        (pf / "Google" / "Chrome" / "Application", "chrome.exe"),
        (local / "Google" / "Chrome" / "Application", "chrome.exe"),
    ):
        p = base / name
        if p.is_file():
            candidates.append(p)
    if not candidates:
        which = shutil.which("brave") or shutil.which("msedge") or shutil.which("chrome")
        if which:
            candidates.append(Path(which))
    if not candidates:
        return None
    exe = str(candidates[0])
    return ("app", [exe, f"--app={_url(port)}", "--new-window"])


def open_window(port: int) -> None:
    found = find_browser(port)
    if found:
        kind, argv = found
        log(f"window mode: {kind} -> {argv[0]}")
        subprocess.Popen(argv, cwd=str(HERE))
        return
    log("no Brave/Edge/Chrome - os.startfile URL")
    url = _url(port)
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", url])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-open", action="store_true", help="ensure serve only")
    ap.add_argument(
        "--daemon-only",
        action="store_true",
        help="start alarm daemon only (no UI) - for optional Startup",
    )
    args = ap.parse_args()
    port = args.port

    DATA.mkdir(parents=True, exist_ok=True)
    log(f"==== Sesefus launch {time.strftime('%Y-%m-%d %H:%M:%S')} ====")

    if args.daemon_only:
        sys.path.insert(0, str(HERE))
        import ui_serve as us  # type: ignore

        out = us.start_daemon()
        log(f"daemon-only -> {out}")
        return 0 if out.get("ok") else 1

    ensure_serve(port)
    if not args.no_open:
        open_window(port)
    log("exit 0 (serve left running)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
