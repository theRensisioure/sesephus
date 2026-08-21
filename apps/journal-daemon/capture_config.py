#!/usr/bin/env python3
"""Capture adapter: BYO designated recorder (not in-process mic / virtual mixer).

Pure-ish logic: load/save config, filter candidates, designate, expand paths.
OS presence probe and spawn live in launcher.py.
"""
from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = HERE / "capture-config.json"
HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())

# Known recorders: always listable; "present" filled by probe when available.
KNOWN_RECORDERS: list[dict[str, Any]] = [
    {
        "id": "ms-sound-recorder",
        "label": "Sound Recorder",
        "match": ["sound recorder", "voice recorder", "soundrecorder", "ms-sound"],
        "command": "shell:AppsFolder\\Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App",
        "inbox": "%USERPROFILE%\\Documents\\Sound Recordings",
        "glob": "*.m4a",
        "open_how": "Windows store app (AppsFolder)",
        "inbox_hint": "Documents\\Sound Recordings\\*.m4a",
        "os": "nt",
    },
    {
        "id": "audacity",
        "label": "Audacity",
        "match": ["audacity"],
        "command": "",  # filled if found on PATH or common paths
        "inbox": "%USERPROFILE%\\Documents\\Sound Recordings",
        "glob": "*.wav",
        "open_how": "desktop app path",
        "inbox_hint": "export / save into inbox (user chooses)",
        "os": "any",
    },
    {
        "id": "custom",
        "label": "Custom command",
        "match": ["custom"],
        "command": "",
        "inbox": "%USERPROFILE%\\Documents\\Sound Recordings",
        "glob": "*.m4a",
        "open_how": "user-supplied command",
        "inbox_hint": "set inbox + glob",
        "os": "any",
    },
]


def expand_path(p: str | Path) -> Path:
    s = str(p or "")
    s = os.path.expandvars(os.path.expanduser(s))
    return Path(s)


def default_config() -> dict[str, Any]:
    ms = next(c for c in KNOWN_RECORDERS if c["id"] == "ms-sound-recorder")
    return {
        "version": 1,
        "product": "sesefus-alarm-daemon",
        "capture": {
            "designated_id": ms["id"],
            "command": ms["command"],
            "inbox": ms["inbox"],
            "glob": ms["glob"],
            "label": ms["label"],
        },
        "probed": [],
    }


def load_config(path: Path | None = None) -> dict[str, Any]:
    path = path or DEFAULT_CONFIG_PATH
    if not path.is_file():
        cfg = default_config()
        return cfg
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()
    if not isinstance(data, dict):
        return default_config()
    base = default_config()
    base.update({k: data[k] for k in data if k in ("version", "product", "probed")})
    cap = data.get("capture") if isinstance(data.get("capture"), dict) else {}
    base["capture"] = {**base["capture"], **{k: cap[k] for k in cap if k in base["capture"] or k in (
        "designated_id", "command", "inbox", "glob", "label"
    )}}
    if isinstance(data.get("probed"), list):
        base["probed"] = data["probed"]
    return base


def save_config(cfg: dict[str, Any], path: Path | None = None) -> Path:
    path = path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def filter_candidates(
    candidates: list[dict[str, Any]],
    query: str,
) -> list[dict[str, Any]]:
    """Grep label + match tokens + command/path. Empty query → all."""
    q = (query or "").strip().lower()
    if not q:
        return list(candidates)
    out: list[dict[str, Any]] = []
    for c in candidates:
        # grep designation surface — not inbox paths (avoids "sound" hitting "Sound Recordings")
        blob_parts = [
            str(c.get("id") or ""),
            str(c.get("label") or ""),
            str(c.get("command") or ""),
            str(c.get("open_how") or ""),
        ]
        for m in c.get("match") or []:
            blob_parts.append(str(m))
        blob = " ".join(blob_parts).lower()
        if q in blob or all(tok in blob for tok in re.split(r"\s+", q) if tok):
            out.append(c)
    return out


def designate(
    cfg: dict[str, Any],
    *,
    candidate: dict[str, Any] | None = None,
    candidate_id: str | None = None,
    command: str | None = None,
    inbox: str | None = None,
    glob: str | None = None,
    label: str | None = None,
) -> dict[str, Any]:
    """Merge designation into config.capture. Returns new config (mutates copy)."""
    out = deepcopy(cfg)
    cap = dict(out.get("capture") or {})
    cand = candidate
    if cand is None and candidate_id:
        for c in list(out.get("probed") or []) + KNOWN_RECORDERS:
            if c.get("id") == candidate_id:
                cand = c
                break
    if cand:
        cap["designated_id"] = str(cand.get("id") or cap.get("designated_id") or "custom")
        if cand.get("command"):
            cap["command"] = str(cand["command"])
        if cand.get("inbox"):
            cap["inbox"] = str(cand["inbox"])
        if cand.get("glob"):
            cap["glob"] = str(cand["glob"])
        if cand.get("label"):
            cap["label"] = str(cand["label"])
    if command is not None:
        cap["command"] = command
        if not cap.get("designated_id"):
            cap["designated_id"] = "custom"
    if inbox is not None:
        cap["inbox"] = inbox
    if glob is not None:
        cap["glob"] = glob
    if label is not None:
        cap["label"] = label
    out["capture"] = cap
    return out


def designated_fields(cfg: dict[str, Any]) -> dict[str, str]:
    cap = cfg.get("capture") or {}
    return {
        "designated_id": str(cap.get("designated_id") or ""),
        "command": str(cap.get("command") or ""),
        "inbox": str(cap.get("inbox") or ""),
        "glob": str(cap.get("glob") or "*.m4a"),
        "label": str(cap.get("label") or ""),
    }


def build_probe_rows(
    *,
    present_check: Callable[[dict[str, Any]], bool] | None = None,
) -> list[dict[str, Any]]:
    """Return compact rows for UI: known recorders with present flag."""
    rows: list[dict[str, Any]] = []
    for raw in KNOWN_RECORDERS:
        c = deepcopy(raw)
        if c.get("os") == "nt" and os.name != "nt":
            # still list custom; skip pure Windows apps on non-nt unless present
            if present_check is None or not present_check(c):
                c["present"] = False
                rows.append(c)
                continue
        present = True
        if present_check is not None:
            present = bool(present_check(c))
        elif c["id"] == "ms-sound-recorder":
            present = os.name == "nt"
        elif c["id"] == "audacity":
            present = False  # filled by launcher.probe if used
        c["present"] = present
        rows.append(c)
    return rows


def set_probed(cfg: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    out = deepcopy(cfg)
    out["probed"] = rows
    # do not clobber designation
    return out
