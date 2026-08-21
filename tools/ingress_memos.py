#!/usr/bin/env python3
"""Scan discovered memo roots and ingress via DualWriter."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dual_writer import AUDIO_EXT, DualWriter
from sesefus_config import load_config

def default_roots() -> list[Path]:
    configured = [Path(r) for r in load_config().get("memo_roots", [])]
    if configured:
        return configured
    home = Path.home()
    repo = Path(__file__).resolve().parent.parent
    return [
        home / "OneDrive" / "src" / "Documents" / "Sound Recordings",
        home / "Documents" / "Sound Recordings",
        repo / "aurgio" / "recordings",
        repo / "aurgio" / "transcript",
    ]


def paths_from_manifests(root: Path) -> list[Path]:
    out: list[Path] = []
    if not root.is_dir():
        return out
    for manifest in root.glob("*.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for key in ("sourcePath",):
            sp = data.get("source", {}).get(key)
            if sp and Path(sp).exists():
                out.append(Path(sp))
        copied = data.get("audio", {}).get("copiedRawPath")
        if copied and Path(copied).exists():
            out.append(Path(copied))
    return out


def collect_audio_files(roots: list[Path]) -> list[Path]:
    seen: set[str] = set()
    files: list[Path] = []

    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() in AUDIO_EXT:
            key = str(root.resolve())
            if key not in seen:
                seen.add(key)
                files.append(root)
            continue
        if root.name == "transcript" and root.is_dir():
            for p in paths_from_manifests(root):
                key = str(p.resolve())
                if key not in seen:
                    seen.add(key)
                    files.append(p)
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXT:
                key = str(path.resolve())
                if key not in seen:
                    seen.add(key)
                    files.append(path)
    return sorted(files, key=lambda p: p.stat().st_mtime)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingress historical audio memos into T:/Archive")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--root", action="append", default=[])
    args = parser.parse_args()

    roots = [Path(r) for r in args.root] if args.root else default_roots()
    files = collect_audio_files(roots)
    if args.limit > 0:
        files = files[: args.limit]

    print(f"Found {len(files)} audio file(s) across {len(roots)} root(s)")
    writer = DualWriter(dry_run=args.dry_run)

    ingested = 0
    for f in files:
        try:
            seq = writer.ingest_file(f)
            if seq is not None:
                ingested += 1
        except Exception as exc:  # noqa: BLE001 — batch ingress reports per-file errors
            print(f"[error] {f}: {exc}")

    print(f"Done. ingested={ingested} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())