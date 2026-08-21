#!/usr/bin/env python3
"""Dry entry: inject messy objective text, mint a house goal packet, persist."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mint import EmptyInputError, mint, render_packet, write_packet

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = Path.home() / ".sesefus" / "goal-minter"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="goal-minter — mint a house 3-Q goal packet from messy text (no mic)",
    )
    ap.add_argument("--say", help="messy objective text (dry; no microphone)")
    ap.add_argument("--text-file", type=Path, help="read objective text from a file")
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory that receives intent/interview.md",
    )
    ap.add_argument("--ui", action="store_true", help="open the goal-minting window")
    args = ap.parse_args(argv)

    if args.ui:
        from ui import run_window

        return run_window()

    text = _load_text(args)
    if text is None:
        ap.print_help(sys.stderr)
        print(
            "\nerror: pass --say TEXT or --text-file PATH (no microphone)",
            file=sys.stderr,
        )
        return 2

    out_dir = args.out if args.out is not None else DEFAULT_OUT
    try:
        packet = mint(text)
    except EmptyInputError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    dest = write_packet(packet, out_dir)
    body = render_packet(packet)
    print(body)
    print(f"wrote {dest}", file=sys.stderr)
    return 0


def _load_text(args: argparse.Namespace) -> str | None:
    if args.say is not None and args.text_file is not None:
        raise SystemExit("error: use --say or --text-file, not both")
    if args.say is not None:
        return args.say
    if args.text_file is not None:
        path = Path(args.text_file)
        return path.read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


if __name__ == "__main__":
    raise SystemExit(main())
