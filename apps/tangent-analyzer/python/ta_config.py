#!/usr/bin/env python3
"""Session controls for tangent-analyzer. Own config, not clip-config, not hop."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "out_dir": "",
    "input_index": 0,
}


def config_path() -> Path:
    env = os.environ.get("SESEFUS_TA_CONFIG")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    return home / ".sesefus" / "ta-config.json"


def default_out_dir() -> Path:
    env = os.environ.get("SESEFUS_TA_OUT")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
    return home / "test-write" / "tangent-analyzer"


def load_config(path: Path | None = None) -> dict[str, Any]:
    p = path or config_path()
    cfg = dict(DEFAULTS)
    if p.is_file():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                if isinstance(data.get("out_dir"), str):
                    cfg["out_dir"] = data["out_dir"]
                if isinstance(data.get("input_index"), int):
                    cfg["input_index"] = data["input_index"]
        except (OSError, json.JSONDecodeError):
            pass
    return cfg


def save_config(cfg: dict[str, Any], path: Path | None = None) -> Path:
    p = path or config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "out_dir": str(cfg.get("out_dir") or ""),
        "input_index": int(cfg.get("input_index") or 0),
    }
    p.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return p


def resolved_out_dir(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg if cfg is not None else load_config()
    raw = str(cfg.get("out_dir") or "").strip()
    if raw:
        return Path(os.path.expandvars(raw)).expanduser()
    return default_out_dir()


def list_input_devices() -> list[tuple[int, str]]:
    """WinMM capture devices. Same shape as clip; own copy so clip stays parked."""
    if sys.platform != "win32":
        return [(0, "default (non-windows)")]
    import ctypes
    from ctypes import wintypes

    class WAVEINCAPSA(ctypes.Structure):
        _fields_ = [
            ("wMid", wintypes.WORD),
            ("wPid", wintypes.WORD),
            ("vDriverVersion", wintypes.UINT),
            ("szPname", ctypes.c_char * 32),
            ("dwFormats", wintypes.DWORD),
            ("wChannels", wintypes.WORD),
            ("wReserved1", wintypes.WORD),
        ]

    winmm = ctypes.windll.winmm
    n = int(winmm.waveInGetNumDevs())
    out: list[tuple[int, str]] = []
    for i in range(n):
        caps = WAVEINCAPSA()
        rc = winmm.waveInGetDevCapsA(i, ctypes.byref(caps), ctypes.sizeof(caps))
        if rc == 0:
            name = caps.szPname.decode("mbcs", errors="replace").rstrip("\x00")
        else:
            name = f"(caps failed {rc})"
        out.append((i, name))
    if not out:
        out.append((0, "default"))
    return out
