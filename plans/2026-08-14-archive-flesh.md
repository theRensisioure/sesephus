# Plan — Archive flesh (keep using the store)

**Date:** 2026-08-14  
**From:** `/make-plan keep fleshing the archive`  
**Mode:** plan only (do not implement in the planning chat)  
**Lineage-role:** child  
**Parent:** `2026-08-10-dyslexic-builder-will-sieve` Phase 2  
**Does not replace:** `2026-08-10-card-ui-platform-archive-safety`  
**Not:** `artifact-scanner/plans/2026-08-10-card-ui-platform-archive-safety.md` (foundation kinematics — cousin)

---

## Goal (one sentence)

Make **durable-archive** a store you actually use: journal captures can land, every land is listable by meaning, pending captures are visible — without a second vault and without starting the sieve.

## What this is

Will-sieve archive flesh. Cold residue later cues can eat. Audio journal is the proving course.

## What this is not

- Chat-governance `~/jwrangle/chat-governance/archives/` (scanner **Archive job** / **Open archival browser**)
- Foundation archive-kinematics (non-destructive + lists after restart)
- Rolling sieve / shredder clone / Takeout classify
- Encryption, backup (horizon), transcription pipeline
- A durable-archive tab on `board.html` (API exists; UI would merge cousins)
- Dual vault / `vault ingest-archive` as this archive

## Human meaning

You record. You land. You can find what landed by name. That is archive. If review cannot see the cue pack we already landed, the store is not flesh yet.

---

## Phase 0 — Documentation discovery (done this turn)

### Two stores (keep split)

- **Durable land (this plan):** `C:\Users\bardw\jwrangle\durable-archive\lands\<stamp>\`  
  `MANIFEST.json` + `INDEX.md` + `files/`. Copy by default.
- **Chat-gov compile (cousin):** `~/jwrangle/chat-governance/archives/<stamp>/`  
  `POST /api/archive` · `GET /api/archive-browser`. Finder only.

### Allowed APIs (exist — copy these, do not invent)

**CLI (serve/SEED SSOT — not the grok-skill fork):**

```text
python C:\Users\bardw\artifact-scanner\scripts\durable_land.py status
python C:\Users\bardw\artifact-scanner\scripts\durable_land.py land --src PATH [--note TEXT] [--name LABEL]
```

Signatures in `artifact-scanner/scripts/durable_land.py`:

- `land(*, src=None, from_capture=False, move=False, note="", label="", stamp=None) -> dict`
- `status() -> dict` (`render: durable-archive`, `lands[]`, `latest`, `capture_pending`)
- `list_lands(limit: int = 30) -> list[dict]`
- New stamps: `YYYYMMDDTHHMMSSZ`. Old `YYYYMMDD-HHMMSS` stay. Do not rename.

**HTTP (scanner finder, local, no keys):**

- `GET /api/durable-archive` (aliases `durable_archive`, `durable-land`, `durable_land`) → `status()`
- `POST /api/durable-archive/land` body `{src|path|from, from_capture?, move?, note?, label|name}`  
  `from` in `capture|inbox|test-write` → inbox. Refuses secret field names. **No `stamp` on HTTP.**

**Journal (Sesefus face):**

- Capture write: `apps/journal-daemon/record.py` `write_capture` → `%USERPROFILE%\test-write\journal\<stamp>\`
- Land hint already printed: `record.py` 129–134 (calls the CLI above)
- Schema land contract: `apps/journal-daemon/schema.md` **Land**
- Inbox land is **into journal stamps**, not durable: `inbox.py` `land_file` / `land_new_from_designated`
- Review already names both roots: `review.py` `CAPTURE` + `LANDS` (lines 10–11, 26–43)

**Already landed (do not recopy unless asked):**

- `lands/20260812-142824` — journal-ui (`audio.webm` + `meta.json`)
- `lands/20260814T210200Z` — sieve-intent-read-first cue pack (8 files, no `meta.json`)

### Gaps (evidence)

1. Journal does **not** call `land()`. Most `test-write\journal\<stamp>\` never reach durable-archive.
2. `review.py` 36–38 **skips any land without `meta.json`**. Cue pack `20260814T210200Z` is invisible there.
3. `board.html` has **zero** `durable-archive` hits. Do not add a board door this plan.
4. session-map still **404s** when `ok` is false (`win_serve.py` 5273–5282). Named open only on the parent will-sieve plan. Smoke before coding.
5. No `test_durable` in artifact-scanner. Journal tests: `apps/journal-daemon/tests/test_inbox_land.py` (copy that unittest shape).

### Anti-patterns (Phase 0)

- Import `~/.grok/skills/durable-land/scripts/durable_land.py` (fork CLI; serve does not use it)
- `GET` land-by-stamp / delete / unland / search (do not exist)
- Auto-land the whole `test-write` inbox (would grab non-journal files)
- `--move` / `move: true`
- Rename stamps
- Clone shredder into this store
- Grow scanner card acts past 3
- Re-add terminal dock

---

## Phase 1 — See the store (review face)

**What:** `review.py` must list **every** durable land, not only those with `meta.json`. Unlanded journal stamps stay visible as `capture`.

**Copy from:**

- `list_lands()` in `artifact-scanner/scripts/durable_land.py` 190–220 (stamp, path, label, note, file_count, bytes)
- Existing row print in `review.py` 45–53
- Cue pack INDEX: `durable-archive/lands/20260814T210200Z/INDEX.md`

**Do:**

1. For lands: prefer `MANIFEST.json` `label` / `note` / `file_count`. Fall back to `meta.json` BA fields when present.
2. Print source `capture` vs `land`.
3. Keep BA glance line. Add one line when a land has no meta (show label/note instead of null mood).
4. Do not write a new review app. Do not call `:8765`.

**Verify:**

- `python C:\dev\sesefus\apps\journal-daemon\review.py` prints stamp `20260814T210200Z` and note containing `will-sieve`.
- Still prints journal captures under `test-write\journal`.
- Exit 0.

**Anti-pattern:** treating cue-pack lands as broken because they lack mood scores.

---

## Phase 2 — Land pending journal (copy only)

**What:** one helper that lands **one** journal stamp dir via the existing `land()` API. Then a `--pending` pass over captures that have `audio.*` + `meta.json` and are not already a land `source`.

**Copy from:**

- `durable_land.land(src=..., note=..., label=...)` return dict (`ok, stamp, path, file_count, deleted`)
- CLI hint already in `record.py` 131–133
- `schema.md` Land paragraph
- Unittest shape: `apps/journal-daemon/tests/test_inbox_land.py` (temp dir, assert copy exists, original stays)

**Do:**

1. Add `apps/journal-daemon/land_durable.py` that **imports** `artifact-scanner/scripts/durable_land.py` (sys.path to that scripts dir) and calls `land()`. Do not reimplement copy/hash.
2. CLI: `python land_durable.py --src <journal-stamp-dir>` and `python land_durable.py --pending` (only audio+meta journal stamps).
3. `note` / `label` from stamp + `journal`.
4. Never `--move`. Assert `deleted == 0`.
5. Skip `_cues` and names starting `_`. Skip NOTE-only stamps.
6. Do **not** land the sieve-intent brief folder again.

**Verify:**

- Unit test: tempfile journal stamp → `land()` into a tempfile lands root if you can pass root via existing `config` / do not invent a new HTTP field. If `land()` only writes the live durable root, smoke **one** real pending stamp and check original still on disk.
- `durable_land.py status` shows a new stamp; `LATEST.txt` updates.
- Original `test-write\journal\<stamp>\` still exists.

**Anti-pattern:** `from_capture=True` on `--pending` (that lands the whole inbox). Landing `you/briefs` again.

---

## Phase 3 — One dogfood loop (record → land → review)

**What:** the proving course the Tue meet locked: durable directory + `~/test-write`.

**Copy from:** week lock in `days/Tue2611th/meet-will-sieve-ui.md`. Capture contract in `schema.md`.

**Do:**

1. One free-form capture **or** land one existing unlanded stamp (prefer existing audio+meta — do not force a new recording if one sits in `test-write\journal`).
2. Run `land_durable.py` then `review.py`.
3. Open Explorer on the new `lands/<stamp>/` (copy of the last-turn habit).
4. One line on `q-meet-will-sieve.md` under spike 1: archive flesh is the store + review can see cue pack + journal land. Do not enqueue a new queue.

**Verify:**

- Review shows both `20260814T210200Z` (cue pack) and the journal land.
- You can open the land folder without the scanner.

**Anti-pattern:** requiring `:8765`. Transcription. Claiming encryption.

---

## Phase 4 — Finder tax only if it still bites

**What:** session-map 404 on **normal session paths** (parent plan Phase 2 support). Smoke first.

**Copy from:** `build_session_map` `win_serve.py` 2177–2263. Route 5273–5282. Board fail paint `board.html` ~4351.

**Do:**

1. Pick one live grok session dir that has `summary.json` or `chat_history.jsonl`.
2. `GET /api/session-map?path=<that path>` against running serve. If 200 + spine: **stop**. Write “closed on smoke” on this plan. Do not refactor.
3. If 404 on a real session-shaped path: fix **path resolve** only (`resolve_path` / encoded `C%3A` vs disk). Map stays map, not a transcript dump.
4. Do not add durable-archive UI to the board.

**Verify:**

- Session-shaped path → 200. Empty path / random file → still 404 with `ok: false`.
- Grep `board.html` still has no `durable-archive`.

**Anti-pattern:** funneling lands through `isSessionPreview`. Inventing `GET /api/durable-archive/<stamp>`.

---

## Phase 5 — Verification (close the flesh slice)

1. `python durable_land.py status` → `ok`, lists cue pack + at least one journal land, `keys_used` false, `deleted` 0.
2. `python review.py` → cue pack visible by label/note; captures still listed.
3. One journal stamp landed this slice; original capture dir still on disk.
4. Grep plan anti-patterns: no new `/api/archive` write, no shredder import, no `board.html` durable tab.
5. Parent sequence still: AyTree leave → **this store usable** → reconstruct face → **then** sieve.

**Done when:** you use durable-archive this week without asking “where did it go,” and review does not lie by omission.

---

## Files likely to change (implementer)

- Modify: `C:\dev\sesefus\apps\journal-daemon\review.py`
- Create: `C:\dev\sesefus\apps\journal-daemon\land_durable.py`
- Create: `C:\dev\sesefus\apps\journal-daemon\tests\test_land_durable.py`
- Touch (one line): `C:\Users\bardw\jwrangle\days\Thu2613th\q-meet-will-sieve.md` (or the live day’s will-sieve payload)
- Touch only if smoke fails: `C:\Users\bardw\artifact-scanner\win_serve.py` `resolve_path` / `build_session_map`
- Do not touch: `board.html` archive-browser, `shredder/*`, chat-governance

## Open questions (do not block Phase 1–2)

- Auto-land on every `record.py` success? Default **no** — keep the hint; `--pending` is the batch door.
- Sesefus journal UI button that POSTs `/api/durable-archive/land`? Later. Capture must keep working with scanner down.

## Suggested first engage

Phase 1 `review.py` so today’s cue pack is visible. Then Phase 2 `--pending` for one real journal stamp.
