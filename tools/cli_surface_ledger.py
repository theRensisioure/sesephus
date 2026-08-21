#!/usr/bin/env python3
"""CLI surface ledger — list / show / register operator entry points.

SSOT: docs/cli_surface.jsonl (append-only).
Human face: docs/CLI_SURFACE_LEDGER.md
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEDGER = REPO / "docs" / "cli_surface.jsonl"
HUMAN = REPO / "docs" / "CLI_SURFACE_LEDGER.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_rows(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"warn: skip line {i}: {e}", file=sys.stderr)
    return rows


def latest_by_id(rows: list[dict]) -> list[dict]:
    """Last row wins per id (allows status supersede via append)."""
    by: dict[str, dict] = {}
    for r in rows:
        rid = r.get("id")
        if rid:
            by[rid] = r
    return list(by.values())


def cmd_list(args: argparse.Namespace) -> int:
    rows = latest_by_id(load_rows())
    if args.product:
        rows = [r for r in rows if r.get("product") == args.product]
    if args.active_only:
        rows = [r for r in rows if r.get("status", "active") == "active"]
    rows.sort(key=lambda r: (r.get("product") or "", r.get("name") or "", r.get("id") or ""))

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0

    if not rows:
        print("(no surfaces — empty ledger or filter)")
        return 0

    cur_prod = None
    for r in rows:
        prod = r.get("product") or "?"
        if prod != cur_prod:
            cur_prod = prod
            print(f"\n## {prod}")
        st = r.get("status", "active")
        mat = r.get("maturity") or ""
        mark = "" if st == "active" else f" [{st}]"
        print(f"- {r.get('name')}  ({r.get('id')}){mark}  {mat}")
        print(f"  cwd: {r.get('cwd', '.')}")
        print(f"  run: {r.get('invoke')}")
        if r.get("purpose"):
            print(f"  why: {r['purpose']}")
    print()
    print(f"{len(rows)} surface(s)  ·  ledger {LEDGER.relative_to(REPO)}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    rows = latest_by_id(load_rows())
    hit = next((r for r in rows if r.get("id") == args.id), None)
    if not hit:
        print(f"not found: {args.id}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(hit, indent=2, ensure_ascii=False))
    else:
        for k in (
            "id", "product", "name", "kind", "path", "cwd", "invoke",
            "purpose", "maturity", "stage", "status", "flags", "outputs", "ts",
        ):
            if k in hit and hit[k] is not None:
                print(f"{k}: {hit[k]}")
    return 0


def cmd_products(args: argparse.Namespace) -> int:
    rows = latest_by_id(load_rows())
    counts: dict[str, int] = {}
    for r in rows:
        if args.active_only and r.get("status", "active") != "active":
            continue
        p = r.get("product") or "?"
        counts[p] = counts.get(p, 0) + 1
    for p in sorted(counts):
        print(f"{p}\t{counts[p]}")
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    existing = latest_by_id(load_rows())
    if any(r.get("id") == args.id for r in existing) and not args.force:
        print(
            f"id {args.id!r} already exists. use --force to append superseding row.",
            file=sys.stderr,
        )
        return 1

    flags = [f.strip() for f in (args.flags or "").split(",") if f.strip()]
    outputs = [o.strip() for o in (args.outputs or "").split(",") if o.strip()]
    row = {
        "id": args.id,
        "ts": utc_now(),
        "product": args.product,
        "name": args.name,
        "kind": args.kind,
        "path": args.path,
        "cwd": args.cwd,
        "invoke": args.invoke,
        "purpose": args.purpose,
        "maturity": args.maturity,
        "stage": args.stage,
        "flags": flags,
        "outputs": outputs,
        "status": args.status,
    }

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, separators=(",", ":"), ensure_ascii=False)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    print(f"appended {args.id} → {LEDGER.relative_to(REPO)}")
    print(f"run: {args.invoke}")
    print(f"note: refresh {HUMAN.relative_to(REPO)} quick list if this is operator-facing")
    return 0


def cmd_path(_: argparse.Namespace) -> int:
    print(LEDGER)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Sesefus CLI surface ledger (docs/cli_surface.jsonl)"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="list surfaces (latest per id)")
    pl.add_argument("--product", default=None)
    pl.add_argument("--active-only", action="store_true")
    pl.add_argument("--json", action="store_true")
    pl.set_defaults(func=cmd_list)

    ps = sub.add_parser("show", help="show one surface by id")
    ps.add_argument("id")
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_show)

    pp = sub.add_parser("products", help="product counts")
    pp.add_argument("--active-only", action="store_true")
    pp.set_defaults(func=cmd_products)

    pr = sub.add_parser("register", help="append a new surface row")
    pr.add_argument("--id", required=True)
    pr.add_argument("--product", required=True)
    pr.add_argument("--name", required=True)
    pr.add_argument("--kind", default="python", choices=("python", "bat", "ps1", "zig", "other"))
    pr.add_argument("--path", required=True, help="repo-relative entry file")
    pr.add_argument("--cwd", default=".", help="run-from directory (repo-relative)")
    pr.add_argument("--invoke", required=True, help="copy-paste command")
    pr.add_argument("--purpose", default="")
    pr.add_argument("--maturity", default="spike")
    pr.add_argument("--stage", default=None)
    pr.add_argument("--flags", default="", help="comma-separated flags")
    pr.add_argument("--outputs", default="", help="comma-separated outputs")
    pr.add_argument("--status", default="active")
    pr.add_argument("--force", action="store_true", help="allow superseding append for same id")
    pr.set_defaults(func=cmd_register)

    sub.add_parser("path", help="print ledger file path").set_defaults(func=cmd_path)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
