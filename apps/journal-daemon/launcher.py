#!/usr/bin/env python3
"""Launch designated BYO recorder (shared by Record button and alarm fire)."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from capture_config import (
    designated_fields,
    expand_path,
    load_config,
)

SpawnFn = Callable[[list[str]], Any]


def resolve_designated(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    cfg = cfg or load_config()
    fields = designated_fields(cfg)
    if not fields.get("command") or not fields.get("label"):
        raise ValueError("designated recorder command/label empty — designate a recorder")
    return fields


def build_launch_argv(cmd: str) -> list[str]:
    """Build OS argv exactly once (no double cmd/start wrap)."""
    cmd = str(cmd or "").strip()
    if not cmd:
        raise ValueError("empty launch command")
    if os.name == "nt":
        # shell: AppsFolder and freeform titles need start; bare .exe can run direct
        if cmd.startswith("shell:"):
            return ["cmd", "/c", "start", "", cmd]
        p = Path(cmd)
        if cmd.lower().endswith(".exe") or p.is_file():
            return [cmd]
        return ["cmd", "/c", "start", "", cmd]
    # non-Windows
    if Path(cmd).is_file() or cmd.endswith((".sh", ".AppImage")):
        return [cmd]
    return ["/bin/sh", "-c", cmd]


def launch_designated(
    *,
    cfg: dict[str, Any] | None = None,
    dry_run: bool = False,
    spawn: SpawnFn | None = None,
) -> dict[str, Any]:
    """Open the designated external recorder app.

    Returns resolved command/label always. If dry_run, does not spawn.
    spawn is injectable for tests (receives final argv list, already wrapped).
    """
    fields = resolve_designated(cfg)
    cmd = fields["command"]
    label = fields["label"]
    argv = build_launch_argv(cmd)
    result: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "label": label,
        "command": cmd,
        "designated_id": fields.get("designated_id") or "",
        "inbox": fields.get("inbox") or "",
        "glob": fields.get("glob") or "",
        "argv": argv,
        "spawned": False,
    }
    if dry_run:
        result["resolved"] = cmd
        return result

    def _default_spawn(final_argv: list[str]) -> None:
        # argv is already complete — do not wrap again
        kwargs: dict[str, Any] = {"cwd": str(Path.home())}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(final_argv, **kwargs)

    sp = spawn or _default_spawn
    if cmd.startswith("shell:") and os.name != "nt":
        raise RuntimeError("shell: AppsFolder launch is Windows-only")
    sp(argv)
    result["spawned"] = True
    return result


def present_check(candidate: dict[str, Any]) -> bool:
    """Cheap presence for probe rows."""
    cid = candidate.get("id")
    if cid == "ms-sound-recorder":
        return os.name == "nt"
    if cid == "custom":
        return True
    if cid == "audacity":
        if shutil.which("audacity"):
            return True
        for p in (
            r"C:\Program Files\Audacity\Audacity.exe",
            r"C:\Program Files (x86)\Audacity\Audacity.exe",
            "/usr/bin/audacity",
        ):
            if Path(p).is_file():
                return True
        return False
    cmd = str(candidate.get("command") or "")
    if cmd and Path(expand_path(cmd)).is_file():
        return True
    return False


def enrich_audacity(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("id") != "audacity":
        return row
    for p in (
        r"C:\Program Files\Audacity\Audacity.exe",
        r"C:\Program Files (x86)\Audacity\Audacity.exe",
    ):
        if Path(p).is_file():
            row = dict(row)
            row["command"] = p
            row["present"] = True
            return row
    w = shutil.which("audacity")
    if w:
        row = dict(row)
        row["command"] = w
        row["present"] = True
    return row
