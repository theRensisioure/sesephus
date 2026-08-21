#!/usr/bin/env python3
"""Open the skills window in its own OS window. Not the scanner host."""
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
DEFAULT_PORT = 8788
DATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / "Sesefus"
LOG = DATA / "skills-window-launch.log"
SERVE_PID = HERE / ".serve.pid"


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
    log(f"starting serve.py on {port}")
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0x00000008
        )
    DATA.mkdir(parents=True, exist_ok=True)
    out = DATA / "skills-window-serve.log"
    logf = open(out, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(HERE / "serve.py"), "--port", str(port)],
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
    log("WARN serve not ready in time — still opening window")


def find_browser() -> tuple[str, list[str]] | None:
    candidates: list[Path] = []
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
    return ("app", [str(candidates[0])])


def open_window(port: int) -> None:
    found = find_browser()
    url = _url(port)
    if found:
        kind, argv = found
        log(f"window mode: {kind} -> {argv[0]}")
        subprocess.Popen(argv + [f"--app={url}", "--new-window"], cwd=str(HERE))
        return
    log("no Brave/Edge/Chrome — os.startfile URL")
    if os.name == "nt":
        os.startfile(url)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["xdg-open", url])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    log(f"==== skills-window {time.strftime('%Y-%m-%d %H:%M:%S')} ====")
    ensure_serve(args.port)
    if not args.no_open:
        open_window(args.port)
    log("exit 0 (serve left running)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
