# Sesephus Git & GitHub Tool Flow

This guide documents how changes **should** be staged, committed, and published — aligned with the version matrix in `docs/gemini.md` and the multi-drive workflow.

## The Three-Layer Model

| Layer | Path (your setup) | Role |
| :--- | :--- | :--- |
| **Staging** | `S:\arcadium-circadia` | Active development, builds, tests. **Not** a git repo. |
| **Git mirror** | `F:\git\Arcadiumandcircadia` or local clone | Audit, commit, push. Only source that reaches GitHub. |
| **Runtime data** | `V:\` | Databases, logs, vault (`sesephus_vault.db`). Never committed. |

**Rule:** Code in staging → mirror to git → one logical commit per concern → open PR → merge to `main`.

---

## How You Should Have Staged the Series

Each milestone below maps to **one feature branch** and **one squash-merge PR**. Do not mix concerns in a single commit.

### Stack 1 — Foundation (`main`, v2.0.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 1 | `main` | `chore: untrack generated artifacts and harden .gitignore` | `.gitignore` only |
| 2 | `main` | `feat(workspace): establish multi-drive layout (S:, V:, F:)` | Path/config changes, not docs |
| 3 | `main` | `docs: add gemini.md agent optimization guidelines` | `docs/gemini.md` |
| 4 | `main` | `docs: document staging-to-git sync workflow` | Sync script + gemini.md §P |

### Stack 2 — Circadia core (`main`, v3.0.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 5 | `feat/circadia-intervals` | `feat(circadia): add subgroups, bulk edits, and interval sequences` | `core/` alarm engine only |
| 6 | `feat/circadia-intervals` | `docs(circadia): add alarm engine README and API reference` | `core/sesephus/README.md` |

### Stack 3 — Dashboard (`feat/telemetry-lighthouse-ui`, v3.1.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 7 | `feat/telemetry-lighthouse-ui` | `feat(dashboard): add Lighthouse Portal glassmorphism UI` | `dashboard/ui/` only |

### Stack 4 — Host embed (`feat/embed-client`, v3.2.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 8 | `feat/embed-client` | `feat(host): embed local testing client thread in host daemon` | `core/sesephus/src/host.zig` + related |

### Stack 5 — Multi-device build (`feat/orchestrated-inference`, v3.3.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 9 | `feat/orchestrated-inference` | `feat(build): add build_client.ps1 for multi-device targets` | `build_client.ps1`, `.gitignore` zig-out |
| 10 | `feat/orchestrated-inference` | `fix(build): quote build target argument in build_client.ps1` | Same file only |

### Stack 6 — Vault security (`vault-security-and-management-of--database`)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 11 | `vault-security-and-management-of--database` | `feat(vault): implement encrypted vault and core daemon security` | `core/sesephus/src/crypto.zig`, `database.zig`, `docs/vault_security.md` |

### Stack 7 — CLI reinforcement (`CLI-Reinforcement`, v3.4.0 → v4.0.0)

| Order | Branch | Commit title | What to stage |
| :---: | :--- | :--- | :--- |
| 12 | `CLI-Reinforcement` | `docs: add machine-readable workspace manifest` | `docs/manifest.json` + README pointer |
| 13 | `CLI-Reinforcement` | `feat(cli): add runtime help and interactive command shell` | `src/cli.zig`, help strings |
| 14 | `CLI-Reinforcement` | `feat(cli): refactor host daemon to modular command structure` | `src/commands/*` |
| 15 | `CLI-Reinforcement` | `docs: update workspace organization and module descriptions` | `README.md`, `overallreadmee.md` |
| 16 | `main` | `refactor: rebrand as Sesephus CLI with dedicated documentation` | `README.md`, `docs/CLI.md`, `ssfs.bat` |
| 17 | `main` | `fix(docs): resolve README merge conflict from CLI-Reinforcement` | `README.md` conflict markers only |

---

## Commit Title Format

```
<type>(<scope>): <imperative summary>
```

| Type | When |
| :--- | :--- |
| `feat` | New behavior |
| `fix` | Bug or conflict repair |
| `docs` | Documentation only |
| `chore` | Tooling, gitignore, wrappers |
| `refactor` | Reorg without behavior change |

**Bad titles from history (do not repeat):** `script bad`, `cli help`, `: embed local testing client thread into host`

---

## Daily Workflow

```powershell
# 1. Develop in staging
cd S:\arcadium-circadia
# ... edit, zig build, test ...

# 2. Mirror to git workspace (when sync script exists)
python S:\arcadium-circadia\sync_to_git.py

# 3. Commit one concern at a time
cd F:\git\Arcadiumandcircadia   # or C:\Users\bardw\sesefus
git checkout -b feat/my-feature
git add core/sesephus/src/commands/journal.zig
git commit -m "feat(cli): add journal record command with duration limit"

# 4. Push and open PR
pwsh tools/gh.ps1 auth login      # once
pwsh tools/gh.ps1 pr create --title "feat(cli): journal record command" --body "Adds duration-limited voice journaling."

# 5. Merge via GitHub UI or:
pwsh tools/gh.ps1 pr merge --squash
```

---

## Rebuilding Clean History (this repo)

If history is tangled (merge commits, bad titles, conflict markers committed):

```powershell
# Fix working tree first, then:
git add README.md
git commit -m "fix(docs): resolve README merge conflict from CLI-Reinforcement"

pwsh tools/remap_history.ps1
git log --oneline toolflow-clean

# After gh auth:
pwsh tools/recreate_repo.ps1 -RepoName sesefus -Visibility private
```

`toolflow-clean` is a **linear replay** with conventional titles. It does not rewrite `main` unless you force-push deliberately.

---

## gh Not in PATH?

GitHub CLI installs to `C:\Program Files\GitHub CLI\gh.exe`. Use the wrapper:

```powershell
pwsh tools/gh.ps1 --version
pwsh tools/gh.ps1 auth login
pwsh tools/gh.ps1 repo clone theRensisioure/sesephus
```

Or add to your PowerShell profile:

```powershell
$env:Path += ";C:\Program Files\GitHub CLI"
```