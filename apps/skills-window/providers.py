"""Load provider skill-dir registry. One JSON object per provider."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_FILE = HERE / "providers.json"


def expand_path(raw: str) -> Path:
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty path")
    s = os.path.expandvars(s)
    s = os.path.expanduser(s)
    return Path(s)


def _norm_root(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    rid = str(raw.get("id") or "").strip()
    path = str(raw.get("path") or "").strip()
    if not rid or not path:
        return None
    label = str(raw.get("label") or rid).strip()
    return {
        "id": rid,
        "label": label,
        "path": path,
        "optional": bool(raw.get("optional")),
    }


def _norm_provider(raw: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    pid = str(raw.get("id") or "").strip()
    if not pid:
        return None
    roots: list[dict[str, Any]] = []
    for item in raw.get("roots") or []:
        r = _norm_root(item)
        if r:
            roots.append(r)
    if not roots:
        return None
    return {
        "id": pid,
        "label": str(raw.get("label") or pid).strip(),
        "enabled": bool(raw.get("enabled", True)),
        "roots": roots,
    }


def load_registry(path: Path | None = None) -> dict[str, Any]:
    src = path or DEFAULT_FILE
    if not src.is_file():
        return {"version": 1, "providers": [], "path": str(src), "error": "missing providers.json"}
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return {"version": 1, "providers": [], "path": str(src), "error": str(e)}
    if not isinstance(data, dict):
        return {"version": 1, "providers": [], "path": str(src), "error": "registry is not an object"}
    out: list[dict[str, Any]] = []
    for item in data.get("providers") or []:
        p = _norm_provider(item)
        if p:
            out.append(p)
    return {
        "version": int(data.get("version") or 1),
        "providers": out,
        "path": str(src),
        "mtime": src.stat().st_mtime,
    }


def enabled_providers(reg: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in (reg.get("providers") or []) if p.get("enabled")]


def resolve_root(root: dict[str, Any]) -> dict[str, Any]:
    raw = root["path"]
    try:
        resolved = expand_path(raw)
        exists = resolved.is_dir()
        err = None
    except (OSError, ValueError) as e:
        resolved = Path(raw)
        exists = False
        err = str(e)
    return {
        **root,
        "resolved": str(resolved),
        "exists": exists,
        "error": err,
    }


def allowed_bases(reg: dict[str, Any]) -> list[Path]:
    bases: list[Path] = []
    for p in enabled_providers(reg):
        for r in p.get("roots") or []:
            info = resolve_root(r)
            if info["exists"]:
                bases.append(Path(info["resolved"]).resolve())
    return bases


def path_allowed(target: Path, bases: list[Path]) -> bool:
    try:
        t = target.resolve()
    except OSError:
        return False
    if not t.exists():
        return False
    for b in bases:
        try:
            t.relative_to(b)
            return True
        except ValueError:
            continue
    return False


def save_registry(reg: dict[str, Any], path: Path | None = None) -> None:
    src = path or DEFAULT_FILE
    payload = {
        "version": int(reg.get("version") or 1),
        "providers": list(reg.get("providers") or []),
    }
    src.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_provider(raw: dict[str, Any], path: Path | None = None) -> dict[str, Any]:
    """Append or replace a provider by id. Returns the new registry."""
    src = path or DEFAULT_FILE
    p = _norm_provider(raw)
    if not p:
        raise ValueError("need id + at least one root with id and path")
    reg = load_registry(src)
    if reg.get("error") and "missing" not in str(reg.get("error")):
        raise ValueError(reg["error"])
    providers = [x for x in (reg.get("providers") or []) if x["id"] != p["id"]]
    providers.append(p)
    reg["providers"] = providers
    save_registry(reg, src)
    return load_registry(src)
