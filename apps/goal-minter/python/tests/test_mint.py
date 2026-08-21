#!/usr/bin/env python3
"""Drive the shipped text→packet mint. No reimplementation. No golden essay."""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from mint import (  # noqa: E402
    PACKET_REL,
    EmptyInputError,
    mint,
    render_packet,
    write_packet,
)

# Representative messy prose: wanted result, a place, something out of scope.
MESSY = (
    "I want a launchable Sesefus app that mints a house goal packet "
    "from messy objective text. It should live at apps/goal-minter. "
    "Don't grow journal-clip or add an extra HTTP listen port."
)


class TestMint(unittest.TestCase):
    def test_messy_prose_fills_packet_fields(self):
        packet = mint(MESSY)
        self.assertTrue(packet.spine.strip(), "spine empty")
        self.assertTrue(packet.outcome.strip(), "outcome empty")
        self.assertTrue(packet.surface.strip(), "surface empty")
        self.assertTrue(packet.fence.strip(), "fence empty")
        self.assertGreaterEqual(len(packet.done_when), 1)
        self.assertTrue(all(str(c).strip() for c in packet.done_when))
        self.assertEqual(packet.surface, "apps/goal-minter")
        self.assertNotIn("journal-clip", packet.surface)
        self.assertNotIn("HTTP", packet.surface)
        self.assertRegex(packet.fence, r"journal-clip|HTTP", re.I)
        self.assertNotIn("apps/goal-minter", packet.fence)
        self.assertNotEqual(packet.surface, packet.fence)

    def test_empty_string_fails(self):
        with self.assertRaises(EmptyInputError):
            mint("")

    def test_whitespace_only_fails(self):
        with self.assertRaises(EmptyInputError):
            mint("  \n\t  ")

    def test_labeled_answers_round_trip(self):
        text = (
            "spine: Ship the goal-minter dry entry.\n"
            "outcome: A packet file with 3-Q answers on disk.\n"
            "surface: apps/goal-minter\n"
            "fence: journal-clip, extra HTTP ports\n"
            "done when:\n"
            "- [ ] dry mint writes interview.md\n"
            "- [ ] empty input fails closed\n"
        )
        packet = mint(text)
        self.assertEqual(packet.spine, "Ship the goal-minter dry entry.")
        self.assertEqual(packet.outcome, "A packet file with 3-Q answers on disk.")
        self.assertEqual(packet.surface, "apps/goal-minter")
        self.assertEqual(packet.fence, "journal-clip, extra HTTP ports")
        self.assertEqual(
            list(packet.done_when),
            ["dry mint writes interview.md", "empty input fails closed"],
        )

    def test_windows_surface_not_substituted(self):
        path = r"C:\Users\bardw\dev\sesefus\apps\goal-minter"
        text = (
            "outcome: Packet lands on disk.\n"
            f"surface: {path}\n"
            "fence: leave apps/journal-clip untouched\n"
        )
        packet = mint(text)
        self.assertEqual(packet.surface, path)
        self.assertIn("apps/journal-clip", packet.fence)

    def test_interview_markdown_round_trip(self):
        text = (
            "# Goal packet\n"
            "status: open\n"
            "\n"
            "## Spine\n"
            "Mint a packet from messy text.\n"
            "\n"
            "## Done when\n"
            "- [ ] dry entry writes interview.md\n"
            "\n"
            "## Fence\n"
            "journal-clip and extra HTTP ports\n"
            "\n"
            "## Interview (max 3)\n"
            "### Q1\n"
            "What exists when this is done?\n"
            "**A:** A launchable mint that writes a 3-Q packet.\n"
            "\n"
            "### Q2\n"
            "Where does it live (repo, skill, doc, path)?\n"
            "**A:** apps/goal-minter\n"
            "\n"
            "### Q3\n"
            "What is explicitly out of scope?\n"
            "**A:** journal-clip and extra HTTP ports\n"
        )
        packet = mint(text)
        self.assertEqual(packet.spine, "Mint a packet from messy text.")
        self.assertEqual(packet.outcome, "A launchable mint that writes a 3-Q packet.")
        self.assertEqual(packet.surface, "apps/goal-minter")
        self.assertEqual(packet.fence, "journal-clip and extra HTTP ports")
        self.assertIn("dry entry writes interview.md", packet.done_when)

    def test_write_packet_shape_and_empty_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            packet = mint(MESSY)
            dest = write_packet(packet, root, time_started="2026-08-21T12:00:00")
            self.assertEqual(dest, root / PACKET_REL)
            self.assertTrue(dest.is_file())
            body = dest.read_text(encoding="utf-8")
            self.assertTrue(body.startswith("# Goal packet\n"))
            self.assertIn("## Spine\n" + packet.spine, body)
            self.assertIn("## Done when\n", body)
            self.assertIn("- [ ] ", body)
            self.assertIn("## Fence\n" + packet.fence, body)
            self.assertIn("### Q1\n", body)
            self.assertIn("**A:** " + packet.outcome, body)
            self.assertIn("### Q2\n", body)
            self.assertIn("**A:** " + packet.surface, body)
            self.assertIn("### Q3\n", body)
            self.assertIn("**A:** " + packet.fence, body)
            rendered = render_packet(packet, time_started="2026-08-21T12:00:00")
            self.assertEqual(body, rendered)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with self.assertRaises(EmptyInputError):
                mint("   ")
            self.assertFalse((root / PACKET_REL).exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_same_input_twice_same_substance(self):
        a = mint(MESSY)
        b = mint(MESSY)
        self.assertEqual(a.spine, b.spine)
        self.assertEqual(a.outcome, b.outcome)
        self.assertEqual(a.surface, b.surface)
        self.assertEqual(a.fence, b.fence)
        self.assertEqual(a.done_when, b.done_when)


if __name__ == "__main__":
    unittest.main()
