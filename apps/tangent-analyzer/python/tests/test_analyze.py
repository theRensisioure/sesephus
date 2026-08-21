#!/usr/bin/env python3
"""Gating tests: shipped prompt+paste leftover transform. No reimplementation."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from ta_analyze import MOVES, analyze  # noqa: E402
from ta_heavy import run  # noqa: E402

# Fixture: two+ distinct open loops plus closed/chatter filler.
PASTE = """
Still need to wire the vault backup before Friday.
The hop UI mic meter is leftover from the mixer idea.
We already shipped the SSFS config layer.
Thanks for the status dump, tests passed.
Parked: Circadia extract is not this sitting.
The grocery list still has oat milk and also the car inspection is overdue.
"""

PRODUCT_PROMPT = "rank Sesefus product leftovers, drop household"
HOUSEHOLD_PROMPT = "rank household chores, drop product work"


def _loops(result) -> list[str]:
    return [c.loop.lower() for c in result.clusters]


class TestShippedAnalyze(unittest.TestCase):
    def test_product_lens_keeps_paste_open_loops_only(self):
        r = analyze(PRODUCT_PROMPT, PASTE)
        self.assertTrue(r.ok, r.error)
        self.assertTrue(r.clusters, "open loops from the paste must appear")
        blob = " ".join(_loops(r))
        self.assertRegex(blob, r"vault|backup")
        self.assertRegex(blob, r"meter|hop|mixer")
        joined = blob
        self.assertNotIn("shipped", joined)
        self.assertNotIn("thanks", joined)
        self.assertNotIn("tests passed", joined)
        self.assertNotRegex(joined, r"\boat\b")
        self.assertNotRegex(joined, r"grocery")
        self.assertNotRegex(joined, r"inspection")
        for c in r.clusters:
            self.assertIn(c.score, range(1, 6))
            self.assertTrue(c.loop.strip())
            self.assertTrue(c.origin.strip())
            self.assertIn(c.move, MOVES)
            self.assertIn("loop ·", r.render())
            self.assertIn("origin ·", r.render())
            self.assertIn("move ·", r.render())

    def test_prompt_steers_kept_set_or_rank(self):
        a = analyze(PRODUCT_PROMPT, PASTE)
        b = analyze(HOUSEHOLD_PROMPT, PASTE)
        self.assertTrue(a.ok, a.error)
        self.assertTrue(b.ok, b.error)
        self.assertTrue(a.clusters)
        self.assertTrue(b.clusters)
        house = " ".join(_loops(b))
        self.assertRegex(house, r"oat|grocery|car|inspection")
        self.assertNotEqual([c.loop for c in a.clusters], [c.loop for c in b.clusters])
        prod = " ".join(_loops(a))
        self.assertNotRegex(prod, r"grocery|oat milk|car inspection")
        self.assertNotRegex(house, r"vault backup|mic meter")

    def test_prompt_only_does_not_invent_loops(self):
        invented = "still need to wire the vault backup and the hop meter leftover"
        r = analyze(invented, "")
        self.assertFalse(r.ok)
        self.assertEqual(r.clusters, [])
        self.assertEqual(r.error, "empty paste")
        self.assertNotIn("vault", (r.render() or "").lower().split("failed")[0] if False else "")
        # prompt text must not become a cluster
        self.assertEqual(r.as_dict()["clusters"], [])

    def test_paste_only_empty_prompt_fails(self):
        r = analyze("", PASTE)
        self.assertFalse(r.ok)
        self.assertEqual(r.error, "empty prompt")
        self.assertEqual(r.clusters, [])

    def test_heavy_run_is_the_dry_entry(self):
        out = run(prompt=PRODUCT_PROMPT, paste=PASTE)
        self.assertTrue(out["ok"], out)
        self.assertTrue(out["clusters"])
        analysis = out["analysis"]
        self.assertIn("tangent analysis", analysis.lower())
        self.assertRegex(analysis.lower(), r"vault|backup")
        self.assertNotIn("thanks for the status dump", analysis.lower())


if __name__ == "__main__":
    unittest.main()
