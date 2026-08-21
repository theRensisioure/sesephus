# Sesefus Roadmap

What's next, in order. First public stamp is **0.1.0 (prerelease)** (2026-08-21).
Progress lives here; history lives in [CHANGELOG.md](CHANGELOG.md).

## Working rules

- **One feature branch = one squash PR into `main`.** Easy to read, easy to bisect, easy to revert.
- **Every merged PR adds a line to `CHANGELOG.md` under `[Unreleased]`.** Thirty seconds, while it's fresh.
- **Lane discipline:** Sesefus core only — `ssfs`, vault, host, dashboard. Side quests
  (audio, SaturnNav, Circadia) may swap in for a planned rung, but they follow the same
  one-branch-one-PR rule.
- **Ship marker:** when the ladder below is done, cut a `prerelease` tag. That's the first
  version number this project gets.

## GitHub rhythm (AyTree ↔ Sesefus)

- **AyTree (`Zychs/AyTree`)** — day-to-day execution. Phases A–F milestones,
  vision issues, PRs. This is where work lives.
- **Sesefus (`Zychs/sesefus`)** — product completions only. When an AyTree phase
  ships, post **one** Sesefus issue or release note: "AyTree Phase B complete → [link]".
  No duplicate phase planning, no granular AyTree issue mirroring here.
- **Labs** (AyTree, SaturnNav, etc.) surface on Sesefus Shipment Dock as external
  links — not as Sesefus milestones.

## The ladder

### ✅ SSFS config-driven storage layer — shipped (PR #26)
- `ssfs/drive-mapping.json` — V:/E:/T: drive contract
- `ssfs/storage/config-engine.js` — label verify + receipt
- `ssfs/storage/paths.js` — resolver API
- `docs/PRODUCTION.md` §5 — SSFS guardrails
- Host hook landed with autostart deliberately paused

### ⬜ Module extraction (`feat/extract-modules`)
Extract cli / capture / net into modules:
- `src/cli/flags.zig`
- `src/modules/capture/wav_record.zig`
- `src/net/protocol.zig`
- `.gitignore` hardening

*Merge note: rebase onto current `main`; expect a `.gitignore` conflict with the
ssfs-storage work already merged.*

### ⬜ Dashboard on the path resolver
Dashboard/sidecar consume `ssfs/storage/paths.js`; zero hardcoded `V:` paths remain
in dashboard code.

### ⬜ Vault resolver migration
Migrate remaining vault hardcodes to the resolver, per `docs/vault_security.md`.

### ⬜ Host storage integration
Re-enable the Zig autostart drive verifier (behind an optional flag).

### ⬜ End the stubs (umbrella [#74](https://github.com/Zychs/sesefus/issues/74))
Phase 0 honesty (#66) → purge DEAD (#67) → journal/rhythm redirect (#68, #69) →
vault wire (#70) → defer the rest honestly (#71–#73).
Rule: **no command in README/help until CANON §2 says WIRED.**

### ⬜ Prerelease hardening
Production checklist pass, redundancy verify script, doc sync.

### 🏁 Ship
Tag `prerelease` on `main`. First version number gets assigned here.

## Open loops (carried from planning)

- [ ] Rebase `feat/extract-modules` onto post-ssfs `main` and PR it
- [ ] Confirm or swap the scope of the middle rungs (dashboard/vault/host) against
      whatever is hottest at the time
- [ ] Voice-control/ETDI pipeline (PR #25) merged outside the ladder — its follow-ups
      go through normal one-branch-one-PR flow
