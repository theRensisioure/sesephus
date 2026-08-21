#!/usr/bin/env python3
"""Unit tests: probe/filter/designate + config load/save (shipped capture_config)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from capture_config import (  # noqa: E402
    KNOWN_RECORDERS,
    default_config,
    designate,
    designated_fields,
    filter_candidates,
    load_config,
    save_config,
)


class TestCaptureConfig(unittest.TestCase):
    def test_defaults_ms_sound_recorder(self):
        cfg = default_config()
        d = designated_fields(cfg)
        self.assertEqual(d["designated_id"], "ms-sound-recorder")
        self.assertIn("SoundRecorder", d["command"])
        self.assertTrue(d["label"])
        self.assertIn("Sound Recordings", d["inbox"])
        self.assertEqual(d["glob"], "*.m4a")

    def test_filter_sound(self):
        hits = filter_candidates(KNOWN_RECORDERS, "sound")
        ids = {h["id"] for h in hits}
        self.assertIn("ms-sound-recorder", ids)
        self.assertNotIn("audacity", ids)

    def test_filter_audacity(self):
        hits = filter_candidates(KNOWN_RECORDERS, "audacity")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["id"], "audacity")

    def test_designate_updates_fields(self):
        cfg = default_config()
        custom = {
            "id": "custom",
            "label": "My Rec",
            "command": "C:\\Tools\\rec.exe",
            "inbox": "C:\\inbox",
            "glob": "*.wav",
            "match": ["custom"],
        }
        cfg2 = designate(cfg, candidate=custom)
        d = designated_fields(cfg2)
        self.assertEqual(d["designated_id"], "custom")
        self.assertEqual(d["command"], "C:\\Tools\\rec.exe")
        self.assertEqual(d["inbox"], "C:\\inbox")
        self.assertEqual(d["glob"], "*.wav")
        self.assertEqual(d["label"], "My Rec")

    def test_load_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "capture-config.json"
            cfg = default_config()
            cfg = designate(
                cfg,
                candidate_id="custom",
                command="echo-recorder",
                label="Echo",
                inbox="%USERPROFILE%\\tmp-inbox",
                glob="*.wav",
            )
            save_config(cfg, p)
            loaded = load_config(p)
            d = designated_fields(loaded)
            self.assertEqual(d["command"], "echo-recorder")
            self.assertEqual(d["label"], "Echo")
            self.assertEqual(d["glob"], "*.wav")
            raw = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(raw["product"], "sesefus-alarm-daemon")


if __name__ == "__main__":
    unittest.main()
