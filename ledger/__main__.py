"""Write a flat Event Ledger JSON for one transcript."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ledger.parse import build_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ledger")
    parser.add_argument("transcript", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    text = args.transcript.read_text(encoding="utf-8")
    payload = json.dumps(build_ledger(text), indent=2) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
