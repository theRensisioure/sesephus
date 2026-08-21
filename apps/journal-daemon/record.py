#!/usr/bin/env python3
"""Audio journal capture → ~/test-write/journal/<stamp>/

The capture IS the audio file. Meta is a sidecar. Text is never a stand-in.
Transcription stays parked — land the raw clip.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE") or Path.home())
CAPTURE = HOME / "test-write" / "journal"


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def _ext_for(name: str, mime: str) -> str:
    n = (name or "").lower()
    m = (mime or "").lower()
    if n.endswith(".wav") or "wav" in m:
        return ".wav"
    if n.endswith(".webm") or "webm" in m:
        return ".webm"
    if n.endswith(".ogg") or "ogg" in m:
        return ".ogg"
    if n.endswith(".mp3") or "mpeg" in m:
        return ".mp3"
    if n.endswith(".m4a") or "mp4" in m:
        return ".m4a"
    return ".webm"


def write_capture(
    *,
    audio: bytes,
    audio_name: str = "audio",
    mime: str = "",
    activity: str = "",
    context: str = "",
    mood: float | None = None,
    pleasure: float | None = None,
    mastery: float | None = None,
    duration_sec: float | None = None,
    note: str = "",
    alarm_id: str = "",
    sampled_by: str = "",
) -> dict:
    if not audio:
        return {"ok": False, "error": "no audio — this is an audio journal, not a text memo"}
    sid = stamp()
    dest = CAPTURE / sid
    dest.mkdir(parents=True, exist_ok=True)
    ext = _ext_for(audio_name, mime)
    fname = "audio" + ext
    (dest / fname).write_bytes(audio)
    sampled = sampled_by or ("alarm" if alarm_id else "freeform")
    meta = {
        "stamp": sid,
        "activity": activity or None,
        "duration_sec": duration_sec,
        "context": context or None,
        "mood": mood,
        "pleasure": pleasure,
        "mastery": mastery,
        "sampled_by": sampled,
        "alarm_id": alarm_id or None,
        "note": note or "",
        "files": [fname],
        "audio": fname,
        "audio_bytes": len(audio),
        "mime": mime or None,
        "transcription": "parked",
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(dest), "stamp": sid, "meta": meta}


def main() -> int:
    ap = argparse.ArgumentParser(description="Sesefus journal record — audio required")
    ap.add_argument("--file", dest="audio_file", help="path to wav/webm/ogg clip")
    ap.add_argument("--note", default="", help="optional caption sidecar — not the capture")
    ap.add_argument("--activity", default="")
    ap.add_argument("--mood", type=float, default=None)
    ap.add_argument("--pleasure", type=float, default=None)
    ap.add_argument("--mastery", type=float, default=None)
    ap.add_argument("--context", default="")
    ap.add_argument("--duration-sec", type=float, default=None, dest="duration_sec")
    ap.add_argument("--alarm-id", default="", dest="alarm_id")
    ap.add_argument("--sampled-by", default="", dest="sampled_by")
    args = ap.parse_args()

    if not args.audio_file:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "need --file <audio> - text is not a stand-in for the journal",
                }
            ),
            file=sys.stderr,
        )
        return 2
    src = Path(args.audio_file)
    if not src.is_file():
        print(json.dumps({"ok": False, "error": f"missing audio file: {src}"}), file=sys.stderr)
        return 2
    data = write_capture(
        audio=src.read_bytes(),
        audio_name=src.name,
        activity=args.activity,
        context=args.context,
        mood=args.mood,
        pleasure=args.pleasure,
        mastery=args.mastery,
        duration_sec=args.duration_sec,
        note=args.note,
        alarm_id=args.alarm_id,
        sampled_by=args.sampled_by,
    )
    print(json.dumps(data, indent=2))
    if data.get("ok"):
        print(
            "\nLand when ready:\n"
            f'  python "%USERPROFILE%\\artifact-scanner\\scripts\\durable_land.py"'
            f' land --src "{data["path"]}" --note "journal {data["stamp"]}"',
            file=sys.stderr,
        )
    return 0 if data.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
