#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from hop_prefs import load_prefs, save_prefs  # noqa: E402


class TestHopPrefs(unittest.TestCase):
    def test_defaults_all_off(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hop-prefs.json"
            got = load_prefs(p)
            self.assertFalse(got["auto_land"])
            self.assertFalse(got["auto_cook"])
            self.assertFalse(got["show_cue_page"])

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hop-prefs.json"
            save_prefs({"auto_cook": True, "show_cue_page": False}, p)
            got = load_prefs(p)
            self.assertTrue(got["auto_cook"])
            self.assertFalse(got["show_cue_page"])
            self.assertFalse(got["auto_land"])


if __name__ == "__main__":
    unittest.main()
