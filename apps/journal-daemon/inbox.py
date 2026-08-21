#!/usr/bin/env python3
"""Detect new inbox takes and land into journal vault path (link or copy)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from capture_config import designated_fields, expand_path, load_config

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("USERPROFILE") or os.environ.get("HOME") or Path.home())
DEFAULT_JOURNAL = HOME / "test-write" / "journal"
DEFAULT_SEEN_PATH = HERE / ".inbox-seen.json"
HOP_TO_ARRAY = HERE / "hop_to_array.py"
SETTLE_SEC = 2.0


def list_inbox_files(
    inbox: str | Path,
    glob_pat: str = "*.m4a",
) -> list[Path]:
    d = expand_path(inbox)
    if not d.is_dir():
        return []
    return sorted(d.glob(glob_pat), key=lambda p: p.stat().st_mtime)


def is_settled(path: Path, min_age_sec: float = SETTLE_SEC) -> bool:
    """Sound Recorder may still be writing. Do not land a growing take."""
    try:
        st = path.stat()
    except OSError:
        return False
    if st.st_size <= 0:
        return False
    return (time.time() - st.st_mtime) >= float(min_age_sec)


def _source_key(src: Path) -> str:
    try:
        return str(src.resolve())
    except OSError:
        return str(src)


def load_seen(path: Path | None = None) -> set[str]:
    path = path or DEFAULT_SEEN_PATH
    if not path.is_file():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(x) for x in data}
        if isinstance(data, dict) and isinstance(data.get("seen"), list):
            return {str(x) for x in data["seen"]}
    except (OSError, json.JSONDecodeError):
        pass
    return set()


def save_seen(seen: set[str], path: Path | None = None) -> None:
    path = path or DEFAULT_SEEN_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"seen": sorted(seen)}, indent=2) + "\n",
        encoding="utf-8",
    )


def rebuild_seen_from_journal(journal_root: Path | None = None) -> set[str]:
    """Union source_path values already landed (recover if seen file missing)."""
    root = journal_root or DEFAULT_JOURNAL
    seen: set[str] = set()
    if not root.is_dir():
        return seen
    for d in root.iterdir():
        if not d.is_dir() or d.name.startswith("_"):
            continue
        mp = d / "meta.json"
        if not mp.is_file():
            continue
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sp = meta.get("source_path")
        if sp:
            try:
                seen.add(str(Path(sp).resolve()))
            except OSError:
                seen.add(str(sp))
    return seen


def land_file(
    src: Path,
    *,
    journal_root: Path | None = None,
    prefer_link: bool = True,
    alarm_id: str = "",
    sampled_by: str = "inbox",
) -> dict[str, Any]:
    """Land one take into journal_root/<stamp>/ — hardlink/symlink or copy."""
    if not src.is_file():
        return {"ok": False, "error": f"not a file: {src}"}
    root = journal_root or DEFAULT_JOURNAL
    root.mkdir(parents=True, exist_ok=True)
    sid = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_dir = root / sid
    n = 0
    while dest_dir.exists():
        n += 1
        dest_dir = root / f"{sid}-{n}"
    dest_dir.mkdir(parents=True, exist_ok=False)
    dest = dest_dir / src.name
    try:
        sys.path.insert(0, str(HOME / "jwrangle" / "tools"))
        from thought_step import play as _memo_beep

        _memo_beep("memo")
    except Exception:
        pass
    method = "copy"
    try:
        if prefer_link:
            try:
                os.link(src, dest)
                method = "hardlink"
            except OSError:
                try:
                    os.symlink(src, dest)
                    method = "symlink"
                except OSError:
                    shutil.copy2(src, dest)
                    method = "copy"
        else:
            shutil.copy2(src, dest)
            method = "copy"
    except OSError as e:
        return {"ok": False, "error": str(e)}

    size = dest.stat().st_size if dest.exists() else 0
    if size == 0 and dest.is_symlink():
        try:
            size = dest.resolve().stat().st_size
        except OSError:
            pass
    meta = {
        "stamp": dest_dir.name,
        "audio": src.name,
        "source_path": str(src),
        "land_method": method,
        "audio_bytes": size,
        "sampled_by": sampled_by,
        "alarm_id": alarm_id or None,
        "transcription": "parked",
    }
    (dest_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "path": str(dest_dir),
        "file": str(dest),
        "size": size,
        "method": method,
        "meta": meta,
        "source_key": _source_key(src),
    }


def land_new_from_designated(
    *,
    cfg: dict[str, Any] | None = None,
    journal_root: Path | None = None,
    seen: set[str] | None = None,
    seen_path: Path | None = None,
    persist_seen: bool = True,
    max_files: int = 50,
    min_age_sec: float = 0.0,
) -> dict[str, Any]:
    """Land files in designated inbox not yet tracked in seen paths.

    When seen is None, load from seen_path (default .inbox-seen.json) and union
    journal meta source_paths so re-clicks do not re-land old takes.
    Unsettled files (mtime younger than min_age_sec) stay unseen so the next
    poll can land them after Sound Recorder finishes the take.
    """
    cfg = cfg or load_config()
    fields = designated_fields(cfg)
    inbox = expand_path(fields["inbox"])
    glob_pat = fields.get("glob") or "*.m4a"
    jroot = journal_root or DEFAULT_JOURNAL
    spath = seen_path or DEFAULT_SEEN_PATH

    if seen is None:
        seen = load_seen(spath) | rebuild_seen_from_journal(jroot)
    else:
        seen = set(seen)

    landed: list[dict[str, Any]] = []
    skipped_unsettled: list[str] = []
    files = list_inbox_files(inbox, glob_pat)
    for f in files[-max_files:]:
        key = _source_key(f)
        if key in seen:
            continue
        if min_age_sec and not is_settled(f, min_age_sec):
            skipped_unsettled.append(f.name)
            continue
        r = land_file(f, journal_root=jroot)
        if r.get("ok"):
            seen.add(key)
            landed.append(r)
    if persist_seen:
        save_seen(seen, spath)
    return {
        "ok": True,
        "inbox": str(inbox),
        "glob": glob_pat,
        "landed": landed,
        "count": len(landed),
        "seen_count": len(seen),
        "seen": sorted(seen),
        "skipped_unsettled": skipped_unsettled,
    }


def seed_existing_inbox(
    *,
    cfg: dict[str, Any] | None = None,
    seen_path: Path | None = None,
    skip_names: set[str] | None = None,
) -> dict[str, Any]:
    """Mark current inbox files seen without landing. Auto-land then only fires on new takes."""
    cfg = cfg or load_config()
    fields = designated_fields(cfg)
    inbox = expand_path(fields["inbox"])
    glob_pat = fields.get("glob") or "*.m4a"
    spath = seen_path or DEFAULT_SEEN_PATH
    skip = {n.lower() for n in (skip_names or set())}
    seen = load_seen(spath)
    added: list[str] = []
    for f in list_inbox_files(inbox, glob_pat):
        if f.name.lower() in skip:
            continue
        key = _source_key(f)
        if key not in seen:
            seen.add(key)
            added.append(f.name)
    save_seen(seen, spath)
    return {
        "ok": True,
        "inbox": str(inbox),
        "added": added,
        "count": len(added),
        "seen_count": len(seen),
    }


def spawn_cook(
    stamps: list[str],
    *,
    runner: Callable[..., Any] | None = None,
) -> list[str]:
    """Cook each new journal stamp. Sequential — Whisper is one basin."""
    stamps = [s for s in stamps if s]
    if not stamps:
        return []
    exe = [sys.executable, str(HOP_TO_ARRAY)]

    def run() -> None:
        for stamp in stamps:
            cmd = exe + ["--journal", stamp]
            if runner is not None:
                runner(cmd)
                continue
            subprocess.run(cmd, cwd=str(HERE), stdin=subprocess.DEVNULL)

    if runner is not None:
        run()
    else:
        threading.Thread(target=run, daemon=True).start()
    return stamps


def poll_inbox(
    *,
    cfg: dict[str, Any] | None = None,
    prefs: dict[str, Any] | None = None,
    journal_root: Path | None = None,
    seen_path: Path | None = None,
    cook: bool = True,
    runner: Callable[..., Any] | None = None,
    min_age_sec: float | None = None,
) -> dict[str, Any]:
    """If auto_land: land settled new takes. If auto_cook: transcribe each one."""
    if prefs is None:
        from hop_prefs import load_prefs

        prefs = load_prefs()
    if not prefs.get("auto_land"):
        return {
            "ok": True,
            "skipped": "auto_land off",
            "count": 0,
            "landed": [],
            "cooking": [],
        }
    result = land_new_from_designated(
        cfg=cfg,
        journal_root=journal_root,
        seen_path=seen_path,
        persist_seen=True,
        min_age_sec=SETTLE_SEC if min_age_sec is None else min_age_sec,
    )
    cooking: list[str] = []
    if cook and prefs.get("auto_cook"):
        stamps = [Path(str(row.get("path") or "")).name for row in (result.get("landed") or [])]
        cooking = spawn_cook(stamps, runner=runner)
    result["cooking"] = cooking
    return result
