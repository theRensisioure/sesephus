#!/usr/bin/env bash
# guard_bigfiles.sh — block accidentally committing large files.
#
# Large binaries bloat git history permanently (you can't really delete them
# later). This catches the "quick context.7z" / WizTree-CSV class of mistake.
#
# Usage: tools/guard_bigfiles.sh --staged   (default; used by pre-commit)
# Exit: 0 = clean, 1 = an oversized file is staged.
set -uo pipefail

# Threshold: 1 MiB by default; override with BIGFILE_LIMIT_MB=5 (etc.).
LIMIT_BYTES=$(( ${BIGFILE_LIMIT_MB:-1} * 1024 * 1024 ))
fail=0

# Optional allow-list for known-large assets: one glob per line in a .bigfile-allow
# file at the repo root (blank lines and #comments ignored).
allowfile="$(git rev-parse --show-toplevel 2>/dev/null)/.bigfile-allow"
is_allowed() {
  [ -f "$allowfile" ] || return 1
  local pat
  while IFS= read -r pat; do
    [ -z "$pat" ] && continue
    case "$pat" in \#*) continue ;; esac
    case "$1" in $pat) return 0 ;; esac
  done < "$allowfile"
  return 1
}

while IFS= read -r -d '' f; do
  # Measure the STAGED blob (what will actually be committed), not the working-tree
  # copy — those can differ, causing false blocks/passes. --diff-filter=AM
  # guarantees the ":$f" index entry exists.
  is_allowed "$f" && continue
  size=$(git cat-file -s ":$f" 2>/dev/null) || continue
  if [ "$size" -gt "$LIMIT_BYTES" ]; then
    printf '  \342\234\226 large file staged: %s (%s bytes > %s limit)\n' "$f" "$size" "$LIMIT_BYTES" >&2
    fail=1
  fi
done < <(git diff --cached -z --name-only --diff-filter=AM)

if [ "$fail" -ne 0 ]; then
  cat >&2 <<'MSG'

BLOCKED: a file over 1 MiB is staged. Large blobs bloat history forever.
Keep it out of git (add to .gitignore) or store it externally.
Genuinely need it tracked? git commit --no-verify (once).
MSG
  exit 1
fi
exit 0
