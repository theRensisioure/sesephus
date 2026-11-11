"""Reject a nested journal-clip clone. A worktree gitlink is allowed."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ledger.clones import nested_clones


def check_flat(root: Path) -> tuple[int, str]:
    bad = nested_clones(root)
    if bad:
        lines = ["flat workspace: nested clone"] + [str(path) for path in bad]
        return 1, "\n".join(lines) + "\n"
    return 0, "flat workspace: clean\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ledger.flat_workspace")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    code, text = check_flat(args.root)
    stream = sys.stderr if code else sys.stdout
    stream.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
