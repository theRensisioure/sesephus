#!/usr/bin/env python3
"""Multimedia hop: cue page + optional sound/picture. Not a third app."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from alarm_core import fire_window  # noqa: E402
from hop import (  # noqa: E402
    build_open_argv,
    resolve_media,
    ride_hop,
    write_cue_page,
)


class TestHop(unittest.TestCase):
    def test_missing_media_is_absent(self):
        m = resolve_media({"sound": "C:\\nope\\missing.wav", "picture": ""})
        self.assertEqual(m["sound"], "")
        self.assertTrue(m["sound_missing"])
        self.assertFalse(m["picture_missing"])

    def test_existing_picture_rides(self):
        with tempfile.TemporaryDirectory() as td:
            pic = Path(td) / "still.png"
            pic.write_bytes(b"\x89PNG\r\n")
            m = resolve_media({"picture": str(pic)})
            self.assertEqual(m["picture"], str(pic))
            self.assertFalse(m["picture_missing"])

    def test_fire_writes_page_even_without_media(self):
        with tempfile.TemporaryDirectory() as td:
            cue_dir = Path(td) / "cues"
            r = fire_window(
                {"id": "morning", "time": "09:30", "label": "morning sample", "prompt": "say it"},
                cue_dir=cue_dir,
                now=datetime(2026, 8, 16, 9, 30, 0),
            )
            self.assertTrue(r["ok"])
            page = Path(r["page"])
            self.assertTrue(page.is_file())
            body = page.read_text(encoding="utf-8")
            self.assertIn("morning sample", body)
            self.assertIn("Sound Recorder is opening", body)
            cue = json.loads(Path(r["cue"]).read_text(encoding="utf-8"))
            self.assertEqual(cue["action"], "open_designated_recorder")
            self.assertEqual(cue["hop"]["page"], str(page))
            self.assertEqual(cue["hop"]["sound"], "")

    def test_picture_lands_in_page_sound_opens(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pic = root / "still.jpg"
            wav = root / "ding.wav"
            pic.write_bytes(b"xxxx")
            wav.write_bytes(b"RIFF")
            cue_dir = root / "cues"
            opened: list[list[str]] = []
            w = {
                "id": "midday",
                "time": "13:00",
                "label": "mid",
                "picture": str(pic),
                "sound": str(wav),
            }
            r = fire_window(
                w,
                cue_dir=cue_dir,
                hop=lambda win, page: ride_hop(
                    win,
                    page_path=page,
                    dry_run=False,
                    show_page=True,
                    spawn=lambda a: opened.append(list(a)),
                ),
                now=datetime(2026, 8, 16, 13, 0, 0),
            )
            body = Path(r["page"]).read_text(encoding="utf-8")
            self.assertIn("still.jpg", body)
            self.assertIn("<img", body)
            self.assertEqual(len(opened), 2)
            self.assertEqual(opened[0], build_open_argv(r["page"]))
            self.assertEqual(opened[1], build_open_argv(str(wav)))
            self.assertEqual(r["hop"]["opened"], ["page", "sound"])

    def test_default_fire_does_not_open_browser(self):
        with tempfile.TemporaryDirectory() as td:
            cue_dir = Path(td) / "cues"
            opened: list[list[str]] = []
            r = fire_window(
                {"id": "e", "label": "eve"},
                cue_dir=cue_dir,
                hop=lambda win, page: ride_hop(
                    win, page_path=page, dry_run=False, spawn=lambda a: opened.append(list(a))
                ),
                now=datetime(2026, 8, 16, 20, 30, 0),
            )
            self.assertTrue(Path(r["page"]).is_file())
            self.assertEqual(opened, [])
            self.assertEqual(r["hop"]["opened"], [])

    def test_dry_run_writes_does_not_open(self):
        with tempfile.TemporaryDirectory() as td:
            cue_dir = Path(td) / "cues"
            opened: list[list[str]] = []
            page = write_cue_page(
                cue_dir,
                {"id": "e", "label": "eve"},
                stem="x-e",
            )
            out = ride_hop(
                {"id": "e"},
                page_path=page,
                dry_run=True,
                spawn=lambda a: opened.append(list(a)),
            )
            self.assertTrue(out["dry_run"])
            self.assertEqual(opened, [])
            self.assertTrue(page.is_file())

    def test_open_argv_single_start_wrap(self):
        argv = build_open_argv(r"C:\tmp\cue.html")
        self.assertEqual(argv[:4], ["cmd", "/c", "start", ""])
        self.assertEqual(argv.count("start"), 1)


if __name__ == "__main__":
    unittest.main()
