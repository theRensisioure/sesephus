[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("StrictMain", "ToolflowClean", "FullPipeline")]
    [string]$Mode,

    [Parameter(Position=1)]
    [string]$RepoName = "sesefus",

    [switch]$ForcePush
)

Set-Location (Split-Path $PSScriptRoot -Parent)
. (Join-Path $PSScriptRoot "git_repo_maintenance.ps1")

# ============================================================
# VERIFIED COMMITS (only SHAs that exist on current main)
# ============================================================
$sesefusCommits = @(
    @{ sha = "3ccfb2065f3fe1f333748d298b57f0520512bb5f"; msg = "docs: add anecdotal paragraph to prosthetic doc" },
    @{ sha = "7d4ac68"; msg = "fix(host): resolve duplicate lead import and variable typos in command dispatcher" },
    @{ sha = "2bdc387"; msg = "docs: consolidate cleaned prosthetic docs and unify dashboard UI components" },
    @{ sha = "b5b2dcb"; msg = "Merge pull request #22 from Zychs/strict-database-host" },
    @{ sha = "d0b90da"; msg = "docs: archive record on base staging (vault) 2026-06-13" },
    @{ sha = "5a85517"; msg = "docs(ops): import zig-cli operator tooling (path-filter per cherry-pick manifest)" },
    @{ sha = "d0d747a"; msg = "feat(lead): wire qualify to vLLM via tools/qualify_post.py (LeadLogic PR2)" },
    @{ sha = "5ef2a97"; msg = "feat(runtime): unified sesefus binary, LAN discovery, and dual-archive ingress" },
    @{ sha = "3671f5e"; msg = "feat(lead): strict-database-host scaffold with vendored LeadLogic prompts" },
    @{ sha = "21daf17"; msg = "feat(vault): implement core daemon, vault management engine, and security documentation" },
    @{ sha = "27e3704"; msg = "feat(circadia): restore subgroups, bulk edits, interval sequences, and interactive CLI testing" },
    @{ sha = "02f789a"; msg = "feat(cli): refactor host daemon to modular CLI structure and add production safety documentation" },
    @{ sha = "a07f9a9"; msg = "refactor: rebrand system as Sesephus CLI and create dedicated documentation file" },
    @{ sha = "132a06d"; msg = "docs: update workspace organization documentation and clarify module descriptions" },
    @{ sha = "d294d79"; msg = "feat(workspace): consolidate codebase migration, relocate db to V:, establish multi-drive layout" },
    @{ sha = "a5b373a"; msg = "chore: untrack synthesis shards, logs, db, and implement robust .gitignore" },
    @{ sha = "9f090eb"; msg = "docs: initial project README and setup guide" }
)

# ============================================================
# LAYER DEFINITIONS (updated with real current SHAs where possible)
# ============================================================
$sesefusLayers = @(
    @{
        Name    = "Scaffold"
        Sha     = "a5b373a"
        Files   = @(".gitignore", "LICENSE", "core/sesefus/build.zig", "requirements.txt")
        Message = "chore: initialize strict-main orphan scaffold + hardened .gitignore"
    },
    @{
        Name    = "Vault"
        Sha     = "21daf17"
        Files   = @("core/sesefus/src/database.zig", "core/sesefus/src/host.zig")
        Message = "feat(vault): implement encrypted vault, core daemon, and security documentation"
    },
    @{
        Name    = "CLI"
        Sha     = "02f789a"
        Files   = @("core/sesefus/src/cli.zig", "core/sesefus/src/commands/*", "ssfs.bat")
        Message = "feat(cli): modular command structure + production safety documentation"
    },
    @{
        Name    = "LeadLogic"
        Sha     = "3671f5e"
        Files   = @("docs/gemini.md", "tools/qualify_post.py")
        Message = "feat(lead): strict-database-host scaffold with vendored LeadLogic prompts"
    },
    @{
        Name    = "Runtime"
        Sha     = "5ef2a97"
        Files   = @("core/sesefus/src/host.zig", "ssfs.bat")
        Message = "feat(runtime): unified sesefus binary, LAN discovery, dual-archive ingress"
    }
)

# ============================================================
# ROBUST TOOLFLOW-CLEAN IMPLEMENTATION (with conflict resolution)
# ============================================================
function New-ToolflowCleanBranch {
    param(
        [string]$TargetBranch,
        [string]$BaseSha,
        [array]$Commits
    )

    Write-Log "Creating clean integration branch '$TargetBranch' from base $BaseSha..." "Cyan"
    
    # Try to checkout, if it fails due to local changes, warn the user
    git checkout -B $TargetBranch $BaseSha 2>&1 | ForEach-Object {
        Write-Log $_ "Yellow"
    }

    foreach ($commit in $Commits) {
        $sha = $commit.sha
        $msg = $commit.msg

        # Skip if commit does not exist on current main
        if (-not (git cat-file -t $sha 2>$null)) {
            Write-Log "  SKIPPING $sha — not found on current main" "Yellow"
            continue
        }

        Write-Log "Cherry-picking $sha — $msg" "Yellow"

        $result = git cherry-pick $sha --strategy=recursive --strategy-option=theirs 2>&1

        if ($LASTEXITCODE -ne 0) {
            if ($result -match "CONFLICT|conflict") {
                Write-Log "  Conflict at $sha — resolving in favor of incoming (refined) code..." "Red"
                git checkout --theirs .
                git add -A
                
                # Check if there is anything to commit
                $status = git status --porcelain
                if ($null -eq $status -or $status -eq "") {
                    Write-Log "  Nothing to commit after resolution, skipping $sha" "Yellow"
                    git cherry-pick --skip
                } else {
                    git cherry-pick --continue --no-edit
                    Write-Log "  Conflict resolved (incoming changes kept)." "Green"
                }
            } else {
                Write-Log "  Non-conflict error at $sha — aborting this pick." "Red"
                git cherry-pick --abort 2>$null
                continue
            }
        } else {
            Write-Log "  Successfully applied $sha" "Green"
        }
    }

    git log --oneline -8
    Write-Log "Branch '$TargetBranch' created successfully with verified history." "Cyan"
}

# ============================================================
# MODE SWITCH
# ============================================================
switch ($Mode) {
    "StrictMain" {
        New-StrictMainBranch -TargetBranch "strict-main" -SourceBranch "main" -Layers $sesefusLayers
    }

    "ToolflowClean" {
        New-ToolflowCleanBranch -TargetBranch "toolflow-clean-refined" -BaseSha "21daf17" -Commits $sesefusCommits

        if ($ForcePush) {
            Publish-ToGitHub -RepoName $RepoName -Visibility "private" `
                -SourceBranch "toolflow-clean-refined" -DestBranch "main" -Force
        }
    }

    "FullPipeline" {
        New-ToolflowCleanBranch -TargetBranch "toolflow-clean-refined" -BaseSha "21daf17" -Commits $sesefusCommits

        Publish-ToGitHub -RepoName $RepoName -Visibility "private" `
            -SourceBranch "toolflow-clean-refined" -DestBranch "main" -Force
    }
}
