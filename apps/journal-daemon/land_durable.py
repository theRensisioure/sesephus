#!/usr/bin/env python3
"""Land one journal stamp into durable-archive via existing durable_land.land()."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE") or Path.home())
HERE = Path(__file__).resolve().parent
SCANNER_SCRIPTS = Path(os.environ.get("USERPROFILE") or HOME) / "artifact-scanner" / "scripts"
CAPTURE = HOME / "test-write" / "journal"
LANDS = HOME / "jwrangle" / "durable-archive" / "lands"

if str(SCANNER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCANNER_SCRIPTS))

import durable_land  # noqa: E402  — artifact-scanner/scripts, not the grok-skill fork


def _norm(p: Path) -> str:
    try:
        return str(p.resolve()).lower()
    except OSError:
        return str(p).lower()


def landed_sources(lands: Path = LANDS) -> set[str]:
    out: set[str] = set()
    if not lands.is_dir():
        return out
    for d in lands.iterdir():
        man = d / "MANIFEST.json"
        if not man.is_file():
            continue
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        src = data.get("source")
        if src:
            out.add(_norm(Path(str(src))))
    return out


def has_audio_and_meta(stamp_dir: Path) -> bool:
    if not (stamp_dir / "meta.json").is_file():
        return False
    return any(p.is_file() and p.name.lower().startswith("audio.") for p in stamp_dir.iterdir())


def pending_stamps(capture: Path = CAPTURE, lands: Path = LANDS) -> list[Path]:
    already = landed_sources(lands)
    found: list[Path] = []
    if not capture.is_dir():
        return found
    for d in sorted(capture.iterdir()):
        if not d.is_dir() or d.name.startswith("_"):
            continue
        if not has_audio_and_meta(d):
            continue
        if _norm(d) in already:
            continue
        found.append(d)
    return found


def land_one(src: Path, *, note: str = "", label: str = "") -> dict:
    stamp = src.name
    result = durable_land.land(
        src=src,
        from_capture=False,
        move=False,
        note=note or f"journal {stamp}",
        label=label or f"journal-{stamp}",
    )
    if result.get("deleted"):
        result = dict(result)
        result["ok"] = False
        result["error"] = f"refusing land with deleted={result.get('deleted')}"
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Copy-land journal stamps into durable-archive")
    ap.add_argument("--src", default="", help="one journal stamp dir")
    ap.add_argument(
        "--pending",
        action="store_true",
        help="land unlanded audio+meta journal stamps (default when no --src)",
    )
    ap.add_argument("--limit", type=int, default=1, help="max stamps for --pending (default 1)")
    args = ap.parse_args(argv)

    if args.src:
        src = Path(args.src).expanduser()
        if not src.is_dir():
            print(json.dumps({"ok": False, "error": f"not a dir: {src}"}))
            return 1
        if not has_audio_and_meta(src):
            print(json.dumps({"ok": False, "error": "skip: need audio.* + meta.json", "src": str(src)}))
            return 1
        if _norm(src) in landed_sources():
            print(json.dumps({"ok": True, "skipped": "already landed", "src": str(src)}))
            return 0
        out = land_one(src)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0 if out.get("ok") else 1

    # Bare run = --pending (the dogfood door).
    pending = pending_stamps()
    if not pending:
        print("no pending journal land — only audio+meta stamps that are not already in durable-archive")
        print(json.dumps({"ok": True, "landed": 0, "pending": 0, "note": "no unlanded audio+meta journal stamps"}))
        return 0
    results = []
    for src in pending[: max(1, args.limit)]:
        results.append(land_one(src))
    ok = all(r.get("ok") and not r.get("deleted") for r in results)
    print(f"landed {len(results)} · pending was {len(pending)}")
    print(json.dumps({"ok": ok, "landed": len(results), "results": results}, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
