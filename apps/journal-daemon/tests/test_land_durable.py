#!/usr/bin/env python3
"""Pending detection + review rows for lands without meta.json."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from land_durable import has_audio_and_meta, pending_stamps  # noqa: E402
from review import collect_rows, format_row  # noqa: E402


class TestLandDurablePending(unittest.TestCase):
    def test_note_only_is_not_pending(self):
        with tempfile.TemporaryDirectory() as td:
            cap = Path(td) / "journal"
            lands = Path(td) / "lands"
            stamp = cap / "20260811-210712"
            stamp.mkdir(parents=True)
            (stamp / "NOTE.txt").write_text("note", encoding="utf-8")
            (stamp / "meta.json").write_text("{}", encoding="utf-8")
            lands.mkdir()
            self.assertFalse(has_audio_and_meta(stamp))
            self.assertEqual(pending_stamps(cap, lands), [])

    def test_already_landed_source_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            cap = Path(td) / "journal"
            lands = Path(td) / "lands"
            stamp = cap / "20260812-142752"
            stamp.mkdir(parents=True)
            (stamp / "audio.webm").write_bytes(b"webm")
            (stamp / "meta.json").write_text("{}", encoding="utf-8")
            land = lands / "20260812-142824"
            land.mkdir(parents=True)
            (land / "MANIFEST.json").write_text(
                json.dumps({"source": str(stamp)}),
                encoding="utf-8",
            )
            self.assertEqual(pending_stamps(cap, lands), [])

    def test_unlanded_audio_meta_is_pending(self):
        with tempfile.TemporaryDirectory() as td:
            cap = Path(td) / "journal"
            lands = Path(td) / "lands"
            stamp = cap / "20260814-000001"
            stamp.mkdir(parents=True)
            (stamp / "audio.wav").write_bytes(b"wav")
            (stamp / "meta.json").write_text("{}", encoding="utf-8")
            lands.mkdir()
            got = pending_stamps(cap, lands)
            self.assertEqual([p.name for p in got], ["20260814-000001"])


class TestReviewSeesLandsWithoutMeta(unittest.TestCase):
    def test_cue_pack_row_uses_label_and_note(self):
        with tempfile.TemporaryDirectory() as td:
            cap = Path(td) / "journal"
            lands = Path(td) / "lands"
            cap.mkdir()
            pack = lands / "20260814T210200Z"
            pack.mkdir(parents=True)
            (pack / "MANIFEST.json").write_text(
                json.dumps(
                    {
                        "label": "sieve-intent-read-first",
                        "note": "will-sieve archive flesh v0",
                        "file_count": 8,
                    }
                ),
                encoding="utf-8",
            )
            (pack / "REVELATION.md").write_text("x", encoding="utf-8")
            rows = collect_rows(cap, lands)
            self.assertEqual(len(rows), 1)
            src, name, meta = rows[0]
            self.assertEqual(src, "land")
            self.assertEqual(name, "20260814T210200Z")
            line = format_row(src, name, meta)
            self.assertIn("20260814T210200Z", line)
            self.assertIn("will-sieve", line)
            self.assertIn("sieve-intent-read-first", line)


if __name__ == "__main__":
    unittest.main()
