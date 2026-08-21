#!/usr/bin/env python3
"""Stamp hop.audio_text onto a plated ARRAY pair. No whisper."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import hop_to_array as h  # noqa: E402


class TestHopToArray(unittest.TestCase):
    def test_stamp_pair_marks_both_sides(self):
        with tempfile.TemporaryDirectory() as td:
            vault = Path(td) / "vault"
            cut = "20260816T053833Z"
            dest = vault / cut
            dest.mkdir(parents=True)
            (dest / "meta.json").write_text(
                json.dumps({"id": cut, "kind": "raw-transcription"}) + "\n",
                encoding="utf-8",
            )
            array = {
                "contract": "raw-transcription-dual-array-v0",
                "count": 1,
                "audio": [{"id": cut, "path": str(dest / "audio.m4a")}],
                "text": [{"id": cut, "path": str(dest / "raw.txt")}],
            }
            ap = vault / "ARRAY.json"
            ap.write_text(json.dumps(array) + "\n", encoding="utf-8")
            hop = {"via": "alarm", "alarm_id": "evening", "journal": "20260816-003833"}
            with mock.patch.object(h, "VAULT", vault), mock.patch.object(h, "ARRAY_PATH", ap):
                out = h.stamp_pair(cut, hop)
            self.assertTrue(out["ok"])
            self.assertEqual(out["dtype"], "hop.audio_text")
            meta = json.loads((dest / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["dtype"], "hop.audio_text")
            self.assertEqual(meta["hop"]["alarm_id"], "evening")
            got = json.loads(ap.read_text(encoding="utf-8"))
            self.assertEqual(got["audio"][0]["dtype"], "hop.audio_text")
            self.assertEqual(got["text"][0]["dtype"], "hop.audio_text")
            self.assertIn("hop.audio_text", got["dtypes"])

    def test_cook_already_plated_returns_existing_cut(self):
        src = Path(tempfile.gettempdir()) / "sesefus-already.m4a"
        src.write_bytes(b"x")
        fake = mock.MagicMock()
        fake.plan_for.return_value = {"already": "20260817T135055Z"}
        fake.land.side_effect = AssertionError("must not cook twice")
        with mock.patch.object(h, "SINK", Path(__file__)):
            with mock.patch.dict(sys.modules, {"food_truck_sink": fake}):
                cut = h.cook(src)
        self.assertEqual(cut, "20260817T135055Z")
        fake.land.assert_not_called()

    def test_rename_generic_recorder_to_cut(self):
        with tempfile.TemporaryDirectory() as td:
            inbox = Path(td) / "Sound Recordings"
            inbox.mkdir()
            src = inbox / "Recording (21).m4a"
            src.write_bytes(b"audio")
            vault = Path(td) / "vault"
            cut = "20260817T135055Z"
            dest = vault / cut
            dest.mkdir(parents=True)
            (dest / "meta.json").write_text(
                json.dumps(
                    {
                        "id": cut,
                        "source": {
                            "path": str(src),
                            "os_name": src.name,
                            "os_name_untouched": True,
                        },
                    }
                ),
                encoding="utf-8",
            )
            ap = vault / "ARRAY.json"
            ap.write_text(
                json.dumps(
                    {
                        "count": 1,
                        "audio": [{"id": cut, "src": str(src), "os_name": src.name}],
                        "text": [{"id": cut}],
                    }
                ),
                encoding="utf-8",
            )
            journal_root = Path(td) / "journal"
            jdir = journal_root / "20260817-090038-1"
            jdir.mkdir(parents=True)
            (jdir / "meta.json").write_text(
                json.dumps({"stamp": jdir.name, "audio": src.name, "source_path": str(src)}),
                encoding="utf-8",
            )
            seen_path = Path(td) / "seen.json"
            seen_path.write_text(json.dumps({"seen": [str(src)]}), encoding="utf-8")
            hop = {"journal": jdir.name}
            spoken = "I need to remember to keep my mic close to the speaker."
            house = "sesefus · hop · mic-close-speaker.m4a"
            with (
                mock.patch.object(h, "VAULT", vault),
                mock.patch.object(h, "ARRAY_PATH", ap),
                mock.patch.object(h, "JOURNAL", journal_root),
                mock.patch("inbox.DEFAULT_SEEN_PATH", seen_path),
            ):
                out = h.rename_inbox_recording(src, cut, hop=hop, text=spoken)
            self.assertTrue(out["ok"], out)
            self.assertEqual(out["from"], "Recording (21).m4a")
            self.assertEqual(out["to"], house)
            self.assertFalse(src.exists())
            renamed = inbox / house
            self.assertTrue(renamed.is_file())
            jm = json.loads((jdir / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(jm["source_path"], str(renamed))
            self.assertEqual(jm["source_renamed_from"], "Recording (21).m4a")
            meta = json.loads((dest / "meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["source"]["os_name"], house)
            self.assertEqual(meta["title"], Path(house).stem)
            self.assertFalse(meta["source"]["os_name_untouched"])
            array = json.loads(ap.read_text(encoding="utf-8"))
            self.assertEqual(array["audio"][0]["os_name"], house)
            seen = json.loads(seen_path.read_text(encoding="utf-8"))["seen"]
            self.assertIn(str(renamed.resolve()), seen)
            self.assertNotIn(str(src.resolve()), seen)

    def test_house_stem_is_title_scheme_not_cut(self):
        stem = h.house_recording_stem(
            "no-live-cut",
            hop={"via": "inbox"},
            text="I need to remember to keep my mic close to the speaker.",
            segments=[],
        )
        self.assertTrue(stem.startswith("sesefus · hop · "))
        self.assertIn("mic", stem)
        divider = h.house_recording_stem(
            "no-live-cut",
            text="So inside of the planet less nanometer, I need to be able to resize the little divider between briefs and meaning.",
            segments=[],
        )
        self.assertTrue(divider.startswith("sesefus · hop · "))
        self.assertIn("divider", divider)
        self.assertNotEqual(divider, "20260817T141217Z")
        self.assertFalse(h.needs_house_rename(stem + ".m4a"))
        self.assertTrue(h.needs_house_rename("20260817T135055Z.m4a"))
        self.assertTrue(h.needs_house_rename("Recording (21).m4a"))

    def test_centroid_picks_spine_clause_not_first(self):
        text = (
            "So inside of the planet less nanometer. "
            "I need to be able to resize the little divider between briefs and meaning. "
            "There also needs to be no scroll."
        )
        probe = h.centroid_probe(text)
        self.assertGreaterEqual(probe["n"], 2)
        self.assertIn("divider", (probe.get("chunk") or "").lower())
        slug = h.artifact_slug(text)
        self.assertIn("divider", slug)
        self.assertNotEqual(slug.split("-")[:3], ["planet", "nanometer", "resize"])

    def test_rename_skips_already_named(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "sesefus · hop · mic-close-speaker.m4a"
            src.write_bytes(b"x")
            out = h.rename_inbox_recording(src, "20260817T135055Z")
            self.assertTrue(out["ok"])
            self.assertEqual(out["skipped"], "already named")
            self.assertTrue(src.is_file())

    def test_rename_promotes_bare_cut_to_house(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "20260817T135055Z.m4a"
            src.write_bytes(b"x")
            vault = td / "vault"
            cut = "20260817T135055Z"
            (vault / cut).mkdir(parents=True)
            (vault / cut / "meta.json").write_text("{}", encoding="utf-8")
            ap = vault / "ARRAY.json"
            ap.write_text(json.dumps({"audio": [{"id": cut, "os_name": src.name}]}), encoding="utf-8")
            seen_path = td / "seen.json"
            seen_path.write_text(json.dumps({"seen": [str(src)]}), encoding="utf-8")
            with (
                mock.patch.object(h, "VAULT", vault),
                mock.patch.object(h, "ARRAY_PATH", ap),
                mock.patch("inbox.DEFAULT_SEEN_PATH", seen_path),
            ):
                out = h.rename_inbox_recording(
                    src,
                    cut,
                    text="I need to remember to keep my mic close to the speaker.",
                )
            self.assertTrue(out["ok"], out)
            self.assertEqual(out["to"], "sesefus · hop · mic-close-speaker.m4a")
            self.assertTrue((td / out["to"]).is_file())


if __name__ == "__main__":
    unittest.main()
