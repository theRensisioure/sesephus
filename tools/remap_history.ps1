# Rebuild a linear, conventionally-titled history for Sesephus/Sesefus.
# Creates branch `toolflow-clean` from the first scaffold commit, then
# cherry-picks each feature commit with remapped titles aligned to the
# version matrix in docs/gemini.md.
#
# Usage (from repo root):
#   pwsh tools/remap_history.ps1
#   git log --oneline toolflow-clean

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$targetBranch = "toolflow-clean"
$baseSha = "ed6c492"

# Chronological non-merge commits after base, with remapped conventional titles.
# `stack` maps to the PR/feature branch that should have carried this change.
$commits = @(
    @{ sha = "4ac4a1f"; msg = "chore: segregate name signals from baseline"; stack = $null }
    @{ sha = "9f090eb"; msg = "docs: add project README and setup guide"; stack = $null }
    @{ sha = "a5b373a"; msg = "chore: untrack generated artifacts and harden .gitignore"; stack = $null }
    @{ sha = "d294d79"; msg = "feat(workspace): establish multi-drive layout (S:, V:, F:)"; stack = $null }
    @{ sha = "2edef26"; msg = "docs: add gemini.md agent optimization guidelines"; stack = $null }
    @{ sha = "4306a6a"; msg = "docs: document staging-to-git sync workflow"; stack = $null }
    @{ sha = "e6048ac"; msg = "feat(circadia): add subgroups, bulk edits, and interval sequences"; stack = $null }
    @{ sha = "8b5f7af"; msg = "docs(circadia): add alarm engine README and API reference"; stack = $null }
    @{ sha = "f676a2a"; msg = "feat(dashboard): add Lighthouse Portal glassmorphism UI"; stack = "feat/telemetry-lighthouse-ui" }
    @{ sha = "7b5d787"; msg = "feat(host): embed local testing client thread in host daemon"; stack = "feat/embed-client" }
    @{ sha = "667453e"; msg = "feat(build): add build_client.ps1 for multi-device targets"; stack = "feat/orchestrated-inference" }
    @{ sha = "f26a58e"; msg = "fix(build): quote build target argument in build_client.ps1"; stack = "feat/orchestrated-inference" }
    @{ sha = "e4a06d7"; msg = "docs: add repository version sequence to gemini.md"; stack = $null }
    @{ sha = "ecae614"; msg = "chore(cli): add ssfs.bat Windows build-and-dispatch wrapper"; stack = $null }
    @{ sha = "27e3704"; msg = "feat(circadia): restore subgroups and interactive CLI testing"; stack = "feat/restore-subgroups-intervals" }
    @{ sha = "21daf17"; msg = "feat(vault): implement encrypted vault and core daemon security"; stack = "vault-security-and-management-of--database" }
    @{ sha = "ecec37e"; msg = "docs: add machine-readable workspace manifest"; stack = "CLI-Reinforcement" }
    @{ sha = "a114cdd"; msg = "feat(cli): add runtime help and interactive command shell"; stack = "CLI-Reinforcement" }
    @{ sha = "d473cc5"; msg = "docs: add comprehensive Gemini agent optimization guide"; stack = "CLI-Reinforcement" }
    @{ sha = "02f789a"; msg = "feat(cli): refactor host daemon to modular command structure"; stack = "CLI-Reinforcement" }
    @{ sha = "132a06d"; msg = "docs: update workspace organization and module descriptions"; stack = "CLI-Reinforcement" }
)

# These land on main after parallel PR merges; cherry-pick often conflicts on README.
# Applied from `main` tip instead of replaying SHAs.
$tailCommits = @(
    @{ files = @("README.md", "overallreadmee.md"); msg = "refactor: rebrand as Sesephus CLI with dedicated documentation"; stack = $null }
    @{ files = @("README.md", "docs/GIT_WORKFLOW.md", "tools/gh.ps1", "tools/recreate_repo.ps1", "tools/remap_history.ps1"); msg = "fix(docs): resolve README merge conflict and add git toolflow tooling"; stack = $null }
)

function Ensure-Clean-Tree {
    $status = git status --porcelain
    if ($status) {
        throw "Working tree is not clean. Commit or stash changes before remapping history."
    }
}

Ensure-Clean-Tree

if (-not (git rev-parse --verify "$baseSha^{commit}" 2>$null)) {
    throw "Base commit $baseSha not found."
}

Write-Host "Creating branch '$targetBranch' from $baseSha ..."
git branch -D $targetBranch 2>$null | Out-Null
git checkout -B $targetBranch $baseSha

$applied = 0
$skipped = @()

foreach ($entry in $commits) {
    $sha = $entry.sha
    $msg = $entry.msg
    $stack = $entry.stack

    if (-not (git rev-parse --verify "$sha^{commit}" 2>$null)) {
        $skipped += "$sha (missing)"
        continue
    }

    Write-Host "Cherry-picking $sha -> $msg"
    git cherry-pick -x $sha 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Cherry-pick conflict on $sha — aborting."
        git cherry-pick --abort 2>$null | Out-Null
        throw "Stopped at $sha. Resolve manually or adjust remap_history.ps1."
    }

    if ($stack) {
        $fullMsg = "$msg`n`nStack-PR: $stack"
    } else {
        $fullMsg = $msg
    }

    git commit --amend -m $fullMsg
    $applied++
}

$sourceBranch = "main"
if (-not (git rev-parse --verify "$sourceBranch^{commit}" 2>$null)) {
    $sourceBranch = "master"
}

foreach ($tail in $tailCommits) {
    Write-Host "Applying tail commit from $sourceBranch -> $($tail.msg)"
    foreach ($file in $tail.files) {
        git checkout $sourceBranch -- $file 2>$null | Out-Null
    }
    git add @($tail.files)
    if ($tail.stack) {
        $fullMsg = "$($tail.msg)`n`nStack-PR: $($tail.stack)"
    } else {
        $fullMsg = $tail.msg
    }
    git commit -m $fullMsg
    $applied++
}

Write-Host ""
Write-Host "Done. Applied $applied commits on '$targetBranch'."
if ($skipped.Count -gt 0) {
    Write-Host "Skipped: $($skipped -join ', ')"
}
Write-Host "Review: git log --oneline --graph $targetBranch"