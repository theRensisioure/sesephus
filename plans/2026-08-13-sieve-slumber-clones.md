# Plan — Sieve slumber · four compact clones

**Date:** 2026-08-13  
**From:** `/make-plan` · `/stack` · `/stacked on` · goal: churn data into revelation via an integration that rivals human slumber; track compact clones before/after sieve and before/after latent reconstruction  
**Mode:** plan + probe (do not build a new sieve engine)  
**Lineage-role:** child  
**Parent:** `2026-08-10-dyslexic-builder-will-sieve`  
**Does not replace:** `2026-08-14-archive-flesh`

---

## Goal (one sentence)

Prove, on **copies**, what the existing sieves actually do to a small dataset — then keep four **compact clones** (fingerprints, not second 5 GB trees) so we can see the before and after of shred, and the before and after of latent reconstruction.

## What this is not

- Not a new sieve product this week
- Not embeddings-as-will (parked)
- Not cloning `shredder/sieve.py` into will-sieve
- Not LeadLogic dual-source-sieve (other product, same word)
- Not moving or deleting `V:\` originals
- Not the live `V:\ssfs-vault` as sieve food (tiny journal tests; user said vault probably not)

## Human meaning

Sleep does not keep every second. It keeps what stuck. The sieve problem is the same: churn a pile until a few cues remain that still matter after a night.

To know if that happened, we need **four small photographs** of the pile:

1. **C0** — before shred  
2. **C1** — after shred  
3. **C2** — before latent reconstruction  
4. **C3** — after latent reconstruction  

A photograph is a compact clone: hashes, counts, top names, skip reasons. Not another full zip.

---

## Phase 0 — Documentation discovery (done this turn)

### Historical variants (sesefus)

- **Text sieve** `C:\dev\sesefus\shredder\sieve.py` — walks a tree, splits paragraphs/blocks, **skips `.zip`**, overwrites `ingest/debris_shards.jsonl`
- **Archival text sieve** `C:\dev\sesefus\archival\shredder\sieve.py` — old hardcoded `/mnt/c/.../arcadium-circadia`; no zip skip; not the live door
- **Image sieve** `C:\dev\sesefus\shredder\image_sieve.py` — screenshots only; appends; hash state
- **Artifact sieve** `C:\dev\sesefus\shredder\artifact_sieve.py` — **only one that opens zips**; members must look like chat/takeout; files > 64 MB inventoried not deep-parsed
- **Dashboard Sieve.jsx** — UI for artifact sieve only
- **Archival Sieve.jsx** — stub, no handlers
- **Forge** `C:\dev\sesefus\utils\forge.py` — Ollama `nomic-embed-text` → `ingest/vector_shards.jsonl` (may be down)
- **ingress_memos.py** — audio DualWriter. Not a sieve

`C:\dev\sesefus\ingest\` did not exist at probe time.

### Cousins (do not collapse)

- **Rolling sieve / latent cue** — `plans/2026-08-10-dyslexic-builder-will-sieve.md` Phase 4 · stick > one turn · **not built**
- **Day reconstruct** — re-read `day.md` from disk · live · not a chat mind
- **Session intent** — 3-Q packet · live
- **/ta** — ranks open loops in a thread · does not write will
- **will-v0** — naissance · membered · **not on this disk**
- **LeadLogic dual-source-sieve** — firehose triage · other product

### Tonight’s science (already on disk)

Copy-only ingress: `C:\Users\bardw\jwrangle\you\sieve-ingress\`

- `from-ssfs-vault/` — 3 tiny files (not sieve food)
- `sandbox/` — 6 MB tar + notes
- `copies/sesefhus.zip` — **5.34 GB copy** of `V:\Archive\sesefhus.zip` (original stayed)
- `out/sandbox-debris.jsonl` — text sieve shipped **22 chunks** from notes
- Artifact sieve `--scan-only` on the ingress root: **0 files** (zip name `sesefhus.zip` fails `classify_path` chat/takeout markers)

That zero is the first revelation: the live artifact sieve cannot see this archival zip.

### Allowed APIs (copy these; do not invent)

- `Sieve(root).scan()` / `.ship(path)` — `shredder/sieve.py`
- `python shredder/sieve.py --root PATH --output PATH --source-node NAME`
- `python shredder/artifact_sieve.py --scan-only --root PATH`
- `python shredder/artifact_sieve.py --root PATH --dry-run --unit conversation|turn`
- `_parse_zip` only via artifact sieve; member names must contain gemini/bard/conversation/activity/chat/applet
- `scan_directory(roots)` return dict: file_count, conversation_count, files[]
- Reconstruct: `python ~/.grok/skills/reconstruct/scripts/reconstruct.py` (day board, not shards)
- `/ta` method: extract → cluster → score 1–5 (chat only)
- Forge only if Ollama `:11434` is up — **probe first**, do not require

### Anti-patterns

- Do not invent `/api/sieve/clone`
- Do not write a second DebrisChunk class
- Do not point shred at `V:\` originals
- Do not treat LeadLogic gates as will
- Do not start `shredder/` rewrite as Phase 4 rolling sieve
- Do not ship 5.3 GB into embeddings
- Do not overwrite `ingest/debris_shards.jsonl` on the sesefus tree — always `--output` under `you/sieve-ingress/out/`

---

## Phase 1 — Compact clone schema (C0–C3)

**What:** one JSON shape for a photograph of a dataset.

Copy field spirit from artifact scan entries (`path`, `size_bytes`, `conversation_count`) plus hashes. New file only under ingress.

**Create:** `C:\Users\bardw\jwrangle\you\sieve-ingress\clones\SCHEMA.md`  
**Create:** `C:\Users\bardw\jwrangle\you\sieve-ingress\clones\C0.json` (first)

Each clone:

- `id` — `C0` | `C1` | `C2` | `C3`
- `when` — local ISO
- `stage` — `before-sieve` | `after-sieve` | `before-latent` | `after-latent`
- `sources[]` — `{path, sha256, bytes}` for files **already copied** (not V:)
- `counts` — files, skipped, chunks, conversations, messages
- `skip_reasons[]` — why the live sieve ignored things (e.g. classify_path, SKIP_BINARY_EXTS, >64MB)
- `top_names[]` — ≤20 human names
- `revelation` — one sentence or empty

**Verify:** C0 exists; sha256 of `copies/sesefhus.zip` matches `5340945733` bytes; originals on V: still present.

**Guard:** do not copy the zip a second time.

---

## Phase 2 — Make artifact sieve *see* a sandbox (or name why not)

**What:** either feed it a file it classifies, or record the miss as science.

Allowed: rename is **not** required. Prefer `--root` pointed at a **member extract** of a few chat-shaped files from the zip, still copies, into `you/sieve-ingress/sandbox/chat-sample/`.

If the zip has no chat-shaped members (likely — it is a sesefus tree), write that as C1 skip_reason and stop. Do not invent Takeout JSON.

**Verify:** `artifact_sieve.py --scan-only --root sandbox/chat-sample` prints file_count > 0 **or** a written miss in `out/SCAN.json`.

**Guard:** do not extract the whole 5.3 GB tree.

---

## Phase 3 — C1 after text shred (already half-done)

**What:** keep the 22-chunk `out/sandbox-debris.jsonl` as C1 for the **notes** slice.

Add counts + sample first lines into `clones/C1.json`.

Do not run text sieve on the zip (it skips `.zip`).

**Verify:** C1.counts.chunks == 22 for the notes slice; zip listed under skip_reasons.

---

## Phase 4 — Latent reconstruction probe (C2 → C3)

Two legal latent doors. Pick **one** per run. Do not merge.

**Door A — day reconstruct (live, no embeddings)**  
C2 = compact of C1 + today’s `day.md` / `q-meet-will-sieve.md`.  
C3 = `reconstruct.py --day Thu2613th` output names (what stuck on the board).

**Door B — forge vectors (only if Ollama answers)**  
`curl http://127.0.0.1:11434/api/embed` probe. If down, write C3 as `latent=unavailable` and stop.  
If up: forge **only** `out/sandbox-debris.jsonl` (22 chunks) to `out/sandbox-vectors.jsonl`. Never the zip.

**Verify:** C2 and C3 files exist; C3 says which door; no new ontology.

**Guard:** do not activate will-v0. It is not on this disk.

---

## Phase 5 — Slumber pass (integration, not more shred)

**What:** leave C0–C3 overnight. Next `/jwrangle` or `/ta` on this thread asks: which cues still matter?

Write `you/sieve-ingress/REVELATION.md` — max 7 cues that survived > one turn. That **is** the rolling-sieve shape, on paper, without an engine.

**Verify:** file exists; each cue traces to a clone id + a human name.

**Guard:** do not promote REVELATION into a fourth day queue.

---

## Phase 6 — Verification

- V: originals untouched (`sesefhus.zip` still at `V:\Archive\`)
- Ingress is copies + clones + out only
- No new API in `dashboard_server.py`
- No write to `C:\dev\sesefus\ingest\` unless you later choose it
- will-sieve sequence still: archive usable → then real rolling sieve
- This plan does not replace `2026-08-10-dyslexic-builder-will-sieve.md`

---

## Files this plan may touch

- `C:\Users\bardw\jwrangle\you\sieve-ingress\**` (requested science)
- `C:\Users\bardw\jwrangle\days\Thu2613th\q-meet-will-sieve.md` (pointer only)
- This file

Do not touch `shredder/*.py` until Phase 2 proves a **named** miss that a one-line classify allowlist would fix — and only then as a later plan.

---

## Stacked

`/stacked on` for this payload: day sink, not Android horizon.

- State: `C:\Users\bardw\jwrangle\days\Thu2613th\stacked.json`
- Cards: `C:\Users\bardw\jwrangle\days\Thu2613th\ensembles\`
- Horizon `dev\horizon\stacked.json` stays the month-ship pair

---

## E1 cycle1 harden (backburner — 2026-08-13)

Shape wave agreed. Parent keeps this spine.

- Photographs record a **transform that happened**. Four JSONs of a zip nobody opened are not slumber.
- C1 is **two stories**: 22 note chunks, and a zip the artifact sieve never saw. Name which sieve per skip.
- Size `5340945733` is not a hash. Store both. Use `artifact_sieve.file_sha256` if hashing; do not recopy.
- Do **not** extract 5.3 GB. Bounded `ZipFile.infolist()` answers classify. Do not mkdir `sandbox/chat-sample/` just to pass `classify_path`.
- Door B (forge) is **illegal as written**: `forge.py` hardcodes `ingest/debris_shards.jsonl`. No `--input`. Probe Ollama only; if you need vectors later, a later plan — do not birth `C:\dev\sesefus\ingest\`.
- Door A C3 cannot be `after-latent` if it only restates today’s board. Call that `latent=board-echo` and stop.
- REVELATION.md is not a day queue.
- Archive flesh still waits. This plan does not replace `2026-08-10-dyslexic-builder-will-sieve.md`.

Cards: `days/Thu2613th/ensembles/E1-shape/cycle1/`

---

## Open questions (do not block Phase 1)

- Does `sesefhus.zip` contain any chat-shaped members? Unknown until a **bounded** zip listing.
- Is Ollama up? Probe at Phase 4, not now.
- User swapping V: — C: copy is the working set after unplug.
