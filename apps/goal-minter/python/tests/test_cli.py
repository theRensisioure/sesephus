#!/usr/bin/env python3
"""Drive the shipped dry entry. Empty input must not write a packet file."""
from __future__ import annotations

import io
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
APP = HERE.parent
CLI = HERE / "cli.py"
MINT_BAT = APP / "Mint.bat"
UI = HERE / "ui.py"
sys.path.insert(0, str(HERE))

from cli import main  # noqa: E402
from mint import PACKET_REL  # noqa: E402
from ui import MAST, WINDOW_TITLE  # noqa: E402

MESSY = (
    "I want a launchable Sesefus app that mints a house goal packet "
    "from messy objective text. It should live at apps/goal-minter. "
    "Don't grow journal-clip or add an extra HTTP listen port."
)


class TestCli(unittest.TestCase):
    def test_launch_entry_exists(self):
        self.assertTrue(CLI.is_file(), CLI)
        self.assertTrue(MINT_BAT.is_file(), MINT_BAT)
        bat = MINT_BAT.read_text(encoding="utf-8")
        self.assertIn("python\\cli.py", bat)

    def test_ui_labels_goal_minting(self):
        src = UI.read_text(encoding="utf-8")
        self.assertIn("goal minting", src.lower())
        self.assertIn("goal minting", WINDOW_TITLE.lower())
        self.assertIn("goal minting", MAST.lower())
        self.assertNotIn("journal transcription", WINDOW_TITLE.lower())
        self.assertNotIn("transcription", MAST.lower())

    def test_mint_button_centered_on_goal_divider(self):
        try:
            import tkinter as tk
        except Exception:
            self.skipTest("tkinter missing")
        from ui import attach_goal_divider

        root = tk.Tk()
        root.withdraw()
        try:
            mid = attach_goal_divider(root, tk, command=lambda: None)
            root.update_idletasks()
            self.assertEqual(int(mid.grid_columnconfigure(0)["weight"]), 1)
            self.assertEqual(int(mid.grid_columnconfigure(1)["weight"]), 0)
            self.assertEqual(int(mid.grid_columnconfigure(2)["weight"]), 1)
            buttons = [
                w for w in mid.winfo_children() if w.winfo_class() == "Button"
            ]
            self.assertEqual(len(buttons), 1)
            self.assertEqual(str(buttons[0].cget("text")), "mint packet")
            info = buttons[0].grid_info()
            self.assertEqual(int(info["column"]), 1)
            self.assertEqual(int(info["row"]), 0)
        finally:
            root.destroy()

    def test_say_writes_packet_and_prints_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["--say", MESSY, "--out", str(root)])
            self.assertEqual(code, 0, err.getvalue())
            dest = root / PACKET_REL
            self.assertTrue(dest.is_file(), dest)
            printed = buf.getvalue()
            on_disk = dest.read_text(encoding="utf-8")
            for needle in ("## Spine", "## Done when", "## Fence", "### Q1", "### Q2", "### Q3"):
                self.assertIn(needle, printed)
                self.assertIn(needle, on_disk)
            self.assertIn("apps/goal-minter", printed)
            self.assertIn("apps/goal-minter", on_disk)
            self.assertRegex(on_disk, r"(?m)^\*\*A:\*\* apps/goal-minter\s*$")
            q2 = on_disk.split("### Q2", 1)[1].split("### Q3", 1)[0]
            self.assertNotIn("journal-clip", q2)
            self.assertRegex(printed, r"journal-clip|HTTP", re.I)
            self.assertIn("wrote ", err.getvalue())

    def test_empty_say_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            buf = io.StringIO()
            err = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["--say", "  \n  ", "--out", str(root)])
            self.assertNotEqual(code, 0)
            self.assertFalse((root / PACKET_REL).exists())
            self.assertEqual(list(root.iterdir()), [])
            self.assertIn("empty objective", err.getvalue().lower())

    def test_whitespace_text_file_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "blank.txt"
            src.write_text("\n\t  \n", encoding="utf-8")
            err = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = main(["--text-file", str(src), "--out", str(root)])
            self.assertNotEqual(code, 0)
            self.assertFalse((root / PACKET_REL).exists())

    def test_subprocess_dry_entry_twice(self):
        py = sys.executable
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            d1 = root / "run1"
            d2 = root / "run2"
            runs = []
            for dest in (d1, d2):
                proc = subprocess.run(
                    [py, str(CLI), "--say", MESSY, "--out", str(dest)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr)
                packet_path = dest / PACKET_REL
                self.assertTrue(packet_path.is_file(), packet_path)
                body = packet_path.read_text(encoding="utf-8")
                self.assertTrue(proc.stdout.strip(), "stdout empty — packet content required")
                self.assertIn("## Spine", proc.stdout)
                self.assertIn("## Spine", body)
                self.assertIn("apps/goal-minter", body)
                self.assertIn("apps/goal-minter", proc.stdout)
                runs.append(body)
            def substance(md: str) -> str:
                lines = [
                    ln
                    for ln in md.splitlines()
                    if not ln.startswith("time_started:")
                ]
                return "\n".join(lines)
            self.assertEqual(substance(runs[0]), substance(runs[1]))


if __name__ == "__main__":
    unittest.main()
