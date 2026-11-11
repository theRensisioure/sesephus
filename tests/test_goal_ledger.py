"""Goal checks for the event ledger, domains, and flat workspace."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPT = ROOT / "fixtures" / "representative.transcript"
MANIFEST = ROOT / "manifest.json"
CLIPPERS = Path(r"C:\dev\journal-clippers\audio-journal-system")


class LedgerTests(unittest.TestCase):
    def test_entry_point_is_stable_flat_and_acyclic(self) -> None:
        from ledger.parse import build_ledger

        first = subprocess.run(
            ["python", "-m", "ledger", str(TRANSCRIPT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        second = subprocess.run(
            ["python", "-m", "ledger", str(TRANSCRIPT)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        ledger = json.loads(first.stdout)
        text = TRANSCRIPT.read_text(encoding="utf-8")
        self.assertIsInstance(ledger["events"], list)
        self.assertGreaterEqual(len(ledger["events"]), 2)
        for event in ledger["events"]:
            span = event["span"]
            self.assertEqual(text[span["start"]:span["end"]], event["text"])
            self.assertNotIn("events", event)
        built = build_ledger(text)
        self.assertEqual(built["curve"]["edges"], [{"from": "e1", "to": "e2"}])
        self.assertEqual(len(ledger["decisions"]), 2)
        self.assertNotEqual(ledger["decisions"][0]["uid"], ledger["decisions"][1]["uid"])

    def test_version_resolver_folds_state(self) -> None:
        from ledger.parse import build_ledger
        from ledger.versions import resolve_state

        ledger = build_ledger(TRANSCRIPT.read_text(encoding="utf-8"))
        early = resolve_state(ledger, ledger["decisions"][0]["uid"])
        later = resolve_state(ledger, ledger["decisions"][1]["uid"])
        self.assertEqual(early, {"theme": "blue"})
        self.assertEqual(later, {"theme": "blue", "size": "large"})
        self.assertNotEqual(early, later)

    def test_domains_are_absolute_manifest_entries(self) -> None:
        from ledger.domains import load_domains, resolve_domain

        domains = load_domains(MANIFEST)
        resolved = {name: resolve_domain(name, domains) for name in domains}
        raw = json.loads(MANIFEST.read_text(encoding="utf-8"))["domains"]
        self.assertEqual(resolved, raw)
        for value in resolved.values():
            self.assertTrue(Path(value).is_absolute())
            self.assertNotIn("..", Path(value).parts)
        with self.assertRaises(ValueError):
            resolve_domain("aytree", {"aytree": "C:/dev/../AyTree"})

    def test_domain_scripts_do_not_walk_parents(self) -> None:
        for rel in ("tools/aytree_launch.py", "tools/sesefus_config.py", "ledger/domains.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("../", text, rel)

    def test_converter_and_hook_on_fixtures(self) -> None:
        from ledger.clones import convert_tree, git_exe, nested_clones
        from ledger.flat_workspace import check_flat

        from ledger.clones import remove_tree

        scratch = Path(os.environ.get("LEDGER_SCRATCH") or tempfile.mkdtemp(prefix="ledger-goal-"))
        scratch.mkdir(parents=True, exist_ok=True)
        for stale in ("parent-repo", "dirty-parent", "hook-nested", "hook-worktree"):
            target = scratch / stale
            if target.exists():
                remove_tree(target)
        before = CLIPPERS.stat().st_mtime if CLIPPERS.exists() else None
        scan = nested_clones(ROOT)
        (scratch / "clone-scan.txt").write_text(
            "\n".join(str(path) for path in scan) + ("\n" if scan else "none\n"),
            encoding="utf-8",
        )
        parent = scratch / "parent-repo"
        nested = parent / "journal-clip-nested"
        _git_repo(parent, git_exe())
        subprocess.run([git_exe(), "clone", str(parent), str(nested)], check=True, capture_output=True)
        self.assertTrue((nested / ".git").is_dir())
        kept = (nested / "README").read_text(encoding="utf-8")
        code, log = convert_tree(parent)
        (scratch / "convert.log").write_text(log, encoding="utf-8")
        self.assertEqual(code, 0, log)
        self.assertTrue((nested / ".git").is_file())
        link = (nested / ".git").read_text(encoding="utf-8")
        self.assertTrue(link.startswith("gitdir:"))
        self.assertNotIn("\\", link)
        self.assertEqual((nested / "README").read_text(encoding="utf-8"), kept)
        git = git_exe()
        listed = subprocess.run(
            [git, "-C", str(nested), "ls-files"],
            check=True, capture_output=True, text=True,
        )
        self.assertIn("README", listed.stdout.splitlines())
        status = subprocess.run(
            [git, "-C", str(nested), "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
        self.assertEqual(status.stdout.strip(), "")
        trees = subprocess.run(
            [git, "-C", str(parent), "worktree", "list", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
        self.assertIn(str(nested.resolve()).replace("\\", "/"), trees.stdout.replace("\\", "/"))
        self.assertNotIn(str((nested / ".git").resolve()).replace("\\", "/"), trees.stdout.replace("\\", "/"))
        parent_status = subprocess.run(
            [git, "-C", str(parent), "status", "--porcelain"],
            check=True, capture_output=True, text=True,
        )
        self.assertNotIn("journal-clip-nested", parent_status.stdout)

        dirty_parent = scratch / "dirty-parent"
        dirty = dirty_parent / "journal-clip-dirty"
        _git_repo(dirty_parent, git_exe())
        subprocess.run([git_exe(), "clone", str(dirty_parent), str(dirty)], check=True, capture_output=True)
        (dirty / "extra.txt").write_text("uncommitted\n", encoding="utf-8")
        code, log = convert_tree(dirty_parent)
        self.assertEqual(code, 1, log)
        self.assertIn("refuse dirty", log)
        self.assertTrue((dirty / ".git").is_dir())
        self.assertTrue((dirty / "extra.txt").is_file())

        nested_fix = scratch / "hook-nested"
        nested_fix.mkdir()
        (nested_fix / "journal-clip-bad").mkdir()
        (nested_fix / "journal-clip-bad" / ".git").mkdir()
        code, text = check_flat(nested_fix)
        (scratch / "hook-nested.txt").write_text(text, encoding="utf-8")
        self.assertEqual(code, 1)

        good = scratch / "hook-worktree"
        link = good / "journal-clip-ok"
        link.mkdir(parents=True)
        (link / ".git").write_text("gitdir: C:/elsewhere\n", encoding="utf-8")
        code, text = check_flat(good)
        (scratch / "hook-worktree.txt").write_text(text, encoding="utf-8")
        self.assertEqual(code, 0)
        if before is not None:
            self.assertEqual(CLIPPERS.stat().st_mtime, before)


def _git_repo(path: Path, git: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run([git, "-C", str(path), "init"], check=True, capture_output=True)
    subprocess.run([git, "-C", str(path), "config", "user.email", "ledger@example.com"], check=True)
    subprocess.run([git, "-C", str(path), "config", "user.name", "ledger"], check=True)
    (path / "README").write_text("keep\n", encoding="utf-8")
    subprocess.run([git, "-C", str(path), "add", "README"], check=True, capture_output=True)
    subprocess.run([git, "-C", str(path), "commit", "-m", "init"], check=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()
