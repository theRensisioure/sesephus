#!/usr/bin/env python3
"""Non-dry-run launch: inject spawn, assert single cmd/start wrap."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from capture_config import default_config, designate  # noqa: E402
from launcher import build_launch_argv, launch_designated  # noqa: E402


class TestLauncherSpawn(unittest.TestCase):
    def test_build_argv_shell_single_wrap(self):
        cmd = "shell:AppsFolder\\Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App"
        argv = build_launch_argv(cmd)
        self.assertEqual(argv[:4], ["cmd", "/c", "start", ""])
        self.assertEqual(argv[4], cmd)
        # must not nest cmd/start twice
        self.assertEqual(argv.count("cmd"), 1)
        self.assertEqual(argv.count("start"), 1)

    def test_launch_injects_single_wrap_argv(self):
        cfg = designate(
            default_config(),
            candidate_id="ms-sound-recorder",
            command="shell:AppsFolder\\Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App",
            label="Sound Recorder",
        )
        seen: list[list[str]] = []

        def fake_spawn(argv: list[str]) -> None:
            seen.append(list(argv))

        out = launch_designated(cfg=cfg, dry_run=False, spawn=fake_spawn)
        self.assertTrue(out["ok"])
        self.assertTrue(out["spawned"])
        self.assertEqual(len(seen), 1)
        argv = seen[0]
        self.assertEqual(argv[:4], ["cmd", "/c", "start", ""])
        self.assertTrue(argv[4].startswith("shell:"))
        self.assertEqual(argv.count("cmd"), 1)
        self.assertEqual(argv.count("/c"), 1)
        self.assertEqual(argv.count("start"), 1)
        # result.argv matches what was spawned
        self.assertEqual(out["argv"], argv)

    def test_exe_no_start_wrap(self):
        cfg = designate(
            default_config(),
            command=r"C:\Tools\rec.exe",
            label="Rec",
            candidate_id="custom",
        )
        seen: list[list[str]] = []
        launch_designated(cfg=cfg, dry_run=False, spawn=lambda a: seen.append(list(a)))
        self.assertEqual(seen[0], [r"C:\Tools\rec.exe"])


if __name__ == "__main__":
    unittest.main()
