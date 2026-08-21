#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from providers import enabled_providers, resolve_root  # noqa: E402
from scan import catalog, first_sentence, parse_frontmatter, scan_root  # noqa: E402


class TestScan(unittest.TestCase):
    def test_frontmatter_name_and_desc(self):
        text = "---\nname: compose\ndescription: >\n  One plan. Matrix widget.\n  Use when /compose.\n---\n\n# Body\n"
        meta = parse_frontmatter(text)
        self.assertEqual(meta.get("name"), "compose")
        self.assertIn("One plan", meta.get("description", ""))

    def test_first_sentence_cuts(self):
        s = first_sentence("See agent skills. Open their folders. One click.")
        self.assertEqual(s, "See agent skills.")

    def test_scan_skips_hidden_and_needs_skill_md(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            keep = root / "compose"
            keep.mkdir()
            (keep / "SKILL.md").write_text(
                "---\nname: compose\ndescription: One plan for the day.\n---\n\n# Compose\n",
                encoding="utf-8",
            )
            (root / "_parked").mkdir()
            (root / "_parked" / "SKILL.md").write_text("# no\n", encoding="utf-8")
            (root / "empty").mkdir()
            rows = scan_root(root)
            self.assertEqual([r["id"] for r in rows], ["compose"])
            self.assertEqual(rows[0]["name"], "compose")
            self.assertIn("One plan", rows[0]["description"])

    def test_catalog_missing_optional(self):
        reg = {
            "path": "x",
            "providers": [
                {
                    "id": "grok",
                    "label": "Grok",
                    "enabled": True,
                    "roots": [
                        {
                            "id": "ghost",
                            "label": "Ghost",
                            "path": str(Path(tempfile.gettempdir()) / "sesefus-no-such-skills-root"),
                            "optional": True,
                        }
                    ],
                }
            ],
        }
        data = catalog(reg, resolve_root, enabled_providers)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["missing_required"], 0)
        self.assertFalse(data["providers"][0]["roots"][0]["exists"])


if __name__ == "__main__":
    unittest.main()
