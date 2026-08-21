"""Shared SSFS drive-mapping reader for tools/ scripts.

Mirrors ssfs/storage/paths.js: never hardcode drive letters here or in any
tool — read them from ssfs/drive-mapping.json, the single source of truth.
"""
from __future__ import annotations

import json
from pathlib import Path

MAPPING_FILE = Path(__file__).resolve().parent.parent / "ssfs" / "drive-mapping.json"


def load_mapping() -> dict:
    return json.loads(MAPPING_FILE.read_text(encoding="utf-8"))


def get_archive_root() -> Path:
    mapping = load_mapping()
    letter = mapping["drives"]["coldArchive"]["letter"]
    sub = mapping["paths"].get("archiveRoot", "Archive\\sesefhus")
    return Path(f"{letter}\\{sub}")


if __name__ == "__main__":
    root = get_archive_root()
    print(f"Reading: {MAPPING_FILE}")
    print(f"archive root resolves to: {root}")
    print(f"exists on disk right now: {root.exists()}")

