# Sesephus lineage/reference inventory

**Repo:** `theRensisioure/sesephus` · **Branch:** `chore/reconcile-sesefus-lineage-20260828` · **Disposition:** 2026-08-28
**275 tracked files** — 212 in the reference tree, 63 in `archival/` (a frozen copy of the older layout).
The review branch commits the six-surface retirement and adds five boundary,
postmortem, and ideas documents. Older file descriptions below are retained as
lineage; historical capture commands are explicitly unsupported.

```bash
# Review the reconciliation branch
git clone https://github.com/theRensisioure/sesephus.git
cd sesephus
git switch chore/reconcile-sesefus-lineage-20260828
```

---

## How it all fits together

```
 you speak
    │
    ▼
 Zig client (core/sesephus/src/client.zig, audio_record.zig)
    │  WAV over TCP, length-prefixed frames
    ▼
 Zig host daemon (core/sesephus/src/host.zig, port 3000)
    │  ChaCha20-Poly1305 encrypt → sesephus_vault.db
    ▼
 Python AI bridge (dashboard/dashboard_server.py, port 3001)
    │  Whisper transcription · ETDI API
    ▼
 React dashboard (dashboard/ui, port 5173)      ← you look at this

 Historical Sesephus capture path (unsupported):
 tools/voice.py ★ → Whisper → manifest (aurgio/transcript/)
                  → tools/etdi_pipeline.py ★ → ETDI → etdi.db + dashboard

 Current Voice (external pointer only):
 C:\dev\journal-clippers\audio-journal-system
 mic → Whisper → tape → shred → cue projection

 Side path for memos-as-files:
 audio file → tools/ingress_memos.py → tools/dual_writer.py → archive.db + manifest
 manifest  → tools/etdi_pipeline.py ★ → emotion JSON → ETDI → etdi.db + dashboard

 Screenshot path:
 screenshot → shredder/image_sieve.py ★ → abstract-notion chunk → debris_shards.jsonl → forge
```

## Start here (the files you'll actually touch)

| File | Why it matters |
|---|---|
| `tools/voice.py` ★ | Historical 0.9.3 push-to-talk loop; retained unchanged and unsupported. |
| `README-TESTERS.md` ★ | Retired tester-path disposition and current external Voice pointer. |
| `tools/etdi_pipeline.py` ★ | Run this to score memos. `python tools/etdi_pipeline.py --scan` |
| `tools/sesefus_config.py` ★ | Per-user config loader (`sesefus.config.json`). Replaced the hardcoded paths. |
| `docs/DRIFT.md` ★ | The app thesis: six drift forms, one shared loop. Read this to remember *why*. |
| `core/sesephus/src/host.zig` | Retained Zig reference. Vault, TCP, command routing. |

---

## Root

| File | Lines | What it is |
|---|---|---|
| `README.md` | 156 | Main guide: `ssfs` CLI workflows (journal / rhythm / stoic / vault). |
| `overallreadmee.md` | 123 | Architecture readme: Zig daemons + Python bridge + React UI, FSM table. |
| `ARCHIVED-BRANCHES.md` | 52 | Record of old branches archived with `archive/*` tags on 2026-06-13. |
| `toclaude.md` | 18 | Session handoff notes to Claude (dashboard consolidation summary). |
| `primordial-read` | 180 | The original AuraEngine readme (project's first incarnation). |
| `README-TESTERS.md` ★ | — | Retired tester path; points to external Desktop Clippers. |
| `install.bat` ★ | 32 | Historical installer for the retained Python environment. |
| `voice.bat` ★ | 9 | Historical launcher for `tools/voice.py`; unsupported. |
| `ssfs.bat` | 10 | Builds the Zig core then dispatches your args to the daemon. |
| `requirements.txt` | 5 | Python deps: psutil, sounddevice, numpy. |
| `requirements-dev.txt` | 3 | Adds fastapi, uvicorn; whisper optional. |
| `sesefus.config.json` ★ | — | Per-user config (gitignored; `install.bat` creates it). Paths, backend, model choices. |
| `LICENSE` | 21 | MIT. |
| `.gitignore` | 89 | Ignores build output, venv, node_modules, DBs, config, recordings. |

**`.devcontainer/`** (6 files) — Dockerfile, devcontainer.json, docker-compose.yml, post-create/post-start/wsl-precheck scripts. VS Code container setup.
**`.vscode/extensions.json`** — recommended extensions.

---

## `core/` — the Zig engine

| File | Lines | What it is |
|---|---|---|
| `core/sesephus/src/host.zig` | 2,436 | Host daemon: vault ops, client coordination, HTTP status API (port 3000), command dispatch. |
| `core/sesephus/src/client.zig` | 401 | Edge client: connects over TCP, streams WAV uploads (Windows API). |
| `core/sesephus/src/database.zig` | 769 | Encrypted vault DB (ChaCha20-Poly1305 per record). |
| `core/sesephus/src/crypto.zig` | 72 | Key derivation (PBKDF2-HMAC-SHA256) + AEAD helpers. |
| `core/sesephus/src/audio_record.zig` | 193 | WinMM waveIn capture (sine-wave fallback for headless). |
| `core/sesephus/src/discovery.zig` | 108 | Finds the host on the LAN. |
| `core/sesephus/src/common.zig` | 106 | Shared protocol frames / time helpers (Win32). |
| `core/sesephus/src/runtime_config.zig` | 149 | Host-vs-client role config. |
| `core/sesephus/src/cli.zig` | 62 | CLI command enum (alarm, group, vault…). |
| `core/sesephus/src/main.zig` | 89 | Entry point; wires host/client/config/discovery. |
| `core/sesephus/src/dashboard.html` | 1,069 | Old built-in single-file dashboard served by the host. |
| `core/sesephus/src/commands/journal.zig` | 21 | `ssfs journal` — stub dispatcher. |
| `core/sesephus/src/commands/rhythm.zig` | 22 | `ssfs rhythm` — stub dispatcher. |
| `core/sesephus/src/commands/stoic.zig` | 22 | `ssfs stoic` — stub dispatcher. |
| `core/sesephus/src/commands/vault.zig` | 72 | `ssfs vault` — locates & shells out to ingress script. |
| `core/sesephus/src/commands/lead.zig` | 120 | `ssfs lead` — wires prompts/qualify-post.md + tools/qualify_post.py. |
| `core/sesephus/build.zig` | 22 | Zig build script. |
| `core/sesephus/run_demo.bat` | 61 | Builds and spawns host + client demo windows. |
| `core/sesephus/README.md` | 126 | Module-level readme. |
| `core/sesephus/test_integration.py` | 197 | Python integration test against the daemon. |
| `core/sesephus/test_circadia_advanced.py` | 227 | Alarm/scheduler tests. |
| `core/sesephus/test_structured_export.py` | 169 | Structured export tests. |
| `core/alarm_engine.zig` | 115 | Older standalone alarm engine (SQLite, polymorphic actions). |
| `core/tcp_server.zig` | 69 | Older minimal WAV-receiving TCP server. |
| `core/wav_db.zig` | 56 | Older SQLite wrapper for WAV metadata. |

**`client/recorder.zig`** (139) — standalone CLI recorder experiment (WinMM → WAV → host).

---

## `tools/` — memo ingestion + ETDI scoring

| File | Lines | What it is |
|---|---|---|
| `tools/voice.py` ★ | 299 | Historical 0.9.3 PTT loop; retained for lineage and unsupported as a recorder. |
| `tools/etdi_pipeline.py` ★ | 261 | **Main ETDI entry point.** Memo → Whisper → emotion JSON → score → vault + manifest. Backends: ollama / grok / heuristic. `--into-manifest` backfills old memos. |
| `tools/etdi_inference.py` ★ | 181 | Locked system prompt, strict JSON schema, Ollama/Grok HTTP calls, audio stats, ETDI formula (√(v²+a²+s²)/(√3·min)). |
| `tools/etdi_store.py` ★ | 160 | `etdi_scores` SQLite table + trend/flags/entries queries. Platform-aware db path. |
| `tools/sesefus_config.py` ★ | 56 | Config loader with home-relative fallbacks; de-personalizes the old hardcoded paths. |
| `tools/dual_writer.py` | 148 | Archive-first ingest: audio file → archive.db + dimensional.db + manifest. |
| `tools/ingress_memos.py` | 105 | Scans your memo folders (config-driven now) and feeds DualWriter. |
| `tools/archive_schema.py` | 65 | DDL for archive.db / dimensional.db under `T:\Archive\sesefhus`. |
| `tools/qualify_post.py` | 132 | Lead qualification via vLLM OpenAI API (LeadLogic). |
| `tools/compress_archive.zig` | 42 | Zips the project via PowerShell Compress-Archive. |
| `tools/sesefus_maintenance.ps1` | 158 | Repo maintenance driver (StrictMain / ToolflowClean / FullPipeline modes). |
| `tools/remap_history.ps1` | 121 | Rebuilds a clean linear git history (`toolflow-clean`). |
| `tools/strict_main.ps1` | 182 | Builds the minimal `strict-main` orphan branch in layers. |
| `tools/recreate_repo.ps1` | 52 | Publishes cleaned history to a fresh GitHub repo. |
| `tools/gh.ps1` | 2 | Wrapper so `gh` works before PATH refresh. |

---

## `dashboard/` — Python bridge + React UI

| File | Lines | What it is |
|---|---|---|
| `dashboard/dashboard_server.py` | 167 | FastAPI sidecar (port 3001): `/api/transcribe` (Whisper), `/api/dashboard`, **★ `/api/etdi/trend` + `/flags` + `/entries`** (sync def, threadpool). |
| `dashboard/dashboard-audio-in-backend` | 851 | Saved LLM chat transcript: Rust dashboard + NATS audio layer design (reference text, not code that runs). |
| `dashboard/aether-dashboard-v2/src/main.rs` | 133 | Rust dashboard experiment (+ Cargo.toml / Cargo.lock). |
| `dashboard/Dockerfile.audio`, `docker-compose.yml` | 7 / 29 | Container setup for the audio backend. |

### `dashboard/ui/` — Vite + React (port 5173)

| File | Lines | What it is |
|---|---|---|
| `src/App.jsx` | 37 | Router. Routes: `/`, `/system`, **★ `/etdi`**, `/shipments/*`. |
| `src/components/Sidebar.jsx` | 47 | Left nav (**★ ETDI link added**). |
| `src/components/EtdiPanel.jsx` ★ | 95 | ETDI page: daily trend bars (SVG) + high-density flag table. Relative `/api` (LAN-safe). |
| `src/components/Circadia.jsx` | 795 | Alarm/circadian UI (biggest component). |
| `src/components/Overview.jsx` | 83 | Overview cards. |
| `src/components/Arcadium.jsx` | 69 | Audio journaling panel. |
| `src/components/Sieve.jsx` / `SaturnNav.jsx` | 21 / 20 | Stubs for those modules. |
| `src/routes/ShipmentDock.jsx` | 92 | Home page ("shipments" = feature modules). |
| `src/routes/ShipmentManifest.jsx` | 105 | Per-module detail view. |
| `src/routes/ShipmentConsole.jsx` | 51 | Per-module console view. |
| `src/routes/SystemOverview.jsx` | 4 | Wrapper for Overview. |
| `src/shipments/saturnnav/` (9 files) | ~710 | SaturnNav lab: RouteMap, BasinEditor, ParetoTray, PreflightPanel, OptimizationStack, RiderProfileSelector, SessionPhaseBar, VoiceSpeakerPanel, SaturnNavLab. |
| `src/data/` (4 files) | ~254 | shipments.json (module registry), mockRoutes, riderProfiles, routeSession. |
| `src/utils/weights.js` | 38 | SaturnNav scoring weights. |
| `src/index.css` | 896 | All styling (vanilla CSS, glassmorphism dark mode). |
| `src/App.css`, `src/main.jsx`, `index.html` | 184 / 10 / 13 | Boilerplate. |
| `vite.config.js` / `vite.config.ts` | 15 / 21 | **Both exist** — js proxies `/api` → 3001; duplicate worth cleaning up someday. |
| `package.json` / `package-lock.json` | 28 / 2,512 | React 19, react-router, Vite. |
| `public/`, `src/assets/`, `eslint.config.js`, `.gitignore`, `README.md` | — | Icons, logo art, lint config. |

---

## `aurgio/` — your voice memos

| File | Lines | What it is |
|---|---|---|
| `aurgio/transcript/aje-*.json` (6 files) | 55 each | Historical memo manifests (`heydhd.audio-journal-entry.v0`); not the current Clippers tape. |
| `aurgio/recordings/` ★ | — | Historical `voice.py` output location (gitignored). |
| `aurgio/readme-sort-n-ingest.md` | 1 | One-line note about checking ingestion compatibility. |

---

## `audio/`, `shredder/`, `simulator/`, `utils/`, `scratch/`

| File | Lines | What it is |
|---|---|---|
| `audio/audio_input_layer.py` | 90 | Mic capture → NATS publisher (sounddevice). |
| `audio/analyze_noise.py` | 71 | PCA noise analysis of captures. |
| `audio/monitor.py` | 79 | System/process monitor (psutil). |
| `shredder/sieve.py` | 120 | Text shredding/redaction into hashed chunks (the original sieve). |
| `shredder/image_sieve.py` ★ | 303 | Screenshot sieve: vision model → abstract-notion chunk → same debris_shards.jsonl. Deduped by image sha256, incremental checkpoint. |
| `simulator/agent_simulator.py` | 52 | Fake agent publishing NATS status updates. |
| `simulator/mock_nats_data.py` | 34 | Mock NATS payload generator. |
| `simulator/test_autogen.py` | 38 | AutoGen agents against local LM Studio. |
| `simulator/test_autogen_v4.py` | 37 | Same, AutoGen v4 API. |
| `utils/forge.py` | 111 | LLM-over-HTTP helper (urllib-based). |
| `utils/prune_chat.py` | 75 | Prunes chat logs. |
| `utils/spiffy_prune.py` | 99 | PCA-based latent noise filter for chats. |
| `utils/tapestry.py` | 78 | PCA embedding visualizer/summarizer. |
| `utils/badinit` | 68 | Old PowerShell init script (Docker GPU checks); "bad" per its name. |
| `scratch/*.py` (9 files) | ~3,500 | One-shot scripts that patched `host.zig` on the T: drive during a past refactor. Historical — safe to ignore. |

---

## `docs/` — reference & history

| File | Lines | What it is |
|---|---|---|
| `docs/DRIFT.md` ★ | 97 | **The app thesis.** Six drift forms, one shared loop, the drift math, design stance. |
| `docs/ETDI.md` ★ | 72 | ETDI metric, pipeline, usage commands, env vars. |
| `docs/IMAGE_SIEVE.md` ★ | 74 | How the screenshot sieve works, backends, usage. |
| `docs/INVENTORY.md` ★ | this file | The cheat sheet you're reading. |
| `docs/session-notes/2026-07-04.md` ★ | 52 | Session ledger: decisions, open loops, pitch kit, traps. |
| `docs/CLI.md` | 84 | Full `ssfs` command reference. |
| `docs/PRODUCTION.md` | 35 | Deployment checklist + `--production` guardrails. |
| `docs/GIT_WORKFLOW.md` | 152 | How commits/branches should flow (multi-drive workflow). |
| `docs/vault_security.md` | 210 | Vault encryption/sync/fallback spec. |
| `docs/sesephus_help.md` | 142 | Help-system text for the suite. |
| `docs/sesephus-circadian-prosthetic.md` | 115 | Essay: "Sisyphus, Flipped" — the why of the project. |
| `docs/vision.md` | 73 | Sovereign personal AI vision doc. |
| `docs/gemini.md` | 234 | Guide for Gemini agents + version matrix. |
| `docs/GUIDE_Vector_Engagement.md` | 78 | How to query the 768-dim vector shards. |
| `docs/manifest.json` | 46 | Machine-readable module map of the workspace. |
| `docs/shipments.json` | 61 | Copy of the dashboard module registry. |
| `docs/gemini_cli_log.txt` | 1,316 | Raw Gemini CLI session log (history). |
| `docs/longhorizonbackup.txt` | 1,257 | Saved LLM conversation backup (4-layer compression model). |
| `docs/prototype-tools/26 - 2026-05-31 12.50.md` | 800 | LM Studio chat export (prototyping session). |
| `docs/prototype-tools/SYSTEM PROMPT` | 172 | Founder system prompt used for prototyping. |
| `docs/prototype-tools/agentic-ingestion` | 172 | Same prompt, ingestion variant. |
| `docs/changelog/0-9-2/*` (3 files) | 0–1 | Empty 0.9.2 changelog stubs. |
| `docs/changelog/0-9-3/*` ★ (3 files) | filled | 0.9.3-alpha adds / culls / notes-to-maintain. |

---

## `prompts/` — LLM prompts used by the engine

| File | Lines | What it is |
|---|---|---|
| `prompts/qualify-post.md` | 69 | Systems Peer post-qualification prompt (used by `ssfs lead`). |
| `prompts/jetstream-sort.md` | 44 | Post sorting via Crow-9B on vLLM. |
| `prompts/jetstream-profile-align.md` | 81 | Profile alignment rollup prompt. |
| `prompts/meta/INDEX.md` | 79 | Context-loading index (load only what the task needs). |
| `prompts/meta/vllm-porting-notes.md` | 39 | Gemini → Crow-9B/vLLM migration notes. |

---

## `archival/` — frozen snapshot (64 files, don't edit)

A complete copy of the pre-consolidation tree, kept for reference. It mirrors the live layout almost 1:1, at older versions:

- `archival/core/sesephus/` — older Zig core (host.zig at 32K vs live 96K; no `cli.zig`, no `commands/`, no `discovery.zig`)
- `archival/dashboard/` + `archival/dashboard/ui/` — older FastAPI server and React UI (smaller Circadia, no shipments/saturnnav, no data/)
- `archival/audio/`, `archival/simulator/`, `archival/utils/`, `archival/shredder/` — same scripts as live, older
- `archival/docs/` — older copies of vision.md, gemini_cli_log.txt, longhorizonbackup.txt, prototype-tools
- `archival/READ-me`, `archival/primordial-read`, `archival/toclaude.md`, `archival/LICENSE`, `archival/requirements.txt`

Rule of thumb: **if a path exists both live and under `archival/`, the live one is the truth.**

---

## Quick commands

```bash
# Backfill the six waiting memos (read source.sourcePath from each aje-*.json)  ★
python tools/etdi_pipeline.py --wav "<path>" --into-manifest aurgio/transcript/aje-xxx.json

# ETDI scoring  ★
python tools/etdi_pipeline.py --scan                      # all manifests, Ollama
python tools/etdi_pipeline.py --scan --backend heuristic  # no model needed (smoke test)

# Screenshot sieve  ★
python shredder/image_sieve.py --backend stub             # smoke test, no model
python shredder/image_sieve.py                            # Ollama vision

# Dashboard: Python sidecar (:3001) + React UI (:5173)
python dashboard/dashboard_server.py
cd dashboard/ui && npm install && npm run dev

# Retained Zig reference build (Windows)
ssfs.bat status
```

Current Voice is Desktop Clippers at
`C:\dev\journal-clippers\audio-journal-system`. This inventory records
the pointer only and provides no launcher for that external tree.
