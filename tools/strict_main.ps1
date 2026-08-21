# Build `strict-main`: a minimal orphan foundation with three sequenced imports.
#
# Layer 0 — empty scaffold (build deps only, no feature code)
# Layer 1 — vault-security-and-management-of--database  (21daf17)
# Layer 2 — gemini prompt engineering                    (2edef26 → e4a06d7 → d473cc5)
# Layer 3 — alarm CLI system                             (curated from e6048ac, 27e3704,
#           a114cdd, 02f789a, 8b5f7af, ecec37e — scratch/ and unrelated stacks excluded)
#
# Usage (from repo root):
#   pwsh tools/strict_main.ps1
#   git log --oneline strict-main

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$targetBranch = "strict-main"
$sourceBranch = "main"

# --- Layer 0: minimal scaffold (no alarms, no vault engine, no agent docs) ---
$scaffoldFiles = @(
    ".gitignore"
    "LICENSE"
    "core/sesephus/build.zig"
    "core/sesephus/run_demo.bat"
    "core/sesephus/src/common.zig"
    "core/sesephus/src/crypto.zig"
    "requirements.txt"
)

# Pre-vault client stub — parent of vault commit, before circadia/CLI overlays.
$scaffoldClientSha = "ecae614"

# --- Layer 1: database / vault branch ---
$vaultSha = "21daf17"
$vaultFiles = @(
    "core/sesephus/src/database.zig"
    "core/sesephus/src/host.zig"
    "docs/vault_security.md"
)

# --- Layer 2: gemini prompt engineering ---
# Final gemini.md after version-sequence + comprehensive guide commits.
$geminiSha = "d473cc5"
$geminiFiles = @(
    "docs/gemini.md"
    "docs/manifest.json"
)
# manifest landed in CLI-Reinforcement (ecec37e) but is agent-context; pair with gemini layer.
$manifestSha = "ecec37e"

# --- Layer 3: alarm CLI — files at integrated tip, excluding scratch refactor scripts ---
$cliTipSha = $sourceBranch
$cliFiles = @(
    "core/sesephus/src/cli.zig"
    "core/sesephus/src/commands/journal.zig"
    "core/sesephus/src/commands/lead.zig"
    "core/sesephus/src/commands/rhythm.zig"
    "core/sesephus/src/commands/stoic.zig"
    "core/sesephus/src/commands/vault.zig"
    "core/sesephus/src/host.zig"
    "core/sesephus/src/client.zig"
    "core/sesephus/src/dashboard.html"
    "core/sesephus/README.md"
    "core/sesephus/test_circadia_advanced.py"
    "docs/sesephus_help.md"
    "docs/CLI.md"
    "docs/PRODUCTION.md"
    "ssfs.bat"
)

# Provenance map for layer-3 (embedded across commits — not a single branch tip).
$cliProvenance = @"
Alarm CLI import sources (curated, scratch/ excluded):
  e6048ac — circadia subgroups, bulk edits, interval sequences (host.zig, dashboard.html, test_circadia_advanced.py)
  8b5f7af — circadia alarm engine README (core/sesephus/README.md)
  27e3704 — restore circadia + interactive CLI testing (host.zig, dashboard.html)
  a114cdd — runtime help shell (client.zig, host.zig help paths, docs/sesephus_help.md)
  02f789a — modular command structure (cli.zig, commands/*, CLI.md, PRODUCTION.md, ssfs.bat)
  ecec37e — workspace manifest (docs/manifest.json, paired in layer 2)
Files checked out from integrated $sourceBranch tip where histories overlap.
"@

function Ensure-Clean-Tree {
    $status = git status --porcelain --untracked-files=no
    if ($status) {
        throw "Working tree has staged/unstaged tracked changes. Commit or stash before building strict-main."
    }
}

function Checkout-Files {
    param([string]$Sha, [string[]]$Files)
    foreach ($file in $Files) {
        git checkout $Sha -- $file 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            throw "Could not checkout $file from $Sha"
        }
    }
}

function Write-Stub-Readme {
    @"
# Sesephus (strict-main foundation)

This branch is a **sequenced foundation** rebuilt from orphan — not a replay of tangled ``main`` history.

| Layer | Import | Status |
| :---: | :--- | :--- |
| 0 | Empty scaffold (build deps) | root commit |
| 1 | ``vault-security-and-management-of--database`` | database + vault daemon |
| 2 | Gemini prompt engineering | ``docs/gemini.md``, ``docs/manifest.json`` |
| 3 | Alarm CLI system | modular ``commands/*``, circadia host, help docs |

See ``tools/strict_main.ps1`` to rebuild. Full workflow matrix: ``docs/GIT_WORKFLOW.md``.
"@ | Set-Content -Path "README.md" -Encoding utf8NoBOM
}

Ensure-Clean-Tree

if (-not (git rev-parse --verify "$sourceBranch^{commit}" 2>$null)) {
    throw "Source branch '$sourceBranch' not found."
}

Write-Host "Creating orphan branch '$targetBranch' ..."
git branch -D $targetBranch 2>$null | Out-Null
git checkout --orphan $targetBranch
git rm -rf --cached . 2>$null | Out-Null

# Layer 0
Write-Host "Layer 0: scaffold ..."
Checkout-Files "a5b373a" @(".gitignore")
Checkout-Files $sourceBranch @(
    "LICENSE"
    "core/sesephus/build.zig"
    "core/sesephus/run_demo.bat"
    "core/sesephus/src/common.zig"
    "core/sesephus/src/crypto.zig"
    "requirements.txt"
)
Checkout-Files $scaffoldClientSha @("core/sesephus/src/client.zig")
Write-Stub-Readme
$layer0 = @("README.md") + $scaffoldFiles + @("core/sesephus/src/client.zig")
git add @($layer0)
git commit -m "chore: initialize strict-main orphan scaffold"

# Layer 1
Write-Host "Layer 1: vault / database branch import ($vaultSha) ..."
Checkout-Files $vaultSha $vaultFiles
git add @($vaultFiles)
$vaultMsg = @"
feat(vault): import database branch (vault-security-and-management-of--database)

Stack-PR: vault-security-and-management-of--database
Source-SHA: $vaultSha
"@
git commit -m $vaultMsg

# Layer 2
Write-Host "Layer 2: gemini prompt engineering import ..."
Checkout-Files $geminiSha @("docs/gemini.md")
Checkout-Files $manifestSha @("docs/manifest.json")
git add @($geminiFiles)
$geminiMsg = @"
docs(gemini): import prompt engineering branch

Sources: 2edef26 (initial guide), e4a06d7 (version sequence), d473cc5 (comprehensive guide)
Manifest: ecec37e (machine-readable workspace context for agents)
"@
git commit -m $geminiMsg

# Layer 3
Write-Host "Layer 3: alarm CLI system import (curated from $cliTipSha) ..."
Checkout-Files $cliTipSha $cliFiles
git add @($cliFiles)
$cliMsg = @"
feat(cli): import alarm CLI system (curated multi-commit extraction)

$cliProvenance
"@
git commit -m $cliMsg

Write-Host ""
Write-Host "Done. strict-main has 4 commits (scaffold + 3 foundation layers)."
Write-Host "Review: git log --oneline strict-main"