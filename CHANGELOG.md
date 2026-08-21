# Changelog

History of what actually shipped, newest first. Public tree starts at **0.1.0
(prerelease)** on 2026-08-21. Earlier bullets were reconstructed from the
private `Zychs/sesefus` line and are marked as such.

## [Unreleased]

### Docs
- **Public mouth (2026-08-21):** clone door is `theRensisioure/sesephus`. Tester
  guide no longer points at `Zychs/sesefus`. CANON §1 names **Sesephus** as this
  repo's product; `sesefus.exe` stays the binary. Not lighthouse
  `theRensisioure/sesefus`.

## [0.1.0] - 2026-08-21

Prerelease. First public cut of **Sesephus**.

### Added
- Public GitHub repo `theRensisioure/sesephus` with a fresh git history.
- Python journal face under `apps/` (daemon, clip, hop, skills window, tangent analyzer, goal minter) as it stood on the private tree.

### Notes
- Not a freeze of private `Zychs/sesefus`. That remote stays the private product.
- Vault default password is still a documented caveat. Do not treat it as a secret.
- Bullets below were reconstructed from the private line. They already live in this 0.1.0 tree (not future work).

### Docs
- **Circadia honesty (2026-08-12):** `core/sesephus/README.md` is now a WIP door
  (one `sesefus.exe`, no `host.exe`/`client.exe`, journal/rhythm stubs).
  `run_demo.bat` launches the real binary and the real `alarm schedule` syntax.
  `overallreadmee.md` and `docs/vision.md` marked dated so they cannot be
  repoed as current.

### Removed
- **Purge DEAD code (#67):** deleted the unreachable second `handleVaultCommand` in
  `host.zig` (~150 lines of vault crypto ops the dispatcher never routed to),
  `core/alarm_engine.zig` (superseded standalone scheduler), and the nine
  one-shot `scratch/*.py` refactor scripts that patched the old handler.

### Fixed
- **Stub honesty pass (Phase 0 of "End the stubs", #74/#66):** no surface claims
  a stub works. README leads with `voice.bat` (the real journal path) and lists
  unwired commands honestly; `docs/CLI.md` carries a stale-banner deferring to
  CANON §2; `docs/sesephus_help.md` drops removed `host.exe`/`client.exe` (#51);
  Circadia.jsx no longer fabricates mock alarms/groups when the backend is down —
  failures surface as errors (#42); EtdiPanel.jsx shows the canonical norm-form
  ETDI formula @0.30 (#40); REPL startup banner regenerated to space-separated
  commands, DEAD `vault_*` lines removed, and `help` output now matches CANON §2.

### Added
- **Alarm hop** (`apps/journal-daemon/`): fire writes a cue page and opens the designated Sound Recorder. Optional `sound` / `picture` on a window ride the same pair. `python hop.py --fire morning`. Not a third app. Not embed. Not curation-retrieval.
- **Skills window** (`apps/skills-window/`): marketplace item — own window on
  `:8788`, lists Grok skill dirs with one-click folder open. New providers are
  one object in `providers.json` (or `POST /api/providers`) then Reload.
- **Artifact sieve** (`shredder/artifact_sieve.py` + Sieve shipment UI): comb
  Google Gemini / Takeout chat dumps (conversations.json mapping DAGs, My
  Activity, AI Studio applet history, HTML) into the same `DebrisChunk` →
  `ingest/debris_shards.jsonl` path as text/image sieves. Dashboard scanner
  view opens a directory, inventories dump files, shreds via
  `/api/sieve/scan` + `/api/sieve/shred`. Docs: `docs/ARTIFACT_SIEVE.md`.
- **Covenant spine** (`covenant-spine` branch): one dialogic turn-taking loop
  over the encrypted vault with modality as a swappable profile.
  `commands/dialogue.zig` (`dialogue start|review [appliance] [n]` — one prompt
  at a time, empty replies never punished), `speech.zig` (first spoken-output
  path: offline OS synths only — SAPI/PowerShell on Windows, espeak-ng on
  POSIX, additive and gracefully degrading), prose fields on `JournalEntry`
  (`entry_kind`/`text`/`prompt`/`session_id`, same encrypted frames as audio,
  both-ways compatible), `docs/COVENANT.md` (the maker-may-concede /
  user-never-must boundary + verification recipes), and
  `dashboard/ui/src/dyslexiui-tokens.css` (DyslexiUI as canonical reading
  layer). POSIX portability: `runtime_config.zig` and the default vault path no
  longer produce literal `V:\`/`E:\` files on Linux (the appliance target);
  host CLI passes its stdin reader into command handlers so sub-loops don't
  fight it for input.
- `CHANGELOG.md` + `ROADMAP.md` — single-file changelog and version-free roadmap.
- **Vault guard** (PR #31, imported from `claude/unprivate-sesefus-jvo5kd` via
  cherry-pick 9ad68a1): `tools/guard_vaults.sh` detects vault data by filename
  (`*.db`/`*.sqlite*`/`*vault*`) and by content (SESEPHUS magic header, catching
  renamed vaults) with `--staged`/`--tree`/`--history` modes; `.githooks/pre-commit`
  + `tools/install_guards.sh` wire it as a pre-commit gate, auto-enabled in the
  devcontainer (`post-create.sh`). Documented in `tools/VAULT_GUARD.md`.
- **Voice control loop** (PR #30): `tools/voice.py` + `voice.bat` — push-to-talk
  speak-to-journal; utterances of ≤ 5 words are commands (status / review last /
  score / dashboard / goodbye), longer is journal. Python+sounddevice capture,
  local Whisper transcription, manifests written with transcript + segments +
  duration, scored in-process via ETDI. `--say`/`--file` test hooks cover
  everything downstream of capture; the mic path (`record_ptt`) is verified on
  real Windows hardware only.
- **Image sieve** (PR #30): `shredder/image_sieve.py` — Windows screenshots →
  abstract-notion chunks into the existing debris/vector pipeline, with
  incremental checkpointing; documented in `docs/IMAGE_SIEVE.md`.
- **Per-user config** (PR #30): `sesefus.config.json` + `tools/sesefus_config.py`
  replace hardcoded personal paths; ETDI DB honors an `etdi_db` config override
  ahead of the drive-mapping default.
- Tester packaging (PR #30): `install.bat`, `voice.bat`, `README-TESTERS.md`.
- Docs (PR #30): `docs/DRIFT.md` (the app thesis — control over all forms of
  drift; v2 drift layer speccing EMA baseline + MAD sigma + personal tau),
  `docs/INVENTORY.md` (repo-wide file inventory cheat sheet),
  `docs/session-notes/2026-07-04.md` (session ledger: decisions, open loops,
  0.9.3 gap, pitch kit).

### Changed
- ETDI formula (PR #30): the product form (|v|·a·s) replaced by the Euclidean
  norm `sqrt(v²+a²+s²)/(sqrt(3)·minutes)`; high-density flag threshold
  recalibrated 0.15 → 0.30 to match. Unknown-duration entries are reported
  UNSCORED instead of being inflated by the old 3-second duration floor.
- Zig client/host capture path removed from the alpha's critical path (still
  present, still the architecture — just not gating testers).

### Removed
- `docs/changelog/0-9-N/` folder scheme (empty placeholders, retired) and the
  version-ladder planning it implied. The legacy `docs/gemini.md` v1.x–v3.x release
  matrix is likewise no longer the source of truth; this file is.
- Hardcoded personal paths (`C:\Users\...`, `T:\...`) in `ingress_memos.py` and
  `image_sieve.py`, in favor of `sesefus.config.json` with home-relative
  fallbacks (PR #30).

### Notes
- Flag threshold 0.30 is calibrated to the norm formula; if the formula changes
  again, recalibrate (see `docs/DRIFT.md` v2: personal baselines replace fixed
  thresholds entirely). `voice.py` intent grammar: tune `COMMAND_MAX_WORDS` if
  testers trip over the 5-word command cutoff. `wav-*` smoke-test rows in
  `etdi.db` double-count against `aje-*` rows if the same memo is scored both
  ways; prefer `--into-manifest` for real memos.

## 2026-07-05 — SSFS path unification (PR #28)

### Fixed
- `tools/archive_schema.py` and `tools/etdi_store.py` hardcoded `T:\Archive\sesefhus`,
  disagreeing with `drive-mapping.json`'s coldArchive (E:). Both now derive the path
  from a new shared reader, `tools/ssfs_config.py`; the same stale `T:` literal in
  `runtime_config.zig`'s `primaryConfigDir` was corrected (92df8d5).
- coldArchive expected volume label corrected to match the actual drive (637b90d).

### Added
- `python tools/ssfs_config.py` runs standalone and prints the resolved archive path
  and whether it exists — config tracing without reading code (f23f403).

### Notes
- `ingress_memos.py`'s separate `T:\sesephus-database\aurgio\transcript` root was
  deliberately left untouched — different subpath, needs manual confirmation.

## 2026-07-03..04 — SSFS drive discipline + ETDI v1 (PRs #25, #26)

### Added
- **SSFS config-driven storage layer** (PR #26): `ssfs/drive-mapping.json` is the
  single source of truth for drive letters (V: vault required, E: cold archive,
  T: future worktrees); `ssfs/storage/config-engine.js` verifies drives fail-loud
  (exit 1) with volume-label checks via PowerShell `Get-Volume`, writing a receipt to
  `V:\ssfs-vault\state\ssfs-verified.json`; `ssfs/storage/paths.js` derives all vault
  paths at call time (`getVaultPath`, `getAudioJournalPath`, `getMainVaultDbPath`).
  `drive-mapping.json` is immutable at runtime (no `lastVerified` rewrites dirtying git).
- Data-loss rules documented in `docs/PRODUCTION.md` §5 and `docs/vault_security.md`:
  never hard-code drive letters, live checkouts only at `C:\dev\sesefus`, E: is
  read-only history, re-verify + confirm 2+ copies before destructive disk ops.
- **ETDI v1 pipeline** (PR #25): `tools/etdi_pipeline.py` + `etdi_inference.py` +
  `etdi_store.py` turn a voice memo into an Emotional Time Density Index
  (|valence| × arousal × salience / minutes) via Whisper transcription and
  locked-prompt/strict-JSON inference against Ollama (default), xAI Grok
  (`--backend grok`), or an offline lexical fallback for smoke tests.
- ETDI surfacing: scores upsert into an `etdi_scores` table (`etdi.db`,
  `SESEFUS_ETDI_DB` override) and into an `etdi` block in each aurgio manifest;
  `dashboard_server.py` gains `/api/etdi/{trend,flags,entries}`; React UI gains an
  ETDI page (`EtdiPanel.jsx`) with daily trend bars and high-density flags.

### Changed
- Zig host startup: an SSFS drive-preflight guard was wired into `runHost` and then
  deliberately unwired the same day (5a20b5d, "per preference") — net result is a
  comment pointing at the manual command `node ssfs/storage/config-engine.js`.

### Notes
- Verifier autostart stays fully functional as a manual command; can be re-wired
  later behind a flag. ETDI v2 scope explicitly deferred in `docs/ETDI.md`: local
  SER (SenseVoice/emotion2vec) audio+text fusion, raw audio features beside the
  JSON, self-validation on high-ETDI moments.

## 2026-07-02 — Docked: Dev Container for WSL + Docker Desktop (PR #24)

### Added
- `.devcontainer/`: Ubuntu 24.04 image with Zig 0.16.0, Node 20, Python 3, and a
  minimal Rust toolchain; compose-based with a `:cached` bind mount and named volumes
  for `.zig-cache`, `node_modules`, and `.venv` so caches survive rebuilds and dodge
  slow `/mnt/c` I/O.
- Lifecycle scripts: `wsl-precheck.sh` (host-side Docker reachability),
  `post-create.sh` (venv + pip, `npm ci`, `zig build`, best-effort cargo build),
  `post-start.sh` (Windows-mount warning, WSLg PulseAudio passthrough for
  audio-input experiments).
- `requirements-dev.txt` layering fastapi/uvicorn on `requirements.txt`
  (openai-whisper optional/manual). Optional NATS 2.10 service gated behind a
  compose "full-stack" profile. `.vscode/extensions.json` recommendations.

### Changed
- `dashboard/ui/vite.config.ts`: dev server binds all hosts, no auto-open browser,
  proxies `/api` to the FastAPI sidecar at `127.0.0.1:3001` so the UI works from
  inside the container.

### Fixed
- WSL docker precheck falls back to Docker Desktop's Windows binary and verifies the
  daemon actually responds (`docker version`), instead of only checking a CLI exists
  (fe4698c).

### Notes
- Documented dev flow is three processes: Zig host (port 3000), FastAPI sidecar
  (port 3001), Vite UI (port 5173). NATS deliberately optional — main flow polls the
  Zig host over HTTP. Commit 323f990 "Update build.zig" is an empty commit; no
  build.zig change actually landed.

## 2026-06-15..24 — Consolidation: SaturnNav Route Lab, router migration, scripted maintenance

### Added
- SaturnNav Route Lab UI: `dashboard/ui/src/shipments/saturnnav/` (SaturnNavLab,
  RouteMap, PreflightPanel, OptimizationStack, ParetoTray, BasinEditor,
  RiderProfileSelector, SessionPhaseBar, VoiceSpeakerPanel) plus mock data in
  `src/data/` and `utils/weights.js` (2bdc387).
- New route components `dashboard/ui/src/routes/{ShipmentDock,ShipmentConsole,ShipmentManifest,SystemOverview}.jsx`,
  and a second copy of the shipments data at `docs/shipments.json`.
- `docs/sesephus-circadian-prosthetic.md` — the "Sisyphus, Flipped" essay on
  circadian entrainment, audio journaling, and AI as cognitive prosthetic.
- `tools/sesefus_maintenance.ps1` with three modes: StrictMain (layered orphan-branch
  rebuild), ToolflowClean (cherry-pick verified commits onto base, conflicts
  auto-resolved `--theirs`), FullPipeline (clean + force-publish to GitHub main)
  (8e81ea3).
- `docs/changelog/` versioning skeleton: `0-9-2/` and `0-9-3/` placeholder folders
  (0646816) — never filled; retired by this changelog.

### Changed
- Dashboard `App.jsx` migrated from a useState module switcher to react-router-dom v7
  with shipment-based routes (`/`, `/system`, `/shipments/:id`, `/shipments/:id/manifest`,
  `/shipments/saturnnav/lab`); Sidebar rewired to links; `index.css` grew ~600 lines
  of unified styling (2bdc387).
- `docs/gemini.md` redefined SaturnNav from a bike-first routing engine to a
  low-stimulus nav speaker layer (sparse phrasing, stimulus budget, rider profiles)
  with a preflight-bundle model — in-ride edits are lightweight patches within the
  preflight corridor, no live cellular reroute.

### Fixed
- `core/sesephus/src/host.zig` had compile errors: an undeclared identifier in the
  vault command dispatcher (`cmd` → `sub`) and a duplicate `lead` import (7d4ac68).

### Notes
- `sesefus_maintenance.ps1` dot-sources `tools/git_repo_maintenance.ps1`, which is
  not tracked — the script won't run from a fresh clone. `components/SaturnNav.jsx`
  is unreferenced after the Route Lab replaced it (deletion candidate); the other
  legacy components are still imported by the new routes. ToolflowClean/FullPipeline
  make history rewriting an intentional, scripted workflow.

## 2026-06-12..13 — LeadLogic runtime: unified binary, dual-archive ingress, branch triage

### Added
- LeadLogic strict-database-host scaffold (first landed via PR #15, re-landed via
  PR #19): vendored canonical prompts under `prompts/` (qualify-post, jetstream-sort,
  jetstream-profile-align, meta/INDEX, meta/vllm-porting-notes); `lead qualify` in
  `commands/lead.zig` resolves `prompts/qualify-post.md` from the repo root; host
  routes the `lead` subcommand to the module.
- `lead qualify` wired to the local vLLM peer (d0d747a): new `tools/qualify_post.py`
  extracts the system block from qualify-post.md and POSTs to `LOCAL_LLM_URL`
  (default localhost:8000); optional `--handle` adds Bluesky profile context.
- LAN discovery and persisted role config (PR #15): `core/sesephus/src/main.zig`
  dispatches host vs client from a `runtime.json` persisted under
  `T:\Archive\sesefhus\config\` (first run prompts and self-restarts with `--role`);
  `discovery.zig` scans the LAN on port 5000 to auto-find the host.
- Dual-archive ingress stack (PR #15): `tools/archive_schema.py` + `dual_writer.py` +
  `ingress_memos.py` write memos into `archive.db` + `dimensional.db` under
  `T:/Archive/sesefhus/db`; new `vault ingest-archive [--dry-run] [--limit N]`;
  `JournalEntry` gained archive-linkage fields (archive_seq, ingest_source, sha256,
  transcript_status, archive_raw_path, schema_version). Also `tools/strict_main.ps1`.
- zig-cli operator tooling imported via path-filtered cherry-pick (5a85517):
  `docs/GIT_WORKFLOW.md` (three-layer S:/F:/V: staging model), `tools/recreate_repo.ps1`,
  `remap_history.ps1`, `gh.ps1`, `test_structured_export.py`.
- `ARCHIVED-BRANCHES.md` branch-triage record (direct commit + PR #20): merged-behind
  branches recorded as archived (tags referenced there live GitHub-side, not in this
  clone); only `main` + the designated base staging branch remain visible.

### Changed
- Build consolidated to a single `sesefus` executable: `build.zig` drops separate
  host/client artifacts in favor of `src/main.zig`; `ssfs.bat` launches
  `zig-out/bin/sesefus.exe`.

### Fixed
- Removed leftover merge-conflict markers from README.md on main (9a997bf).

### Notes
- `lead mine` / `lead feed` remain print-only stubs; vllm-porting-notes lists unwired
  pieces (symptom-library.json instant-hit bypass, skills-injection.md) with profile
  hydration as the recommended next step. vLLM endpoint/model env-overridable
  (`LOCAL_LLM_URL`, `LOCAL_LLM_MODEL`, `SALES_INTENT`).

## 2026-06-10..11 — Vault engine, guardrail CLI, Sesephus rebrand (PRs #6–#13)

### Added
- Encrypted vault management engine (`database.zig`, ~500 new lines) with host
  commands `vault_profile`, `vault_audit`, `vault_shuffle`, `vault_refactor`,
  `vault_distribute`, `vault_key_verify`, and `backup`; startup resolves the vault
  path with graceful fallback to `./sesephus_vault.db`, checks the SESEPHUS magic
  header, derives a public key for parity verification — specified in
  `docs/vault_security.md`.
- Restored Circadia features in host.zig + dashboard.html (lost in the 06-05
  regression): alarm subgroups over HTTP and CLI, bulk alarm edits, interval alarm
  sequences, plus interactive CLI testing commands.
- Modular CLI layer (PRs #12/#13): `cli.zig` parses `--production/--dry-run/--json/--expert`
  and gates destructive ops behind a y/N confirm; command modules under
  `core/sesephus/src/commands/` (journal, lead, rhythm, stoic, vault); `ssfs.bat`
  launcher; `docs/CLI.md` + `docs/PRODUCTION.md` guardrail/deployment checklist.
- CLI help system (`--vault <path>`, `--read-vault`, `--extract`) + `docs/sesephus_help.md`;
  machine-readable workspace manifest at `docs/manifest.json`.

### Changed
- README rewritten from the "Arcadium & Circadia (AuraEngine / Sesephus Suite)"
  architecture overview into a command-first "Sesephus CLI — Audio-First Growth
  Engine" guide; old architecture/mermaid content moved to `overallreadmee.md`.

### Notes
- The `commands/*.zig` modules are print-only stubs — real logic still lives in
  host.zig's dispatcher; the modular split is scaffolding awaiting real extraction
  (→ roadmap: module extraction). `scratch/` carries ~3,500 lines of one-off refactor
  scripts (cleanup candidates). PRODUCTION.md marks API rate limiting "Upcoming" and
  has an env-var typo (`SESAPHUS_PRODUCTION`).

## 2026-06-05 — Circadia expansion, Lighthouse Portal, repo restructure

### Added
- Circadia alarm engine expansion: subgroups, bulk alarm edits, interval alarm
  sequences, precision tuning — host.zig, embedded dashboard.html, `Circadia.jsx`,
  plus `test_circadia_advanced.py` and a core README documenting the TCP host/client
  architecture (e6048ac, 8b5f7af).
- Client telemetry and crash capture in `client.zig`: synchronous logging to
  client.log, fatal-exit wrapping, panic-handler override that writes to disk before
  stack tracing.
- Embedded local test client (PR #4 embed-client): host spawns an "embedded-01"
  client thread on interactive boot, loopback TCP port 5000 with connect-retry;
  `runClientProgrammatic` for in-process invocation.
- `docs/gemini.md` (2edef26, 4306a6a): persistent agent guide — Sesephus vision
  (Circadia, Arcadium, SaturnNav), pure-Zig-0.16/zero-runtime-deps constraint,
  hard-won agentic rules; includes the legacy v1.0.0–v3.3.0 release matrix
  (superseded by this changelog).
- 86-line root `.gitignore`; `aurgio/` voice-journal transcript shards (a5b373a).

### Changed
- Dashboard rebuilt on the "Lighthouse Portal" theme — glassmorphic dark cards,
  pulsing status badges, conic-gradient accents (f676a2a; net −523 lines in the
  embedded dashboard.html).
- Codebase migration (d294d79): original prototype snapshot moved wholesale into
  `archival/`; fresh top-level module homes (`core/alarm_engine.zig`, `tcp_server.zig`,
  `wav_db.zig`, `client/recorder.zig`, `tools/compress_archive.zig`); vault DB
  hardcoded to `V:\sesephus_vault.db` (V:-data / S:-workspace scheme — the debt the
  2026-07 SSFS work paid down); README.md rewritten as canonical.

### Removed
- Committed runtime artifacts untracked: client.log, host.log, dashboard.log, and
  the binary sesephus_vault.db removed from git alongside the new .gitignore (a5b373a).
- `build_client.ps1` (device-targeted cross-compile helper): added, arg-quoting
  fixed, then deleted the same day — "script bad" (ecae614).

### Notes
- **Regression:** the embed-client commit (7b5d787) rewrote host.zig from an older
  base (1423 → 801 lines), wiping the Circadia subgroup/bulk/interval endpoints added
  hours earlier; UI, README, and tests still expected them. Restored 06-10.
  gemini.md codifies avoiding version-string churn in Zig/HTML source to keep binary
  hashes stable (Windows Smart App Control).

## 2026-06-03..04 — Genesis (PRs #1, #3, #4)

### Added
- Full prototype import (~14k lines, PR #3 — branch literally named
  "Decision,-rust,-python,-or-zig"): Zig host/client daemons with
  ChaCha20-Poly1305-encrypted vault (`host.zig`, `client.zig`, `crypto.zig`,
  `database.zig`, `audio_record.zig` on Win32 winmm), Python FastAPI+Whisper sidecar
  (`dashboard_server.py`), React+Vite dashboard, a Rust dashboard experiment
  (`aether-dashboard-v2/`), audio/shredder/simulator/utils tooling, and ~3.9k lines
  of docs (vision.md, GUIDE_Vector_Engagement.md, longhorizonbackup.txt, prototype-tools/).
- Project README (READ-me, PR #4) describing the Arcadium & Circadia suite: Zig
  daemons, Python AI bridge on port 3001, Vite/React UI, build/run steps.

### Changed
- Language decision resolved (PRs #1/#3): the pure-Zig "AuraEngine" identity draft
  demoted via rename to `primordial-read` ("name signals segregation from baseline"),
  landing on a polyglot stack — Zig for low-level daemons, Python as the
  Whisper/FastAPI AI bridge, React for UI polling via dev proxy (no NATS broker,
  no CORS pain).

### Notes
- Debt taken knowingly: runtime logs and the binary vault DB were committed in the
  initial import (cleaned 06-05). The Rust dashboard was a dead end (archived 06-05).
  SaturnNav existed only as a UI component — no engine code.
