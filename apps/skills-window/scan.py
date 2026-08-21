"""Scan a provider root for skill directories (SKILL.md)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_KV = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse_frontmatter(text: str) -> dict[str, str]:
    m = _FM.match(text or "")
    if not m:
        return {}
    out: dict[str, str] = {}
    key = None
    buf: list[str] = []
    for line in m.group(1).splitlines():
        km = _KV.match(line)
        if km and not line.startswith(" "):
            if key:
                out[key] = " ".join(buf).strip()
            key = km.group(1).strip().lower()
            first = km.group(2).strip()
            if first in (">", "|", ""):
                buf = []
            else:
                buf = [_unquote(first)]
        elif key and (line.startswith("  ") or line.startswith("\t") or line.startswith("- ")):
            buf.append(line.strip().lstrip("- ").strip())
        elif key and line.strip() == "":
            continue
    if key:
        out[key] = " ".join(buf).strip()
    return out


def first_sentence(text: str, limit: int = 140) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return ""
    for sep in (". ", " — ", " – "):
        i = t.find(sep)
        if 8 <= i <= limit:
            return t[: i + 1].strip() if sep == ". " else t[:i].strip()
    if len(t) > limit:
        return t[: limit - 1].rstrip() + "…"
    return t


def scan_root(root: Path) -> list[dict[str, Any]]:
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for child in sorted(children, key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        name = child.name
        if name.startswith(".") or name.startswith("_"):
            continue
        md = child / "SKILL.md"
        if not md.is_file():
            continue
        try:
            body = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
        meta = parse_frontmatter(body)
        desc = first_sentence(meta.get("description") or meta.get("short-description") or "")
        if not desc:
            for line in body.splitlines():
                s = line.strip()
                if s.startswith("#"):
                    continue
                if s.startswith("---"):
                    continue
                if s:
                    desc = first_sentence(s)
                    break
        rows.append(
            {
                "id": name,
                "name": meta.get("name") or name,
                "description": desc,
                "path": str(child.resolve()),
                "has_scripts": (child / "scripts").is_dir(),
                "has_refs": (child / "references").is_dir(),
            }
        )
    return rows


def catalog(reg: dict[str, Any], resolve_root, enabled_providers) -> dict[str, Any]:
    providers_out: list[dict[str, Any]] = []
    total = 0
    missing = 0
    for p in enabled_providers(reg):
        roots_out: list[dict[str, Any]] = []
        skills: list[dict[str, Any]] = []
        for r in p.get("roots") or []:
            info = resolve_root(r)
            info_row = {
                "id": info["id"],
                "label": info["label"],
                "path": info["path"],
                "resolved": info["resolved"],
                "exists": info["exists"],
                "optional": info["optional"],
                "error": info.get("error"),
                "count": 0,
            }
            if info["exists"]:
                found = scan_root(Path(info["resolved"]))
                for s in found:
                    s["provider"] = p["id"]
                    s["root"] = r["id"]
                info_row["count"] = len(found)
                skills.extend(found)
                total += len(found)
            else:
                missing += 0 if info["optional"] else 1
            roots_out.append(info_row)
        providers_out.append(
            {
                "id": p["id"],
                "label": p["label"],
                "roots": roots_out,
                "skills": skills,
                "count": len(skills),
            }
        )
    return {
        "ok": True,
        "providers": providers_out,
        "total": total,
        "missing_required": missing,
        "registry": reg.get("path"),
    }
