#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import ui_serve as us  # noqa: E402


class TestPlateLatest(unittest.TestCase):
    def test_reads_last_pair_snippet(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = root / "raw.txt"
            raw.write_text("Here we go. Volume as grain.\n", encoding="utf-8")
            ap = root / "ARRAY.json"
            ap.write_text(
                json.dumps(
                    {
                        "count": 1,
                        "audio": [{"id": "X", "os_name": "Recording (19).m4a"}],
                        "text": [{"id": "X", "path": str(raw), "dtype": "hop.audio_text", "chars": 20}],
                        "dtypes": {"hop.audio_text": "pair"},
                    }
                ),
                encoding="utf-8",
            )
            with mock.patch.object(us, "ARRAY_PATH", ap):
                got = us.plate_latest()
            self.assertTrue(got["ok"])
            self.assertEqual(got["count"], 1)
            self.assertEqual(got["pair"]["dtype"], "hop.audio_text")
            self.assertIn("Volume", got["pair"]["snippet"])


if __name__ == "__main__":
    unittest.main()
