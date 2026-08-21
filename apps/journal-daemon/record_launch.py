#!/usr/bin/env python3
"""CLI: open designated BYO recorder (same path as UI Record + alarm fire)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from capture_config import load_config  # noqa: E402
from launcher import launch_designated  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Open designated Sesefus recorder")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    try:
        out = launch_designated(cfg=load_config(), dry_run=args.dry_run)
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 1
    print(json.dumps(out, indent=2))
    return 0 if out.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
