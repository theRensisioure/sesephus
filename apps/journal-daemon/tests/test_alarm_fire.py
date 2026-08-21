#!/usr/bin/env python3
"""Unit tests: alarm due/fire once-per-day + same launch path as Record."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from alarm_core import (  # noqa: E402
    day_key,
    due_windows,
    fire_window,
    mark_fired,
)
from capture_config import default_config, designate  # noqa: E402
from launcher import launch_designated  # noqa: E402


class TestAlarmFire(unittest.TestCase):
    def test_due_once_per_day(self):
        now = datetime(2026, 8, 12, 9, 30, 0)
        windows = [{"id": "morning", "time": "09:30", "label": "m"}]
        st = {"fired": {}}
        due = due_windows(windows, st, now=now)
        self.assertEqual(len(due), 1)
        st = mark_fired(st, due[0], now=now)
        due2 = due_windows(windows, st, now=now)
        self.assertEqual(len(due2), 0)
        # different day
        now2 = datetime(2026, 8, 13, 9, 30, 0)
        due3 = due_windows(windows, st, now=now2)
        self.assertEqual(len(due3), 1)

    def test_fire_writes_cue_and_calls_launch(self):
        with tempfile.TemporaryDirectory() as td:
            cue_dir = Path(td) / "cues"
            launches = []

            def launch(w):
                launches.append(w)
                return {"ok": True, "command": "shell:AppsFolder\\test", "label": "T"}

            w = {"id": "midday", "time": "13:00", "label": "mid"}
            r = fire_window(w, cue_dir=cue_dir, launch=launch, now=datetime(2026, 8, 12, 13, 0, 0))
            self.assertTrue(r["ok"])
            self.assertTrue(Path(r["cue"]).is_file())
            self.assertTrue(Path(r["page"]).is_file())
            cue = json.loads(Path(r["cue"]).read_text(encoding="utf-8"))
            self.assertEqual(cue["action"], "open_designated_recorder")
            self.assertTrue(cue["hop"]["page"].endswith(".html"))
            self.assertEqual(len(launches), 1)
            self.assertEqual(launches[0]["id"], "midday")

    def test_fire_handler_is_launch_designated(self):
        """Same function Record uses — launch_designated — is what fire should call."""
        cfg = designate(
            default_config(),
            candidate_id="ms-sound-recorder",
            command="shell:AppsFolder\\Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App",
            label="Sound Recorder",
        )
        # dry_run still returns non-empty command via real function
        out = launch_designated(cfg=cfg, dry_run=True)
        self.assertTrue(out["ok"])
        self.assertTrue(out["command"])
        self.assertEqual(out["label"], "Sound Recorder")
        self.assertTrue(out["dry_run"])

        with tempfile.TemporaryDirectory() as td:
            cue_dir = Path(td) / "cues"
            calls = []

            def launch(w):
                # call the real shipped launcher (dry)
                r = launch_designated(cfg=cfg, dry_run=True)
                calls.append(r)
                return r

            fire_window(
                {"id": "t", "time": "10:00"},
                cue_dir=cue_dir,
                launch=launch,
                now=datetime(2026, 8, 12, 10, 0, 0),
            )
            self.assertEqual(len(calls), 1)
            self.assertIn("SoundRecorder", calls[0]["command"])


if __name__ == "__main__":
    unittest.main()
