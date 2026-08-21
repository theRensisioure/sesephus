#!/usr/bin/env python3
"""Reliability prefs for the hop UI. Default: you click each hop."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
PREFS_PATH = HERE / "hop-prefs.json"

DEFAULTS: dict[str, Any] = {
    "auto_land": False,
    "auto_cook": False,
    "show_cue_page": False,
}


def load_prefs(path: Path | None = None) -> dict[str, Any]:
    path = path or PREFS_PATH
    out = dict(DEFAULTS)
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return out
        if isinstance(data, dict):
            for k in DEFAULTS:
                if k in data:
                    out[k] = bool(data[k])
    return out


def save_prefs(prefs: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    path = path or PREFS_PATH
    out = load_prefs(path)
    for k in DEFAULTS:
        if k in prefs:
            out[k] = bool(prefs[k])
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out
