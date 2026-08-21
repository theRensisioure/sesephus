#!/usr/bin/env python3
"""Multi-day review of journal captures + durable lands (BA pattern glance)."""
from __future__ import annotations

import json
import os
from pathlib import Path

HOME = Path(os.environ.get("USERPROFILE") or Path.home())
CAPTURE = HOME / "test-write" / "journal"
LANDS = HOME / "jwrangle" / "durable-archive" / "lands"


def load_json(p: Path) -> dict:
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_meta(p: Path) -> dict:
    return load_json(p / "meta.json")


def load_manifest(p: Path) -> dict:
    return load_json(p / "MANIFEST.json")


def land_fields(d: Path) -> dict:
    """Prefer MANIFEST label/note/file_count; BA fields from meta.json when present."""
    man = load_manifest(d)
    meta = {}
    for m in d.rglob("meta.json"):
        meta = load_json(m)
        if meta:
            break
    return {
        "activity": meta.get("activity"),
        "mood": meta.get("mood"),
        "pleasure": meta.get("pleasure"),
        "mastery": meta.get("mastery"),
        "sampled_by": meta.get("sampled_by"),
        "label": man.get("label") or "",
        "note": man.get("note") or "",
        "file_count": man.get("file_count"),
        "has_meta": bool(meta),
    }


def collect_rows(
    capture: Path = CAPTURE, lands: Path = LANDS, land_limit: int = 30
) -> list[tuple[str, str, dict]]:
    rows: list[tuple[str, str, dict]] = []
    if capture.is_dir():
        for d in sorted(capture.iterdir()):
            if not d.is_dir() or d.name.startswith("_"):
                continue
            rows.append(("capture", d.name, load_meta(d)))
    if lands.is_dir():
        n = 0
        for d in sorted(lands.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            rows.append(("land", d.name, land_fields(d)))
            n += 1
            if n >= land_limit:
                break
    return rows


def format_row(src: str, name: str, meta: dict) -> str:
    if src == "land" and not meta.get("has_meta"):
        note = (meta.get("note") or "").replace("\n", " ").strip()
        label = meta.get("label") or "—"
        n = meta.get("file_count")
        files = f"files={n}" if n is not None else "files=?"
        return f"{name} · land · {label} · {note} · {files}"
    return (
        f"{name} · {src} · {meta.get('activity')} · "
        f"m={meta.get('mood')} p={meta.get('pleasure')} "
        f"k={meta.get('mastery')} · {meta.get('sampled_by')}"
    )


def main() -> int:
    rows = collect_rows()
    print("# journal review")
    print(f"# rows {len(rows)} · capture={CAPTURE} · lands={LANDS}")
    print("# stamp · source · activity · mood · pleasure · mastery · sampled_by")
    print("# land without meta: stamp · land · label · note · files")
    for src, name, meta in rows:
        print(format_row(src, name, meta))
    print(
        "\n# BA glance (manual): long null moods + empty activity ≈ inactive "
        "stretch; look for small lifts. Lands with only a label/note are cue "
        "packs, not broken scores."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
