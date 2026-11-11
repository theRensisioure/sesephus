"""Turn a clean nested journal-clip clone into a git worktree gitlink."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _make_writable(path: Path) -> None:
    os.chmod(path, stat.S_IWRITE)


def remove_tree(path: Path) -> None:
    def _onexc(func, failed, exc):  # noqa: ANN001
        _make_writable(Path(failed))
        func(failed)

    shutil.rmtree(path, onexc=_onexc)


def git_exe() -> str:
    import shutil as _shutil

    found = _shutil.which("git")
    if found:
        return found
    candidate = Path(r"C:\Program Files\Git\cmd\git.exe")
    if candidate.is_file():
        return str(candidate)
    raise FileNotFoundError("git")


def is_journal_clip(path: Path) -> bool:
    return any("journal-clip" in part.lower() for part in path.parts)


def nested_clones(root: Path) -> list[Path]:
    found: list[Path] = []
    root = root.resolve()
    for dirpath, dirnames, _names in __import__("os").walk(root):
        current = Path(dirpath)
        if ".git" in dirnames:
            git_path = current / ".git"
            if current != root and git_path.is_dir() and is_journal_clip(current):
                found.append(current)
            dirnames.remove(".git")
    return found


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def is_dirty(repo: Path) -> bool:
    result = _run([git_exe(), "-C", str(repo), "status", "--porcelain"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    return bool(result.stdout.strip())


def _enclosing_repo(clone: Path) -> Path:
    current = clone.parent.resolve()
    while True:
        if (current / ".git").exists():
            return current
        if current.parent == current:
            raise RuntimeError(f"no enclosing git repo for {clone}")
        current = current.parent


def _posix(path: Path) -> str:
    return path.resolve().as_posix()


def convert_clone(clone: Path) -> str:
    git_dir = clone / ".git"
    if not git_dir.is_dir():
        return f"skip {clone} (not a nested clone)"
    if is_dirty(clone):
        raise RuntimeError(f"refuse dirty nested clone: {clone}")
    head = _run([git_exe(), "-C", str(clone), "rev-parse", "HEAD"])
    if head.returncode != 0:
        raise RuntimeError(head.stderr.strip() or "rev-parse failed")
    sha = head.stdout.strip()
    index = git_dir / "index"
    if not index.is_file():
        raise RuntimeError(f"nested clone has no index: {clone}")
    main = _enclosing_repo(clone)
    slot = main / ".git" / "worktrees" / clone.name
    if slot.exists():
        raise RuntimeError(f"worktree slot already exists: {slot}")
    slot.mkdir(parents=True)
    shutil.copyfile(index, slot / "index")
    (slot / "HEAD").write_text(sha + "\n", encoding="utf-8")
    (slot / "commondir").write_text("../..\n", encoding="utf-8")
    gitlink = _posix(git_dir)
    (slot / "gitdir").write_text(gitlink + "\n", encoding="utf-8")
    remove_tree(git_dir)
    git_dir.write_text(f"gitdir: {_posix(slot)}\n", encoding="utf-8")
    _hide_from_parent(main, clone)
    return f"converted {clone} -> {slot}"


def _hide_from_parent(main: Path, clone: Path) -> None:
    """A linked worktree inside the parent tree is still untracked until excluded."""
    common = _run([git_exe(), "-C", str(main), "rev-parse", "--git-common-dir"])
    if common.returncode != 0:
        raise RuntimeError(common.stderr.strip() or "git-common-dir failed")
    git_common = Path(common.stdout.strip())
    if not git_common.is_absolute():
        git_common = (main / git_common).resolve()
    exclude = git_common / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    rel = clone.resolve().relative_to(main.resolve()).as_posix().rstrip("/") + "/"
    existing = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    if rel not in existing.splitlines():
        if existing and not existing.endswith("\n"):
            existing += "\n"
        exclude.write_text(existing + rel + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="ledger.clones")
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args(argv)
    code, text = convert_tree(args.root)
    stream = sys.stderr if code else sys.stdout
    stream.write(text)
    return code


def convert_tree(root: Path) -> tuple[int, str]:
    clones = nested_clones(root)
    if not clones:
        return 0, "no nested journal-clip clone\n"
    lines: list[str] = []
    for clone in clones:
        try:
            lines.append(convert_clone(clone))
        except RuntimeError as exc:
            lines.append(str(exc))
            return 1, "\n".join(lines) + "\n"
    return 0, "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
