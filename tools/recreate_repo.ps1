# Publish toolflow-clean history to a fresh GitHub repo via gh.
#
# Prereqs:
#   1. pwsh tools/remap_history.ps1
#   2. pwsh tools/gh.ps1 auth login
#
# Usage:
#   pwsh tools/recreate_repo.ps1 -RepoName sesefus-clean -Visibility private
#   pwsh tools/recreate_repo.ps1 -RepoName sesefus -Visibility public -ForcePush

param(
    [string]$RepoName = "sesefus",
    [ValidateSet("public", "private", "internal")]
    [string]$Visibility = "private",
    [string]$Branch = "toolflow-clean",
    [switch]$ForcePush
)

$ErrorActionPreference = "Stop"
$gh = Join-Path $PSScriptRoot "gh.ps1"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (git rev-parse --verify "$Branch^{commit}" 2>$null)) {
    throw "Branch '$Branch' not found. Run tools/remap_history.ps1 first."
}

$auth = & $gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host $auth
    throw "Not authenticated. Run: pwsh tools/gh.ps1 auth login"
}

Write-Host "Creating GitHub repo '$RepoName' ($Visibility) ..."
& $gh repo create $RepoName --$Visibility --source . --remote new-origin --description "Sesephus/Sesefus — offline-first voice growth engine (clean toolflow history)" 2>&1 | Out-Host

if ($LASTEXITCODE -ne 0) {
    Write-Host "Repo may already exist. Adding remote 'new-origin' if missing ..."
    $owner = (& $gh api user -q .login).Trim()
    git remote remove new-origin 2>$null | Out-Null
    git remote add new-origin "https://github.com/$owner/$RepoName.git"
}

$pushArgs = @("push", "new-origin", "${Branch}:main")
if ($ForcePush) { $pushArgs += "--force" }

Write-Host "Pushing $Branch -> main on new-origin ..."
git @pushArgs

Write-Host ""
Write-Host "Repository ready:"
& $gh repo view "$RepoName" --web 2>$null | Out-Null
Write-Host "  git remote -v"
Write-Host "  git log --oneline new-origin/main"