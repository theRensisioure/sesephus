"""Shared safety helpers for the Sesephus integration tests.

Historically these tests began by DELETING a vault file at a fixed path
(``V:\\sesephus_vault.db`` or ``./sesephus_vault.db``). Run on a machine with the
real vault mounted, that quietly destroyed live data.

These helpers make the reset refuse to touch a real vault unless the caller
explicitly opts in, and let a run be pointed at a throwaway sandbox instead.
"""
import os
import shutil
import sys
import tempfile

VAULT_MAGIC = b"SESEPHUS"          # first 8 bytes of a real Sesephus vault
_OVERRIDE = "SESEPHUS_ALLOW_VAULT_WIPE"   # set to "1" to force-allow a delete
_PATH_ENV = "SESEPHUS_TEST_VAULT"          # point a run at a sandbox vault path


def resolve_test_vault(default_path):
    """Return the vault path a test should use.

    Honors ``SESEPHUS_TEST_VAULT`` so a run can be sandboxed without editing code.
    """
    return os.environ.get(_PATH_ENV, default_path)


def _looks_like_real_vault(path):
    try:
        with open(path, "rb") as fh:
            if fh.read(8) != VAULT_MAGIC:
                return False
        return os.path.getsize(path) > 4096   # more than an empty header page
    except OSError:
        return False


def _within(path, base):
    """True if `path` is `base` or lives under it — with a separator boundary so a
    sibling sharing a name prefix (e.g. .../sesefus_evil vs .../sesefus) is NOT
    treated as inside."""
    real = os.path.realpath(path)
    base = os.path.realpath(base)
    return real == base or real.startswith(base + os.sep)


def _in_tempdir(path):
    return _within(path, tempfile.gettempdir())


def safe_reset_vault(path):
    """Delete a stale *test* vault, but REFUSE to nuke a real one.

    Aborts the test (``SystemExit``) if ``path`` is an existing, populated
    Sesephus vault outside the temp dir — unless ``SESEPHUS_ALLOW_VAULT_WIPE=1``.
    """
    if not os.path.exists(path):
        return
    if (_looks_like_real_vault(path)
            and not _in_tempdir(path)
            and os.environ.get(_OVERRIDE) != "1"):
        sys.exit(
            "[ABORT] Refusing to delete what looks like a REAL vault:\n"
            f"        {path}\n"
            "        (SESEPHUS magic + >4KB, outside the temp dir.)\n"
            "        These tests used to wipe live vaults; this guard stops that.\n"
            f"        Reset a genuine test vault here: set {_OVERRIDE}=1\n"
            f"        Better: point {_PATH_ENV} at a throwaway path."
        )
    os.remove(path)
    print(f"Cleaned up old vault: {path}")


def safe_reset_dir(path):
    """Remove a test output dir, but never something outside CWD or the temp dir."""
    if not os.path.isdir(path):
        return
    if not (_within(path, os.getcwd()) or _in_tempdir(path)):
        sys.exit(f"[ABORT] Refusing to rmtree outside CWD/temp: {path}")
    shutil.rmtree(path)
    print(f"Cleaned up local recordings folder: {path}")
