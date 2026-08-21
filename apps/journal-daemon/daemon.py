#!/usr/bin/env python3
"""Sesefus alarm daemon — schedule poll; fire opens designated BYO recorder.

Not Artifact Scanner. Not virtual mixer. Not in-house mic capture.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from alarm_core import (
    due_windows,
    fire_window,
    load_alarms,
    load_state,
    mark_fired,
    save_state,
)
from capture_config import load_config
from hop import ride_hop
from hop_prefs import load_prefs
from inbox import poll_inbox
from launcher import launch_designated

HERE = Path(__file__).resolve().parent
HOME = Path(__import__("os").environ.get("USERPROFILE") or Path.home())
STATE = HERE / ".daemon-state.json"
DEFAULT_ALARMS = HERE / "alarms.json"
CUE_DIR = HOME / "test-write" / "journal" / "_cues"


def _launch_on_fire(*, dry_run: bool = False) -> dict:
    return launch_designated(cfg=load_config(), dry_run=dry_run)


def run_once(
    *,
    alarms_path: Path = DEFAULT_ALARMS,
    state_path: Path = STATE,
    cue_dir: Path = CUE_DIR,
    now: datetime | None = None,
    dry_run_launch: bool = False,
    show_page: bool = False,
    force_due_id: str | None = None,
) -> dict:
    """Check due windows once. Returns summary for tests/smoke."""
    if not alarms_path.is_file():
        return {"ok": False, "error": f"missing alarms: {alarms_path}"}
    windows = load_alarms(alarms_path)
    st = load_state(state_path)
    now = now or datetime.now()

    if force_due_id:
        match = [w for w in windows if str(w.get("id")) == force_due_id]
        if not match:
            match = [{"id": force_due_id, "time": now.strftime("%H:%M"), "label": "forced"}]
        w = dict(match[0])
        w["time"] = now.strftime("%H:%M")
        key = f"{now.date().isoformat()}:{w['id']}"
        fired_map = dict(st.get("fired") or {})
        fired_map.pop(key, None)
        st["fired"] = fired_map
        due = [w]
    else:
        due = due_windows(windows, st, now=now)

    results = []
    for w in due:
        r = fire_window(
            w,
            cue_dir=cue_dir,
            hop=lambda _win, page: ride_hop(
                _win, page_path=page, dry_run=dry_run_launch, show_page=show_page
            ),
            launch=lambda _win: _launch_on_fire(dry_run=dry_run_launch),
            now=now,
        )
        st = mark_fired(st, w, now=now)
        results.append(r)
        print(f"[alarm] FIRED {w.get('id')} @ {w.get('time')} → {r.get('cue')}", flush=True)
        if w.get("prompt"):
            print(f"        prompt: {w['prompt']}", flush=True)
        hr = r.get("hop") or {}
        if hr.get("page"):
            print(f"        cue page: {hr.get('page')}", flush=True)
        if hr.get("sound"):
            print(f"        sound rode: {hr.get('sound')}", flush=True)
        if hr.get("picture"):
            print(f"        picture rode: {hr.get('picture')}", flush=True)
        lr = r.get("launch") or {}
        if lr.get("command"):
            mode = "dry-run" if lr.get("dry_run") else ("spawned" if lr.get("spawned") else "resolved")
            print(f"        recorder [{mode}]: {lr.get('label')} · {lr.get('command')}", flush=True)
    save_state(state_path, st)
    inbox = poll_inbox(prefs=load_prefs())
    if inbox.get("count"):
        print(
            f"[inbox] landed {inbox.get('count')} · cooking {inbox.get('cooking') or []}",
            flush=True,
        )
    elif inbox.get("skipped_unsettled"):
        print(f"[inbox] waiting to settle {inbox.get('skipped_unsettled')}", flush=True)
    return {"ok": True, "fired": results, "due_count": len(due), "inbox": inbox}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sesefus alarm daemon")
    ap.add_argument("--alarms", type=Path, default=DEFAULT_ALARMS)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--poll", type=int, default=20)
    ap.add_argument("--dry-run-launch", action="store_true", help="resolve recorder, do not spawn GUI")
    ap.add_argument("--force-due", default="", help="force fire window id (smoke)")
    ap.add_argument("--auto-record", action="store_true", help="legacy: open designated on fire (default on fire always opens)")
    args = ap.parse_args()

    print(
        f"[daemon] alarms={args.alarms} · poll={args.poll}s · "
        f"BYO recorder · no scanner host",
        flush=True,
    )
    while True:
        summary = run_once(
            alarms_path=args.alarms,
            dry_run_launch=args.dry_run_launch,
            force_due_id=args.force_due or None,
        )
        if not summary.get("ok"):
            print(json.dumps(summary), file=sys.stderr)
            return 1
        if args.once or args.force_due:
            print(json.dumps({"ok": True, "summary": summary}, default=str))
            return 0
        time.sleep(max(5, args.poll))


if __name__ == "__main__":
    raise SystemExit(main())
