#!/usr/bin/env python3
"""Rebuild embedded #atlas-data in sesefus-atlas.html from the installed tree."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATLAS_HTML = Path(__file__).resolve().parent / "sesefus-atlas.html"
DATA_TAG = re.compile(
    r'(<script id="atlas-data" type="application/json">)(.*?)(</script>)',
    re.DOTALL,
)

START_HERE = {
    "core": "Zig host (sesephus) — CLI, vault, rhythm, discovery",
    "audio": "Voice capture pipeline — pairs with voice.bat",
    "dashboard": "React UI + dashboard_server.py API",
    "tools": "Maintenance scripts, ETDI, atlas builder",
    "docs": "Operator guides and session notes",
    "prompts": "LeadLogic / Jetstream prompt vendoring",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def in_git() -> bool:
    try:
        run("git", "rev-parse", "--git-dir")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def top_dir(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "·root"


def ext_of(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    if name.startswith(".") and name.count(".") == 1:
        return name[1:].lower()
    if "." in name:
        return name.rsplit(".", 1)[-1].lower()
    return name.lower()


def collect_files() -> list[dict]:
    lines = run("git", "ls-files", "-z").split("\0")
    files = sorted(p for p in lines if p)
    return [{"p": p, "e": ext_of(p), "t": top_dir(p)} for p in files]


def parse_decorations(raw: str) -> list[str]:
    if not raw:
        return []
    refs = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.startswith("HEAD -> "):
            refs.append(part)
        elif "/" in part or part.isidentifier():
            refs.append(part)
    return refs


def collect_commits() -> list[dict]:
    rows = []
    log = run(
        "git", "log", "--all",
        r"--format=%H|%h|%P|%ct|%D|%s",
    )
    for line in log.splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 5)
        if len(parts) < 6:
            continue
        full, short, parents, ts, deco, msg = parts
        parent_list = [p for p in parents.split() if p]
        rows.append(
            {
                "h": full,
                "s": short,
                "p": parent_list,
                "t": int(ts),
                "r": parse_decorations(deco),
                "g": [],
                "m": msg,
            }
        )

    by_hash = {c["h"]: c for c in rows}
    for ref in run("git", "for-each-ref", "--format=%(refname:short)").splitlines():
        if not ref.startswith("archive/"):
            continue
        tip = run("git", "rev-parse", ref)
        if tip in by_hash:
            by_hash[tip]["g"].append(ref)
    return rows


def collect_refs() -> list[dict]:
    refs = []
    for line in run("git", "for-each-ref", r"--format=%(refname:short)|%(objectname)").splitlines():
        if not line or "|" not in line:
            continue
        name, obj = line.split("|", 1)
        if name.startswith("origin/") and name.count("/") > 2:
            continue
        refs.append({"n": name, "o": obj})
    return sorted(refs, key=lambda r: r["n"])


def build_guide(files: list[dict], repo: str) -> str:
    tops: dict[str, int] = defaultdict(int)
    for f in files:
        tops[f["t"]] += 1
    ranked = sorted(tops.items(), key=lambda kv: (-kv[1], kv[0]))
    lines = [
        f"{repo} — {len(files)} tracked files across {len(tops)} top-level areas.",
        "Open tools/atlas/sesefus-atlas.html for the structural map (zero inference).",
    ]
    for area, count in ranked[:6]:
        hint = START_HERE.get(area, "")
        suffix = f" — {hint}" if hint else ""
        lines.append(f"  • {area}: {count} files{suffix}")
    return "\n".join(lines)


def patch_html(payload: dict) -> None:
    text = ATLAS_HTML.read_text(encoding="utf-8")
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    if not DATA_TAG.search(text):
        raise SystemExit(f"atlas-data block not found in {ATLAS_HTML}")
    updated = DATA_TAG.sub(lambda m: f"{m.group(1)}{blob}{m.group(3)}", text, count=1)
    ATLAS_HTML.write_text(updated, encoding="utf-8", newline="\r\n")


def main() -> int:
    if not in_git():
        print("atlas build: not a git checkout — skipped", file=sys.stderr)
        return 0

    files = collect_files()
    payload = {
        "repo": ROOT.name,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "guide": build_guide(files, ROOT.name),
        "files": files,
        "commits": collect_commits(),
        "refs": collect_refs(),
    }
    patch_html(payload)
    print(
        f"atlas: {payload['repo']} — {len(files)} files, "
        f"{len(payload['commits'])} commits → {ATLAS_HTML.name}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())