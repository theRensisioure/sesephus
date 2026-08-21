# ARCHIVED BRANCHES - 2026-06-13 (sesefus base staging copy)

Base staging branch (vault-security-and-management-of--database) copy of archive record.

Full details on main (including table of feat/unified-runtime-archive and feat/restore-subgroups-intervals archived with tags archive/*-20260613).

Context: post ac00128, sesefus#19 authored, INDEX/§10/leadlogic/alignment followed. Only merged (behind) archived; this base + main remain as designated.

See main branch ARCHIVED-BRANCHES.md for complete cross references, tags, and process notes.
# ARCHIVED BRANCHES - 2026-06-13

**Context (full alignment through and through)**
- Post Zychs/repo-libs-naissance main push ac00128 ("docs(prompting): sync meta/INDEX §10 tool selection/orchestration/token budget funnel, jetstream profile-align prompts...").
- Prior: reviewed all Zychs GitHub repos for mains needing PRs; authored sesefus#19 (strict-database-host with vendored qualify-post Systems Peer), intuitree#1 (swarm-path-tuner-governor), groxi-ui#1 (VC drift guardrails).
- Mandates followed: leadlogic skill + global rule (canonical naissance prompts only, Systems Peer as judge, 3-stage CPU triage <0.55/>=0.78/0.55-0.77, @handle hydration, INDEX route first).
- Alignment: context-economist (todos with seeds, relative paths in *all* calls, enter_plan on ambig, economy), session-curator, localization-guardian (no UI edits triggered).
- §10 funnel applied: temperature (Warm/Agent for infra/branch hygiene) → deliverable (clean branches + detailed notes) → minimal toolchain (gh api/MCP push_files/list_branches, no glob) → smoke (targeted compares first).
- Staging contract per prompting-infrastructure.md §6: compose → T: → ~/.grok → git (here: archive to tags, notes on main).
- No ad-hoc; only required files loaded (INDEX first, then infra references from grep).

**Per-repo policy applied**
- Archive *only* branches with compare status "behind" (0 ahead, fully merged into main).
- Leave main + designated "base staging" (see below).
- Do not touch heads with open PRs or no-common-ancestor special cases (e.g. strict-main, feat/jetstream-profile-align-pipeline).
- Tags created under refs/tags/archive/<sanitized>-20260613 for recovery.
- Detailed notes committed via MCP push_files (relative discipline, no local git identity issues).

## Zychs/sesefus
- **main**: 5a8551735a5061e96f5c9f996b557f0cfb38ea05
- **base staging**: vault-security-and-management-of--database (sha d38637068798773e423befcf00ac56e89f228dc9; explicit per leadlogic skill "scaffolds on vault... → strict-database-host", infra §6 staging contract, hot-mvp-blueprint "strict-main layers" + "unified-runtime-archive stacked on strict-database-host").
- Active PR head left: strict-database-host (sesefus#19, diverged 1/17, vendored LeadLogic prompts/Systems Peer).
- strict-main: no common ancestor with main (special history per blueprint; NOT archived).

**Archived (confirmed behind/merged)**:

| Branch | Tip SHA (pre-archive) | Compare vs main | Tag created | Alignment / Reason notes |
|--------|-----------------------|-----------------|-------------|----------------------------|
| feat/unified-runtime-archive | 5ef2a97c1c570cf398a83607390325860a37994e | behind (0/3) | archive/feat-unified-runtime-archive-20260613 | Matches "unified-runtime-archive" + "unified sesefus binary" work; aligns with infra §6 staging + hot-mvp "unified archive" after naissance ac00128 prompting sync. Fully merged, safe to archive. |
| feat/restore-subgroups-intervals | d473cc5b5c27ebfce482a5690e561d8d85b97563 | behind (0/15) | archive/feat-restore-subgroups-intervals-20260613 | Old feat for subgroups; behind main, no open PR. Archived per "all merged branches". |

**Remaining visible branches**: main, vault-security-and-management-of--database (plus active PR head strict-database-host until merge).

**Tags**: refs/tags/archive/*-20260613 (recoverable).

## Other repos (see their ARCHIVED-BRANCHES.md for full)
- Similar process applied to Zychs/LeadLogic-Engine (base: setup-infrastructure), Zychs/repo-libs-naissance (base: governance/ebike-range-finder-audit-2026-06-12 for current aligned meta), Zychs/intuitree (temp base: feat/swarm-path-tuner-governor), Zychs/groxi-ui (temp base: experimental).
- Only behind/merged extras archived.
- No-common-ancestor cases (LeadLogic-Engine feat/jetstream-profile-align-pipeline) and ahead PR heads left untouched.

**Verification**: Re-list branches post-action shows reduction. Notes pushed to main (and base where distinct). Followed full mandate for branch hygiene as orchestration per §10.

See also: repo-libs-naissance ac00128, sesefus#19, intuitree#1, groxi-ui#1, prior review session.
