"""Named domains resolve only to absolute paths from manifest.json."""

from __future__ import annotations

import json
from pathlib import Path


def _has_parent_segment(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return any(part == ".." for part in normalized.split("/"))


def load_domains(manifest_path: Path) -> dict[str, str]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = data.get("domains")
    if not isinstance(raw, dict) or not raw:
        raise ValueError("manifest.json needs a domains object")
    out: dict[str, str] = {}
    for name, value in raw.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise ValueError(f"domain {name!r} must be a string path")
        if _has_parent_segment(value):
            raise ValueError(f"domain {name} uses a forbidden parent segment")
        path = Path(value)
        if not path.is_absolute():
            raise ValueError(f"domain {name} is not absolute")
        out[name] = value
    return out


def resolve_domain(name: str, domains: dict[str, str]) -> str:
    if name not in domains:
        raise KeyError(name)
    value = domains[name]
    if _has_parent_segment(value) or not Path(value).is_absolute():
        raise ValueError(name)
    return value
