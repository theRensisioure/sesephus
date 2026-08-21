#!/usr/bin/env python3
"""Sesefus → AyTree launcher (suite Version Control / derivation-map module).

Resolves the AyTree checkout without baking a suite project roster into product
logic:

  1. AYTREE_ROOT env
  2. sesefus.config.json ``aytree_root``
  3. Sibling folders next to this repo: AyTree / aytree

Surfaces (HTTP on aytree_port, default 8000):
  open / map  → /derivation   (directory lineage map)
  tree        → /             (in-repo tree + notes tool)
  serve       → start server in foreground
  status      → probe /api/derivation

Usage:
  python tools/aytree_launch.py [open|map|tree|serve|status|help]
  ssfs aytree open   # via Zig REPL once wired
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# tools/ → repo root
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools"))

try:
    from sesefus_config import load_config
except ImportError:
    def load_config() -> dict:
        return {}


def resolve_aytree_root(cfg: dict | None = None) -> Path | None:
    cfg = cfg if cfg is not None else load_config()
    env = os.environ.get("AYTREE_ROOT", "").strip()
    if env:
        p = Path(env).expanduser()
        if _is_aytree(p):
            return p.resolve()
        print(f"[aytree] AYTREE_ROOT set but not an AyTree tree: {p}", file=sys.stderr)

    conf = (cfg.get("aytree_root") or "").strip()
    if conf:
        p = Path(conf).expanduser()
        if _is_aytree(p):
            return p.resolve()
        print(f"[aytree] aytree_root in config not valid: {p}", file=sys.stderr)

    # Sibling discovery only — not a hardcoded suite inventory
    parent = REPO_ROOT.parent
    for name in ("AyTree", "aytree"):
        cand = parent / name
        if _is_aytree(cand):
            return cand.resolve()

    return None


def _is_aytree(p: Path) -> bool:
    try:
        return (p / "server" / "aytree_server.py").is_file()
    except OSError:
        return False


def aytree_port(cfg: dict | None = None) -> int:
    cfg = cfg if cfg is not None else load_config()
    env = os.environ.get("AYTREE_PORT", "").strip()
    if env.isdigit():
        return int(env)
    raw = cfg.get("aytree_port", 8000)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 8000


def base_url(port: int) -> str:
    return f"http://127.0.0.1:{port}"


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def probe_status(port: int) -> dict:
    url = f"{base_url(port)}/api/derivation"
    try:
        with urllib.request.urlopen(url, timeout=1.5) as resp:
            body = resp.read(200)
            return {"ok": True, "status": resp.status, "snippet": body[:80].decode("utf-8", "replace")}
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# The AyTree server binds its own DEFAULT_PORT and walks upward while that is
# busy (AyTree/server/aytree_server.py), and it does not read AYTREE_PORT. So
# the port we ask for is a preference, not a guarantee — find where the server
# actually landed instead of polling one that nothing will ever open.
SERVER_PORT_SCAN = 20


def discover_server_port(preferred: int) -> int | None:
    """Port an AyTree server is actually answering on, or None."""
    for p in [preferred] + [preferred + i for i in range(1, SERVER_PORT_SCAN)]:
        if port_open(p) and probe_status(p).get("ok"):
            return p
    return None


def ensure_server(root: Path, port: int, background: bool = True) -> subprocess.Popen | None:
    live = discover_server_port(port)
    if live is not None:
        print(f"[aytree] server already listening on :{live}")
        return None
    if port_open(port):
        # A bare TCP connect only proves *something* holds the port. Without
        # this check the launcher announced success and opened a browser at
        # whatever unrelated app happened to be sitting there.
        print(
            f"[aytree] port {port} is held by something that is not AyTree — "
            f"stop it or choose another port",
            file=sys.stderr,
        )
        raise SystemExit(1)

    server_py = root / "server" / "aytree_server.py"
    py = sys.executable or ("python" if os.name == "nt" else "python3")
    env = os.environ.copy()
    # The server reads its port from the environment; without this a non-default
    # --port/aytree_port polled and opened a port nothing was listening on.
    env["AYTREE_PORT"] = str(port)
    # Prefer the resolved root; server finds WEB_ROOT from its own file path
    cmd = [py, str(server_py)]
    print(f"[aytree] starting {server_py} (cwd={root})")
    if background:
        # Detach so REPL returns. Keep the child's stderr in a log rather than
        # DEVNULL — a server that dies instantly used to leave no diagnosis path.
        log_path = root / ".aytree_server.log"
        try:
            log = open(log_path, "ab", buffering=0)
        except OSError:
            log = subprocess.DEVNULL
        kwargs: dict = {
            "cwd": str(root),
            "env": env,
            "stdout": log,
            "stderr": subprocess.STDOUT if log is not subprocess.DEVNULL else subprocess.DEVNULL,
        }
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
                subprocess, "DETACHED_PROCESS", 0
            )
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(cmd, **kwargs)
        # Wait briefly for bind
        for _ in range(40):
            if proc.poll() is not None:
                print(
                    f"[aytree] server exited immediately (rc={proc.returncode}); see {log_path}",
                    file=sys.stderr,
                )
                return None
            live = discover_server_port(port)
            if live is not None:
                if live != port:
                    print(f"[aytree] note: server bound :{live}, not the requested :{port}")
                print(f"[aytree] up at {base_url(live)}/")
                return proc
            time.sleep(0.1)
        print("[aytree] server started but port not open yet — give it a moment", file=sys.stderr)
        return proc
    # Foreground. Not os.execv: on Windows exec spawns a *new* process and kills
    # this one, so `aytree serve` returned instantly and orphaned the server.
    raise SystemExit(subprocess.call(cmd, cwd=str(root), env=env))


def open_surface(port: int, path: str, no_browser: bool) -> None:
    url = f"{base_url(port)}{path}"
    print(f"[aytree] {url}")
    if no_browser:
        return
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[aytree] could not open browser: {e}", file=sys.stderr)


def cmd_help() -> int:
    print(__doc__)
    root = resolve_aytree_root()
    print(f"Resolved root: {root or '(not found — set AYTREE_ROOT or aytree_root in sesefus.config.json)'}")
    print(f"Port: {aytree_port()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aytree_launch", add_help=False)
    parser.add_argument(
        "action",
        nargs="?",
        default="open",
        choices=["open", "map", "tree", "serve", "status", "help", "h"],
    )
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--port", type=int, default=None)
    args, _unknown = parser.parse_known_args(argv)

    if args.action in ("help", "h"):
        return cmd_help()

    cfg = load_config()
    port = args.port if args.port is not None else aytree_port(cfg)
    root = resolve_aytree_root(cfg)

    if args.action == "status":
        live = discover_server_port(port)
        if live is not None:
            print(f"[aytree] port {live}: open; derivation API: {probe_status(live)}")
            return 0
        if port_open(port):
            print(f"[aytree] port {port}: open, but nothing there answers the AyTree API")
            return 1
        print(f"[aytree] port {port}: not listening")
        if root:
            print(f"[aytree] install found at {root} — run: aytree open")
        else:
            print("[aytree] no AyTree checkout resolved")
        return 1

    if root is None:
        print(
            "[aytree] AyTree not found.\n"
            "  Set AYTREE_ROOT, or aytree_root in sesefus.config.json,\n"
            "  or clone AyTree as a sibling of the sesefus repo (../AyTree).",
            file=sys.stderr,
        )
        return 2

    if args.action == "serve":
        # ensure_server raises SystemExit with the server's own exit code
        ensure_server(root, port, background=False)
        return 0  # unreachable

    ensure_server(root, port, background=True)

    # Don't point a browser at a port nothing came up on, and don't report
    # success when the server died on startup.
    live = discover_server_port(port)
    if live is None:
        print(
            f"[aytree] no AyTree server answering near :{port} — see {root / '.aytree_server.log'}",
            file=sys.stderr,
        )
        return 1

    if args.action in ("open", "map"):
        open_surface(live, "/derivation", args.no_browser)
    elif args.action == "tree":
        open_surface(live, "/", args.no_browser)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
