# Vault guard

Vaults are **local-only**. A vault file must never be committed to git or sit in
history. These scripts enforce that.

## Files
- `tools/guard_vaults.sh` — detector. Flags vault data by filename
  (`*.db`, `*.sqlite`, `*vault*`, `*sidevault*`) **and** by content (first 8
  bytes = the `SESEPHUS` vault magic, so a renamed vault is still caught).
- `.githooks/pre-commit` — runs the detector on staged changes and aborts the
  commit if a vault is found.
- `tools/install_guards.sh` — one-time enable in a fresh clone.

## Enable (once per clone)
```bash
bash tools/install_guards.sh
# equivalent to:  git config core.hooksPath .githooks
```
Git hooks are not shared automatically, so every clone runs this once.
PowerShell: `git config core.hooksPath .githooks`

## Use
```bash
tools/guard_vaults.sh --staged     # what the hook runs
tools/guard_vaults.sh --tree       # scan working tree + untracked files
tools/guard_vaults.sh --history    # audit every blob in every branch/tag
```
Exit code `1` means vault data was found. In CI, run `--history` to fail the
build if a vault ever lands in any ref.

## If the hook blocks a legitimate commit
Inspect the reported file. Real false positives should be rare (only a file
whose first bytes are literally `SESEPHUS`). To override a single commit:
`git commit --no-verify` (discouraged).
