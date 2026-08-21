#!/usr/bin/env python3
"""Button-dock contract: hop take cell, legal inputs, meter, ingest pins.

Drives shipped journal-daemon helpers. Does not reimplement legal-host filters.
Scanner board.html must stay a finder (no ui_serve).
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

UI = HERE / "ui.html"
SERVE = HERE / "ui_serve.py"
HOP_TO_ARRAY = HERE / "hop_to_array.py"
HOME = Path(os.environ.get("USERPROFILE") or Path.home())
SCANNER_BOARDS = [
    HOME / "artifact-scanner" / "board.html",
    HOME
    / ".grok"
    / "worktrees"
    / "bardw-artifact-scanner"
    / "revert-to-zip-behavior"
    / "board.html",
]


def _board_texts() -> list[tuple[Path, str]]:
    out = []
    for p in SCANNER_BOARDS:
        if p.is_file():
            out.append((p, p.read_text(encoding="utf-8", errors="replace")))
    return out


def _inside_btn_record(html: str) -> str:
    m = re.search(
        r'<button[^>]*\bid=["\']btnRecord["\'][^>]*>(.*?)</button>',
        html,
        flags=re.S,
    )
    return m.group(1) if m else ""


class TestButtonDockMarkup(unittest.TestCase):
    def test_hop_is_named_button_dock(self):
        html = UI.read_text(encoding="utf-8")
        self.assertIn('data-dock="buttons"', html)
        self.assertIn('data-slot="record"', html)
        self.assertIn('id="micSelect"', html)
        inner = _inside_btn_record(html)
        self.assertIn("<canvas", inner)
        self.assertIn('id="recWave"', inner)
        self.assertIn("no widget", html.lower())

    def test_record_still_opens_designated_and_ingest_stays_truck(self):
        html = UI.read_text(encoding="utf-8")
        self.assertIn("/api/record/open", html)
        self.assertIn("/api/inbox/land", html)
        self.assertIn("/api/hop/cook", html)
        self.assertNotIn("MediaRecorder", html)
        self.assertNotIn("getUserMedia", html)
        hop = HOP_TO_ARRAY.read_text(encoding="utf-8")
        self.assertIn("food_truck_sink.py", hop)

    def test_scanner_board_does_not_load_ui_serve(self):
        boards = _board_texts()
        self.assertTrue(boards, "scanner board.html not found")
        for path, text in boards:
            self.assertNotIn(
                "ui_serve.py",
                text,
                f"journal UI-serve leaked into {path}",
            )
            self.assertNotIn("getUserMedia", text)
            self.assertNotIn("/api/record", text)
            self.assertNotIn("id=\"micSelect\"", text)
            self.assertNotIn("id='micSelect'", text)


class TestListInputsShipped(unittest.TestCase):
    """Drive the same list_inputs the :8777 inputs route calls."""

    DEVICES = [
        {
            "name": "CABLE Output (VB-Audio Virtual Cable)",
            "hostapi": 0,
            "max_input_channels": 2,
            "default_samplerate": 48000,
        },
        {
            "name": "Microphone (Maono PD200W Mic USB)",
            "hostapi": 1,
            "max_input_channels": 2,
            "default_samplerate": 48000,
        },
        {
            "name": "Primary Sound Capture Driver",
            "hostapi": 0,
            "max_input_channels": 2,
            "default_samplerate": 48000,
        },
        {
            "name": "Stereo Mix",
            "hostapi": 2,
            "max_input_channels": 2,
            "default_samplerate": 44100,
        },
    ]
    HOSTAPIS = [
        {"name": "Windows WASAPI"},
        {"name": "Windows WDM-KS"},
        {"name": "Windows DirectSound"},
    ]

    def test_list_inputs_filters_wdmks_and_matches_pick(self):
        from ui_serve import list_inputs  # shipped route helper

        got = list_inputs(devices=self.DEVICES, hostapis=self.HOSTAPIS, prefer="")
        self.assertTrue(got.get("ok"), got)
        rows = got.get("inputs") or []
        self.assertTrue(rows)
        keys = {"index", "name", "hostapi", "device_id", "channels", "samplerate"}
        for row in rows:
            self.assertTrue(keys <= set(row), row)
            self.assertNotIn("wdm-ks", str(row.get("hostapi") or "").lower())
        names = [r["name"] for r in rows]
        self.assertIn("CABLE Output (VB-Audio Virtual Cable)", names)
        self.assertIn("Stereo Mix", names)
        self.assertNotIn("Microphone (Maono PD200W Mic USB)", names)
        picked = got.get("picked") or {}
        self.assertIn("CABLE", picked.get("name") or "")
        self.assertFalse(got.get("keys_used"))
        self.assertFalse(got.get("network"))

    def test_list_inputs_prefer_switches_pick(self):
        from ui_serve import list_inputs

        a = list_inputs(devices=self.DEVICES, hostapis=self.HOSTAPIS, prefer="cable")
        b = list_inputs(devices=self.DEVICES, hostapis=self.HOSTAPIS, prefer="stereo")
        self.assertTrue(a.get("ok") and b.get("ok"), (a, b))
        self.assertIn("CABLE", (a.get("picked") or {}).get("name") or "")
        self.assertIn("Stereo", (b.get("picked") or {}).get("name") or "")
        self.assertNotEqual(
            (a.get("picked") or {}).get("device_id"),
            (b.get("picked") or {}).get("device_id"),
        )

    def test_list_inputs_missing_backend_is_honest(self):
        from ui_serve import list_inputs

        got = list_inputs(backend=False)
        self.assertFalse(got.get("ok"))
        self.assertEqual(got.get("inputs"), [])
        err = str(got.get("error") or "")
        self.assertTrue(err)
        self.assertNotIn("\n", err)
        self.assertLessEqual(len(err), 200)


class TestMeterSampleShipped(unittest.TestCase):
    """Drive the same sample_meter the hop polls."""

    DEVICES = TestListInputsShipped.DEVICES
    HOSTAPIS = TestListInputsShipped.HOSTAPIS

    def test_sample_meter_shape_and_no_file(self):
        from mic_meter import sample_meter

        with tempfile.TemporaryDirectory() as td:
            before = set(Path(td).rglob("*"))
            got = sample_meter(
                "cable",
                devices=self.DEVICES,
                hostapis=self.HOSTAPIS,
                scratch=Path(td),
            )
            after = set(Path(td).rglob("*"))
            self.assertIn("ok", got)
            self.assertIn("rms", got)
            self.assertIn("peak", got)
            self.assertIn("device_id", got)
            self.assertEqual(after, before, "meter must not write a file")
            self.assertIn("cable", str(got.get("device_id") or "").lower())
            if not got.get("ok"):
                # live stream may be unavailable; resolution still rebound
                self.assertEqual(float(got.get("rms") or 0), 0.0)

    def test_sample_meter_rebinds_on_prefer_change(self):
        from mic_meter import sample_meter

        a = sample_meter("cable", devices=self.DEVICES, hostapis=self.HOSTAPIS)
        b = sample_meter("stereo", devices=self.DEVICES, hostapis=self.HOSTAPIS)
        self.assertIn("cable", str(a.get("device_id") or "").lower())
        self.assertIn("stereo", str(b.get("device_id") or "").lower())
        self.assertNotEqual(a.get("device_id"), b.get("device_id"))


if __name__ == "__main__":
    unittest.main()
