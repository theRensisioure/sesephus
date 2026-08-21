#!/usr/bin/env bash
# guard_vaults.sh — keep Sesephus vault data out of git.
#
# Vaults are LOCAL-ONLY by design (documented throughout the project); a vault
# file must never be committed or live in history. This script detects vault
# data two ways so a rename can't sneak one past:
#   1. by name    — *.db / *.sqlite / *vault* / *sidevault* database files
#   2. by content — the first 8 bytes equal the vault magic "SESEPHUS"
#
# Usage:
#   tools/guard_vaults.sh --staged     check staged changes (used by pre-commit)
#   tools/guard_vaults.sh --tree       check working tree + untracked files
#   tools/guard_vaults.sh --history    scan every blob in every ref (full audit)
#   tools/guard_vaults.sh              default: --staged
#
# Exit: 0 = clean, 1 = vault data found, 2 = bad usage.
set -uo pipefail

VAULT_MAGIC="SESEPHUS"   # magic header at offset 0 of a Sesephus vault
fail=0
report() { printf '  \342\234\226 %s\n' "$1" >&2; fail=1; }

# name-based match: databases / vaults that must never be tracked
name_is_vault() {
  case "${1##*/}" in
    *.db|*.db-journal|*.sqlite|*.sqlite2|*.sqlite3) return 0 ;;
  esac
  case "$1" in
    *sidevault*|*sesephus_vault*|*[Vv]ault*.db) return 0 ;;
  esac
  return 1
}

# content-based match: first 8 bytes equal the vault magic (catches renames)
first8() { head -c 8 2>/dev/null; }

check_staged() {
  while IFS= read -r -d '' f; do
    if name_is_vault "$f"; then report "staged vault (name): $f"; continue; fi
    magic=$(git cat-file blob ":$f" 2>/dev/null | first8)
    [ "$magic" = "$VAULT_MAGIC" ] && report "staged vault (magic): $f"
  done < <(git diff --cached -z --name-only --diff-filter=AM)
}

scan_paths() {  # reads NUL-delimited paths from stdin, labels with $1
  local label="$1" f magic
  while IFS= read -r -d '' f; do
    [ -f "$f" ] || continue
    if name_is_vault "$f"; then report "$label vault (name): $f"; continue; fi
    magic=$(first8 <"$f")
    [ "$magic" = "$VAULT_MAGIC" ] && report "$label vault (magic): $f"
  done
}

check_tree() {
  # Feed scan_paths via process substitution (NOT a pipe): a piped final stage
  # runs in a subshell, so report()'s fail=1 would be lost and a found vault
  # would still exit 0. Matches the pattern used in check_staged.
  scan_paths "tracked"   < <(git ls-files -z)
  scan_paths "untracked" < <(git ls-files -z --others --exclude-standard)
}

check_history() {
  local sha path magic
  while read -r sha path; do
    [ -n "$sha" ] || continue
    [ "$(git cat-file -t "$sha" 2>/dev/null)" = blob ] || continue
    if name_is_vault "$path"; then report "history vault (name): $path @ $sha"; continue; fi
    magic=$(git cat-file -p "$sha" 2>/dev/null | first8)
    [ "$magic" = "$VAULT_MAGIC" ] && report "history vault (magic): $path @ $sha"
  done < <(git rev-list --objects --all)
}

case "${1:---staged}" in
  --staged)  check_staged ;;
  --tree)    check_tree ;;
  --history) check_history ;;
  -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
  *) echo "unknown option: ${1}" >&2; exit 2 ;;
esac

if [ "$fail" -ne 0 ]; then
  cat >&2 <<'MSG'

BLOCKED: vault data must not be committed — vaults are local-only.
If a match above is a genuine false positive, rename/remove it or inspect the
bytes. To bypass this once (NOT recommended): git commit --no-verify
MSG
  exit 1
fi
echo "vault guard: clean"
exit 0
