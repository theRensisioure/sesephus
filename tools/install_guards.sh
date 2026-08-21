#!/usr/bin/env bash
# install_guards.sh — enable the vault pre-commit guard in this clone.
# Run once after cloning:  bash tools/install_guards.sh
set -uo pipefail
root="$(git rev-parse --show-toplevel)"
# Every hook and guard, not just pre-commit: a clone made on a filemode-blind
# filesystem (Windows) arrives with the exec bits stripped, and a non-executable
# hook is skipped by git *silently* — the guard reads as installed but is off.
chmod +x "$root/.githooks/pre-commit" "$root/.githooks/pre-push" "$root"/tools/*.sh 2>/dev/null || true
git -C "$root" config core.hooksPath .githooks

status=0
for h in pre-commit pre-push; do
  if [ ! -x "$root/.githooks/$h" ]; then
    echo "WARNING: .githooks/$h is not executable — that guard is OFF" >&2
    status=1
  fi
done

echo "vault guard enabled: core.hooksPath -> .githooks"
echo "audit full history any time with:  tools/guard_vaults.sh --history"
exit $status
