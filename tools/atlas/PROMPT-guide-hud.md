# PROMPT: Atlas guide HUD

## Intent

`tools/atlas/build.py` now emits a deterministic `guide` string in `#atlas-data` (token-free "start here" prose from top-dir counts). The atlas HTML ignores it. Surface `DATA.guide` in the status HUD so operators and agents see install-specific orientation without opening the JSON or running inference.

**Prerequisite:** `renderer` branch commit with `build.py` + install hook (atlas dynamic manifest).

## Base

- Branch from: `renderer` (after atlas builder commit merges or is current tip).
- Do not merge `MachineState.jsx`, fleet runner, or dashboard wiring — atlas only.

## Scope

**In scope**

- `tools/atlas/sesefus-atlas.html` — read `DATA.guide` and `DATA.built`; display in existing `#status` HUD (or collapsible panel if guide exceeds one line).
- Optional: `tools/atlas/build.py` — only if guide format needs a tweak for HUD display (keep deterministic; no LLM).

**Out of scope**

- `sesefus-dev-tree.csv` (deleted; never restore).
- Dashboard `MachineState.jsx`, `/api/machine`, fleet runner.
- AI-generated prose; `guide` stays template output from `build.py`.
- New dependencies or build steps beyond existing `install.bat` `[5/5]`.

## Tasks

1. Checkout `feat/atlas-guide-hud` (or create from `renderer` if missing).
2. Open `tools/atlas/sesefus-atlas.html`; locate `setStatus()` (~line 597).
3. If `DATA.guide` exists, render first line in `#status` alongside repo/view counts; show full guide on click or `?` help panel.
4. If `DATA.built` exists, show as dim timestamp (e.g. `built 2026-07-09`).
5. Graceful fallback when `guide`/`built` absent (older snapshots).
6. Run `python tools/atlas/build.py`; open HTML in browser — verify HUD shows guide without console errors.
7. Single commit; no other files.

## Acceptance

- [ ] `#status` shows repo name, view label, file/commit counts (unchanged behavior).
- [ ] When `DATA.guide` present, at least the first line is visible without opening devtools.
- [ ] When `DATA.built` present, build timestamp visible in status or inspector.
- [ ] No LLM calls; no new network requests.
- [ ] `python tools/atlas/build.py` still succeeds; regenerated HTML retains HUD behavior.
- [ ] Diff touches only `tools/atlas/*` (max 2 files).

## Context pointers

- Atlas data loader: `const DATA = JSON.parse(document.getElementById('atlas-data').textContent);`
- Status renderer: `setStatus()` in `sesefus-atlas.html`.
- Guide builder: `build_guide()` in `tools/atlas/build.py`.
- Fork decision (closed): atlas = trunk renderer; prose = `guide` garnish from same manifest.

## Execute

```bash
git checkout feat/atlas-guide-hud
# Agent: read this file and implement Tasks 1–7.
```