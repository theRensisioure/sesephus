#!/usr/bin/env python3
"""Wav shred + dry entry through shipped ta_heavy.run."""
from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from ta_heavy import run, shred_temp  # noqa: E402
from test_analyze import PASTE, PRODUCT_PROMPT  # noqa: E402


def _tiny_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x10" * 160)


class TestHeavy(unittest.TestCase):
    def test_shred_temp_zeros_and_unlinks(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "gone.wav"
            p.write_bytes(b"SECRETWAV")
            shred_temp(p)
            self.assertFalse(p.is_file())

    def test_run_shreds_wav_after_transcribe_hook(self):
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td) / "prompt.wav"
            _tiny_wav(wav)
            self.assertTrue(wav.is_file())
            out = run(
                prompt="",
                paste=PASTE,
                wav=wav,
                transcribe=lambda _p: PRODUCT_PROMPT,
            )
            self.assertFalse(wav.is_file(), "wav must be shredded")
            self.assertTrue(out["ok"], out)
            self.assertTrue(out["wav_shredded"])
            self.assertEqual(out["prompt"], PRODUCT_PROMPT)
            self.assertTrue(out["clusters"])
            self.assertRegex(out["analysis"].lower(), r"vault|backup")

    def test_empty_inputs_fail_through_run(self):
        empty_paste = run(prompt=PRODUCT_PROMPT, paste="")
        self.assertFalse(empty_paste["ok"])
        self.assertEqual(empty_paste["error"], "empty paste")
        self.assertEqual(empty_paste["clusters"], [])
        empty_prompt = run(prompt="", paste=PASTE)
        self.assertFalse(empty_prompt["ok"])
        self.assertEqual(empty_prompt["error"], "empty prompt")


if __name__ == "__main__":
    unittest.main()
