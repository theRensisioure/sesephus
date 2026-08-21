#!/usr/bin/env bash
# scan_secrets.sh — keep API keys / credentials out of git.
#
# Prefers gitleaks if installed; otherwise falls back to a built-in regex sweep so
# it still works on a machine without gitleaks (the common case here).
#
# Usage:
#   tools/scan_secrets.sh --staged   scan staged additions (used by pre-commit)
#   tools/scan_secrets.sh --tree     scan all tracked files (pre-push / CI)
#   tools/scan_secrets.sh            default: --staged
#
# Exit: 0 = clean, 1 = possible secret found.
set -uo pipefail

mode="${1:---staged}"
fail=0

# Files that legitimately contain secret *patterns* (not secrets) — never flag them.
EXCLUDES=( ':(exclude)tools/scan_secrets.sh' ':(exclude).gitleaks.toml' ':(exclude).secretsallow' )

# --- gitleaks path (preferred) --------------------------------------------
if command -v gitleaks >/dev/null 2>&1; then
  case "$mode" in
    --staged) gitleaks protect --staged --redact --no-banner || fail=1 ;;
    --tree)   gitleaks detect --no-git --redact --no-banner --source . || fail=1 ;;
    *) echo "unknown mode: $mode" >&2; exit 2 ;;
  esac
  [ "$fail" -eq 0 ] && echo "secret scan (gitleaks): clean"
  exit "$fail"
fi

# --- regex fallback --------------------------------------------------------
# Dedicated high-signal patterns — a match IS a credential. These are NOT run
# through the placeholder IGNORE below, so a trailing "# example" comment on the
# line can't mask a real key (a real-key-bypass the previous version had).
dedicated=(
  'xai-[A-Za-z0-9]{20,}'                       # xAI / Grok
  'sk-ant-[A-Za-z0-9_-]{20,}'                  # Anthropic
  'sk-[A-Za-z0-9]{32,}'                        # OpenAI-style
  'sk_(live|test)_[A-Za-z0-9]{20,}'            # Stripe
  'AKIA[0-9A-Z]{16}'                           # AWS access key id
  'gh[pousr]_[A-Za-z0-9]{30,}'                 # GitHub tokens
  'xox[baprs]-[A-Za-z0-9-]{10,}'               # Slack
  'AIza[0-9A-Za-z_-]{35}'                      # Google API key
  'GOCSPX-[A-Za-z0-9_-]{20,}'                  # Google OAuth secret
  'SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}'   # SendGrid
  'BEGIN [A-Z ]*PRIVATE KEY'                   # private key blocks
)

# Generic backstop: a secret-ish keyword set to a QUOTED 16+char literal.
# Case-insensitive (catches API_KEY / SECRET / Token). Requiring quotes avoids
# matching function calls like  password = hash_password(raw).
generic="(api[_-]?key|secret|token|password|passwd|pwd)[\"' ]*[:=][[:space:]]*[\"'][A-Za-z0-9/+_.=-]{16,}[\"']"
# Obvious non-secrets — applied ONLY to the generic net, never the dedicated ones.
IGNORE='example|placeholder|your[_-]?key|xxxx+|<[a-z_]+>|dummy|sample|redacted|changeme|\$\{'

# Tracked, known-accepted exceptions (one regex per line in .secretsallow at the
# repo root; each references a tracking issue). Applied to ALL hits so a
# documented legacy secret doesn't block every push. See issue #63.
sallow="$(git rev-parse --show-toplevel 2>/dev/null)/.secretsallow"
allow_re=""
[ -f "$sallow" ] && allow_re="$(grep -vE '^[[:space:]]*(#|$)' "$sallow" | paste -sd'|' -)"
filter_allow() { if [ -n "$allow_re" ]; then grep -vE "$allow_re" || true; else cat; fi; }

emit() {  # $1 = label, $2 = hits. Called directly (not piped) so fail=1 persists.
  local label="$1" hits="$2"
  if [ -n "$hits" ]; then
    printf '  \342\234\226 possible secret (%s):\n' "$label" >&2
    printf '%s\n' "$hits" | cut -c1-160 | sed 's/^/      /' >&2
    fail=1
  fi
}

collect() {
  case "$mode" in
    --staged)
      git diff --cached -U0 --no-color -- . "${EXCLUDES[@]}" \
        | grep '^+' | grep -v '^+++'
      ;;
    --tree)
      # awk (not sed) prefixes the path so a '#' or '&' in a filename can't break
      # the substitution and silently drop the file from the scan.
      git ls-files -z -- . "${EXCLUDES[@]}" \
        | while IFS= read -r -d '' f; do
            [ -f "$f" ] && awk -v p="$f" '{print p": "$0}' "$f" 2>/dev/null
          done
      ;;
    *) echo "unknown mode: $mode" >&2; exit 2 ;;
  esac
}

content="$(collect | tr -d '\000')"

# Capture hits via command substitution into a variable, THEN call emit directly,
# so `fail=1` runs in this shell (not a lost subshell) — the bug we just fixed in
# guard_vaults.check_tree.
for pat in "${dedicated[@]}"; do
  hits="$(printf '%s\n' "$content" | grep -nE "$pat" | filter_allow || true)"
  emit "/$pat/" "$hits"
done
ghits="$(printf '%s\n' "$content" | grep -niE "$generic" | grep -viE "$IGNORE" | filter_allow || true)"
emit "generic assignment" "$ghits"

if [ "$fail" -ne 0 ]; then
  cat >&2 <<'MSG'

BLOCKED: possible secret detected — do not commit credentials.
Put it in an untracked .env (already gitignored) and load it at runtime.
False positive? Refine the patterns in tools/scan_secrets.sh.
Bypass once (NOT recommended): git commit --no-verify
MSG
  exit 1
fi
echo "secret scan (regex fallback): clean"
exit 0
