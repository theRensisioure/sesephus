#!/usr/bin/env python3
"""Alarm due/fire logic — once per window per local day."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

FireHandler = Callable[[dict[str, Any]], None]


def load_alarms(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("windows") or [])


def load_state(path: Path) -> dict[str, Any]:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"fired": {}}


def save_state(path: Path, st: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def day_key(aid: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    return f"{when.date().isoformat()}:{aid}"


def due_windows(
    windows: list[dict[str, Any]],
    st: dict[str, Any],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    now = now or datetime.now()
    hhmm = now.strftime("%H:%M")
    out: list[dict[str, Any]] = []
    fired = st.get("fired") or {}
    for w in windows:
        aid = str(w.get("id") or w.get("time"))
        t = str(w.get("time") or "")
        if t != hhmm:
            continue
        if fired.get(day_key(aid, now)):
            continue
        out.append(w)
    return out


def mark_fired(st: dict[str, Any], window: dict[str, Any], *, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now()
    aid = str(window.get("id") or window.get("time"))
    st = dict(st)
    fired = dict(st.get("fired") or {})
    fired[day_key(aid, now)] = now.isoformat(timespec="seconds")
    st["fired"] = fired
    return st


def fire_window(
    window: dict[str, Any],
    *,
    cue_dir: Path,
    launch: FireHandler | None = None,
    hop: Callable[..., Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Write cue JSON + cue page, ride hop, then open designated recorder."""
    from hop import resolve_media, write_cue_page

    now = now or datetime.now()
    cue_dir.mkdir(parents=True, exist_ok=True)
    aid = str(window.get("id") or "alarm")
    ts = now.strftime("%Y%m%d-%H%M%S")
    stem = f"{ts}-{aid}"
    path = cue_dir / f"{stem}.json"
    media = resolve_media(window)
    page = write_cue_page(cue_dir, window, stem=stem, media=media)
    cue = {
        "fired_at": now.isoformat(timespec="seconds"),
        "alarm": window,
        "action": "open_designated_recorder",
        "hop": {
            "page": str(page),
            "sound": media.get("sound") or "",
            "picture": media.get("picture") or "",
            "sound_missing": bool(media.get("sound_missing")),
            "picture_missing": bool(media.get("picture_missing")),
        },
    }
    path.write_text(json.dumps(cue, indent=2) + "\n", encoding="utf-8")
    try:
        tools = Path(os.environ.get("USERPROFILE") or "") / "jwrangle" / "tools"
        if str(tools) not in sys.path:
            sys.path.insert(0, str(tools))
        from thought_step import play as _memo_beep

        _memo_beep("memo")
    except Exception:
        pass
    hop_result = None
    if hop is not None:
        hop_result = hop(window, page)
    launch_result = None
    if launch is not None:
        launch_result = launch(window)
    return {
        "ok": True,
        "cue": str(path),
        "page": str(page),
        "alarm_id": aid,
        "hop": hop_result,
        "launch": launch_result,
    }
