"""Drive shipped journal/rhythm handlers and a Clippers tape fixture.

Zig unit tests in commands/journal.zig and commands/rhythm.zig are the
shipped-code bar. This module writes the same schema=1 tape row those
tests consume, then runs `zig test` on those files (not a reimplementation).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parent
CLIPPERS_ROOT = r"C:\dev\journal-clippers\audio-journal-system"
FIXTURE_TEXT = "spoken take kept after shred"
CANNED = (
    "Starting audio journaling session",
    "Reviewing recent audio entries",
    "Generating a stoic reflection prompt",
    "use voice.bat (the real journal loop)",
)


def fixture_row() -> dict:
    return {
        "id": "1",
        "date": "2026-09-04",
        "time": "12:00:00",
        "kind": "dump",
        "score": 0.0,
        "text": FIXTURE_TEXT,
        "structured": FIXTURE_TEXT,
        "title": "",
        "source": "clip",
        "schema": 1,
        "extra": {},
    }


def write_fixture(path: Path) -> None:
    path.write_text(json.dumps(fixture_row()) + "\n", encoding="utf-8")


def test_fixture_tape_is_schema_1_text_without_wav(tmp_path: Path | None = None) -> Path:
    root = tmp_path if tmp_path is not None else CORE
    tape = Path(root) / "takes.jsonl"
    write_fixture(tape)
    row = json.loads(tape.read_text(encoding="utf-8").splitlines()[0])
    assert row["schema"] == 1
    assert row["text"] == FIXTURE_TEXT
    assert not (Path(root) / "take.wav").exists()
    return tape


def test_shipped_zig_journal_and_rhythm_handlers() -> None:
    tape = test_fixture_tape_is_schema_1_text_without_wav()
    try:
        for src in (
            "src/commands/journal.zig",
            "src/commands/rhythm.zig",
            "src/commands/help_text.zig",
        ):
            r = subprocess.run(
                ["zig", "test", src],
                cwd=CORE,
                capture_output=True,
                text=True,
                timeout=120,
            )
            out = (r.stdout or "") + (r.stderr or "")
            assert r.returncode == 0, f"{src} failed:\n{out}"
            for banned in CANNED:
                assert banned not in out
    finally:
        if tape.exists() and tape.parent == CORE:
            tape.unlink()


def test_journal_source_points_at_clippers_not_voice_bat_loop() -> None:
    src = (CORE / "src/commands/journal.zig").read_text(encoding="utf-8")
    help_src = (CORE / "src/commands/help_text.zig").read_text(encoding="utf-8")
    # Zig source stores Windows paths with escaped backslashes.
    assert "journal-clippers" in src and "audio-journal-system" in src
    assert CLIPPERS_ROOT.replace("\\", "\\\\") in src or CLIPPERS_ROOT in src
    assert "journal-clippers" in help_src and "audio-journal-system" in help_src
    assert "takes.jsonl" in src
    assert "schema" in src
    prod = src.split("\ntest ")[0]
    help_prod = help_src.split("\ntest ")[0]
    for banned in CANNED:
        assert banned not in prod
        assert banned not in help_prod


if __name__ == "__main__":
    test_fixture_tape_is_schema_1_text_without_wav()
    test_journal_source_points_at_clippers_not_voice_bat_loop()
    test_shipped_zig_journal_and_rhythm_handlers()
    print("[SUCCESS] shipped journal/rhythm stub tests passed")
    sys.exit(0)
