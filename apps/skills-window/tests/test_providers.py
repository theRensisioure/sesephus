#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from providers import add_provider, expand_path, load_registry, path_allowed  # noqa: E402


class TestProviders(unittest.TestCase):
    def test_expand_home(self):
        p = expand_path("~/.grok/skills")
        self.assertTrue(str(p).replace("\\", "/").endswith("/.grok/skills") or str(p).endswith(".grok\\skills"))
        self.assertFalse(str(p).startswith("~"))

    def test_load_shipped_grok(self):
        reg = load_registry(HERE / "providers.json")
        self.assertNotIn("error", reg)
        ids = [p["id"] for p in reg["providers"]]
        self.assertEqual(ids, ["grok"])
        self.assertTrue(reg["providers"][0]["enabled"])
        roots = {r["id"] for r in reg["providers"][0]["roots"]}
        self.assertIn("user", roots)

    def test_add_provider_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "providers.json"
            src.write_text('{"version":1,"providers":[]}\n', encoding="utf-8")
            add_provider(
                {
                    "id": "claude",
                    "label": "Claude",
                    "enabled": True,
                    "roots": [{"id": "user", "label": "Claude skills", "path": "~/.claude/skills", "optional": True}],
                },
                src,
            )
            reg = load_registry(src)
            self.assertEqual(reg["providers"][0]["id"], "claude")
            data = json.loads(src.read_text(encoding="utf-8"))
            self.assertEqual(data["providers"][0]["id"], "claude")

    def test_path_allowed_under_base(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            child = base / "compose"
            child.mkdir()
            (child / "SKILL.md").write_text("# x\n", encoding="utf-8")
            self.assertTrue(path_allowed(child, [base]))
            self.assertFalse(path_allowed(base.parent, [base]))


if __name__ == "__main__":
    unittest.main()
