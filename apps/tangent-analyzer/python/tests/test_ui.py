#!/usr/bin/env python3
"""Chrome + role split. Drive shipped helpers. Tk window is not required."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
APP = HERE.parent
sys.path.insert(0, str(HERE))

from ta_ui import (  # noqa: E402
    LOWER_PLATE_LABEL,
    PLATE_LABEL,
    TA_BAT,
    TA_UI_BAT,
    is_silent,
    load_recent_dir,
    parse_device_list,
    parse_seconds,
    pick_default_device,
    record_clicks_to_seconds,
    save_recent_dir,
)


class TestTaChrome(unittest.TestCase):
    def test_launch_bats_exist(self):
        self.assertTrue(TA_BAT.is_file(), TA_BAT)
        self.assertTrue(TA_UI_BAT.is_file(), TA_UI_BAT)

    def test_lower_plate_is_tangent_analysis_not_transcription(self):
        self.assertEqual(PLATE_LABEL, "tangent analysis")
        self.assertEqual(LOWER_PLATE_LABEL, "tangent analysis")
        src = (HERE / "ta_ui.py").read_text(encoding="utf-8")
        self.assertIn('text=LOWER_PLATE_LABEL', src)
        self.assertIn('PLATE_LABEL = "tangent analysis"', src)
        self.assertNotIn('ttk.Label(pad, text="transcription"', src)
        self.assertIn('ttk.Label(pad, text="paste"', src)
        self.assertIn("self.wave = tk.Canvas", src)
        self.assertIn("record clicks  1=10s  2=20s  3=30s  4=40s", src)
        self.assertIn('text="log"', src)
        self.assertIn('text="input"', src)
        self.assertIn('ink_button(dirrow, "change"', src)
        self.assertIn("stop / send", src)

    def test_paste_surface_and_record_chrome_in_source(self):
        src = (HERE / "ta_ui.py").read_text(encoding="utf-8")
        self.assertIn("self.paste = plate", src)
        self.assertIn("paste_text", src)
        self.assertIn("record   1–4 clicks", src)
        self.assertIn("voice prompt", src)

    def test_record_clicks_cap_at_40s(self):
        self.assertEqual(record_clicks_to_seconds(1), 10)
        self.assertEqual(record_clicks_to_seconds(2), 20)
        self.assertEqual(record_clicks_to_seconds(3), 30)
        self.assertEqual(record_clicks_to_seconds(4), 40)
        self.assertEqual(record_clicks_to_seconds(9), 40)
        self.assertEqual(record_clicks_to_seconds(0), 10)

    def test_parse_seconds_and_devices(self):
        self.assertEqual(parse_seconds(""), 10)
        self.assertEqual(parse_seconds("30"), 30)
        self.assertEqual(parse_seconds("999"), 40)
        text = (
            "[0] Microphone (Maono AU-PM421)\n"
            "[1] Stereo Mix (Realtek)  (current)\n"
            "current_index=1\n"
        )
        devices, current = parse_device_list(text)
        self.assertEqual(current, 1)
        self.assertEqual(pick_default_device(devices, current=1), 0)

    def test_recent_dir_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td) / "ta"
            folder.mkdir()
            state = Path(td) / "ta-ui.json"
            save_recent_dir(folder, state)
            self.assertEqual(load_recent_dir(state), folder.resolve())

    def test_silence_detect(self):
        self.assertTrue(is_silent(b""))
        self.assertTrue(is_silent(b"\x00\x00" * 200))
        loud = b"\x00\x00" * 50 + b"\x00\x40" + b"\x00\x00" * 50
        self.assertFalse(is_silent(loud))

    def test_clip_tree_not_this_app(self):
        clip_ui = APP.parent / "journal-clip" / "python" / "clip_ui.py"
        self.assertTrue(clip_ui.is_file())
        clip_src = clip_ui.read_text(encoding="utf-8")
        self.assertIn('text="transcription"', clip_src)
        self.assertNotIn("tangent analysis", clip_src)


if __name__ == "__main__":
    unittest.main()
