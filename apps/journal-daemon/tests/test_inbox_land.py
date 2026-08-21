#!/usr/bin/env python3
"""Unit tests: inbox detect + land into journal path."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from inbox import (  # noqa: E402
    is_settled,
    land_file,
    land_new_from_designated,
    list_inbox_files,
    poll_inbox,
    seed_existing_inbox,
)


class TestInboxLand(unittest.TestCase):
    def test_land_file_copy_or_link(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "inbox"
            journal = td / "journal"
            inbox.mkdir()
            src = inbox / "take.m4a"
            src.write_bytes(b"fake-m4a-bytes-12345")
            r = land_file(src, journal_root=journal, prefer_link=True)
            self.assertTrue(r["ok"], r)
            self.assertGreater(r["size"], 0)
            dest = Path(r["file"])
            self.assertTrue(dest.exists() or dest.is_symlink())
            meta = Path(r["path"]) / "meta.json"
            self.assertTrue(meta.is_file())

    def test_land_new_from_designated(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "Sound Recordings"
            journal = td / "journal"
            inbox.mkdir()
            (inbox / "a.m4a").write_bytes(b"aaa")
            (inbox / "b.m4a").write_bytes(b"bbbb")
            cfg = {
                "capture": {
                    "designated_id": "ms-sound-recorder",
                    "command": "shell:AppsFolder\\x",
                    "inbox": str(inbox),
                    "glob": "*.m4a",
                    "label": "Sound Recorder",
                }
            }
            r = land_new_from_designated(cfg=cfg, journal_root=journal, seen=set())
            self.assertTrue(r["ok"])
            self.assertEqual(r["count"], 2)
            stamps = list(journal.iterdir())
            self.assertEqual(len(stamps), 2)
            for s in stamps:
                files = [p for p in s.iterdir() if p.suffix == ".m4a"]
                self.assertEqual(len(files), 1)
                self.assertGreater(files[0].stat().st_size, 0)

    def test_list_inbox_glob(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "x.m4a").write_bytes(b"1")
            (d / "y.txt").write_bytes(b"2")
            files = list_inbox_files(d, "*.m4a")
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "x.m4a")

    def test_second_land_skips_already_seen(self):
        """Persistent seen: second land_new call must not re-land same files."""
        from inbox import land_new_from_designated

        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "inbox"
            journal = td / "journal"
            seen_path = td / "seen.json"
            inbox.mkdir()
            (inbox / "a.m4a").write_bytes(b"aaa")
            cfg = {
                "capture": {
                    "designated_id": "ms-sound-recorder",
                    "command": "shell:AppsFolder\\x",
                    "inbox": str(inbox),
                    "glob": "*.m4a",
                    "label": "Sound Recorder",
                }
            }
            r1 = land_new_from_designated(
                cfg=cfg, journal_root=journal, seen_path=seen_path, persist_seen=True
            )
            self.assertEqual(r1["count"], 1)
            r2 = land_new_from_designated(
                cfg=cfg, journal_root=journal, seen_path=seen_path, persist_seen=True
            )
            self.assertEqual(r2["count"], 0)
            self.assertEqual(len(list(journal.iterdir())), 1)
            # new file still lands
            (inbox / "b.m4a").write_bytes(b"bbbb")
            r3 = land_new_from_designated(
                cfg=cfg, journal_root=journal, seen_path=seen_path, persist_seen=True
            )
            self.assertEqual(r3["count"], 1)
            self.assertEqual(len(list(journal.iterdir())), 2)

    def test_unsettled_file_not_landed(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "inbox"
            journal = td / "journal"
            inbox.mkdir()
            (inbox / "fresh.m4a").write_bytes(b"aaa")
            cfg = {
                "capture": {
                    "designated_id": "ms-sound-recorder",
                    "command": "x",
                    "inbox": str(inbox),
                    "glob": "*.m4a",
                    "label": "Sound Recorder",
                }
            }
            r = land_new_from_designated(
                cfg=cfg,
                journal_root=journal,
                seen=set(),
                persist_seen=False,
                min_age_sec=30.0,
            )
            self.assertEqual(r["count"], 0)
            self.assertEqual(r["skipped_unsettled"], ["fresh.m4a"])
            self.assertFalse(is_settled(inbox / "fresh.m4a", 30.0))

    def test_seed_does_not_land(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "inbox"
            seen_path = td / "seen.json"
            inbox.mkdir()
            (inbox / "old.m4a").write_bytes(b"aaa")
            (inbox / "Recording (20).m4a").write_bytes(b"bbb")
            cfg = {
                "capture": {
                    "designated_id": "ms-sound-recorder",
                    "command": "x",
                    "inbox": str(inbox),
                    "glob": "*.m4a",
                    "label": "Sound Recorder",
                }
            }
            r = seed_existing_inbox(
                cfg=cfg,
                seen_path=seen_path,
                skip_names={"Recording (20).m4a"},
            )
            self.assertEqual(r["count"], 1)
            self.assertEqual(r["added"], ["old.m4a"])
            self.assertFalse((td / "journal").exists())

    def test_poll_inbox_off_does_nothing(self):
        cooked = []
        out = poll_inbox(prefs={"auto_land": False, "auto_cook": True}, runner=cooked.append)
        self.assertEqual(out["count"], 0)
        self.assertEqual(out["skipped"], "auto_land off")
        self.assertEqual(cooked, [])

    def test_poll_inbox_cooks_every_landed_stamp(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            inbox = td / "inbox"
            journal = td / "journal"
            seen_path = td / "seen.json"
            inbox.mkdir()
            (inbox / "a.m4a").write_bytes(b"aaa")
            (inbox / "b.m4a").write_bytes(b"bbbb")
            cfg = {
                "capture": {
                    "designated_id": "ms-sound-recorder",
                    "command": "x",
                    "inbox": str(inbox),
                    "glob": "*.m4a",
                    "label": "Sound Recorder",
                }
            }
            cooked: list[list[str]] = []
            out = poll_inbox(
                cfg=cfg,
                prefs={"auto_land": True, "auto_cook": True},
                journal_root=journal,
                seen_path=seen_path,
                runner=lambda cmd: cooked.append(cmd),
                min_age_sec=0,
            )
            self.assertEqual(out["count"], 2)
            self.assertEqual(len(cooked), 2)
            self.assertTrue(all("--journal" in c for c in cooked))


if __name__ == "__main__":
    unittest.main()
