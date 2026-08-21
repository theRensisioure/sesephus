Z# Plan — Light rules complexity budget (Sesefus speech-display module)

> **For implementers:** execute phase-by-phase; do not invent a second host or chat stream.  
> **Parent product:** Sesefus **small app** (`apps/journal-daemon` · UI `:8777` · Start “Sesefus”).  
> **Not:** Artifact Scanner host · Grok stream · LM Studio desktop chat dump.

**Goal:** Decide how complex **light rules** (deterministic pre-LLM structure) can get so they stay **fast**, **reliable**, and **do not compete with** optional later local LLM latency or correctness.

**Architecture (locked from interview so far):**
- **Display, not stream.** Structured speech appears **in the Sesefus UI** (same app as Record + Alarms). No “output text to chat” product surface.
- **Brain v0 = light rules.** Local LLM (LM Studio / remote box) is **optional later**, not required to ship the face.
- **Reserved (user):** (1) third module vs Record mode · (3) clear vs land on next utterance. Plan must not force those; leave hooks only.

**Tech stack (when built):** Python under `apps/journal-daemon/` · existing `ui_serve.py` / `ui.html` · optional later OpenAI-compat client to LM Studio `http://host:1234/v1`.

**Dogfood note:** That word was agent thrash. Product language = **module · display · light rules · optional model**. Do not re-center “journal dogfood.”

---

## Phase 0 — Documentation / surface discovery (before any rule engine)

### What to read (copy patterns, don’t reinvent)

| Source | Why |
|--------|-----|
| `C:\dev\sesefus\apps\journal-daemon\README.md` | Launch, modules, port 8777 |
| `ui.html` · `ui_serve.py` · `ui_host.py` | Dual-module UI + JSON APIs |
| `schema.md` · `record.py` | Capture + meta.json shape |
| `C:\dev\sesefus\plans\2026-08-11-journal-alarm-daemon.md` | Dual-module spine (Record + Alarms; Review face) |
| `C:\Users\bardw\jwrangle\YOU-AGENT.md` | you/ vs agent/ if new files land |
| LM Studio OpenAI compat (docs) | Only Phase 4+; `POST /v1/chat/completions` stream optional, **not** required for light rules |

### Allowed APIs (later model path — do not invent)

- `GET /v1/models`
- `POST /v1/chat/completions` (`stream: true|false`)
- Optional `POST /v1/responses` on newer LM Studio — **only if** already on that build; prefer chat/completions for one client shape

### Anti-patterns (Phase 0 guards)

- Do **not** put this module under Artifact Scanner serve (`:8765`)
- Do **not** require Zig REPL / CANON stubs (`journal` is STUB; this app is the real face)
- Do **not** design light rules as a mini-NLU that “almost LLMs”
- Do **not** block UI paint on network or model load

### Phase 0 exit

- One short **Allowed surface** note in this plan’s “Done when” (already partially filled below)
- Confirm: structure pipeline = **sync function** `raw_text → structure_dict` with hard time budget

---

## The complexity answer (decision record)

### Latency budgets (hard)

| Stage | Budget | Notes |
|-------|--------|--------|
| Light rules after transcript arrives | **≤ 30 ms** typical · **≤ 100 ms** absolute max on mid laptop | Must feel instant next to STT |
| UI paint of structure | **≤ 1 frame** after rules return | DOM only; no server round-trip required for pure client rules |
| STT (whatever mic path) | **Separate** budget; rules must not wait on mic |
| Optional LLM later | **≥ 200 ms–several s** | Must be **async** · never gate first paint |

**Rule of thumb:** if a rule needs more than one linear pass over the string + a small fixed set of regexes/keyword maps, it is **too complex for light rules** → defer to model or human edit.

### Reliability law

Light rules may only do what is **deterministic and explainable**:

| Allowed | Forbidden (unreliable / overshadows LLM) |
|---------|------------------------------------------|
| Split on silence markers / newlines / ` — ` / `. ` when clear | Guess sentence boundaries across ASR garbage with ML |
| Keyword / phrase lists (activity, mood digits, “park”, “queue”) | Soft intent classification (“sounds like anxiety”) |
| Pull numbers 0–10 near mood words | Infer mood without cue words |
| Strip fillers (`um`, `uh`, `like` optional) with toggle | Aggressive rewrite that changes meaning |
| Tag **sections** you already use (what I said · want · park) | Invent ontology from free text |
| Flag `[unclear]` when no pattern hits | Fake confidence / silent wrong structure |
| Preserve **raw** always beside structured | Overwrite raw with “cleaned” only |

**Unreliable = any rule whose failure mode is silent wrong structure.** Prefer **under-structure** + raw display over clever wrong buckets.

### Complexity ceiling (how far light rules can go)

**Tier A — always ship (cheap, reliable)**  
Complexity budget: **~50–150 LOC**, pure functions, no deps.

1. Normalize whitespace; keep raw copy.
2. Optional filler strip (off by default if dyslexia/voice identity matters).
3. Split into **utterance lines** (newline or `. ` / `? ` / `! ` only when capital follows or end).
4. **Keyword tags** from a **user-editable** list file (you/): e.g. `sesefus`, `msi`, `park`, `will`, mood words.
5. **BA-shaped extract** only when explicit: `mood 6`, `mood is 6`, `pleasure 4` → fields matching `schema.md`.
6. Output shape fixed JSON for UI:

```json
{
  "raw": "...",
  "lines": ["..."],
  "tags": ["..."],
  "fields": { "mood": null, "activity": null },
  "flags": ["unclear"],
  "rules_ms": 12
}
```

**Tier B — careful (only if Tier A stays under budget)**  
Still no model. Cap: **one extra linear pass**.

1. “Bulletize” if user said “bullet” / “list” / numbered ASR (`1.`, `2.`).
2. Simple **sortation**: lines matching tag lists → buckets `do` / `park` / `open` / `other` (keyword only).
3. Cap lines shown (e.g. first 12 + “+N more”) so display never floods.

**Tier C — do not put in light rules**  
These **overshadow LLM** (duplicate its job) or go unreliable:

- Paraphrase / expand rough speech into prose
- Cross-sentence coreference (“that thing from earlier”)
- Ranking by “importance” or “will strength”
- Multi-language guess
- Emotion model / sentiment beyond keyword
- Dialogue state machine across many turns (that’s session memory, not light rules)
- Any network call

**LLM’s job later (if ever):** expand · sort by latent intent · will-sieve stick rule · multi-turn.  
**Light rules’ job forever:** **fast skeleton + explicit fields + never lie.**

### Interaction with optional LLM (so rules don’t fight latency)

```
transcript ready
    → light_rules()          # sync ≤100ms → paint UI immediately
    → optional: enqueue llm  # async; when done, paint "expanded" panel
    → clear face             # drops UI state; land path = reserved (3)
```

- First paint **never** waits on LLM.
- If LLM fails/timeout: UI still has Tier A/B structure + raw.
- Rules must **not** pre-chew text so hard that LLM gets garbage (keep raw full fidelity).

---

## Phase 1 — Spec only (no product feature yet)

**What:** Lock the budget into a short module note next to the app (when implementing, under `you/` if new docs).

**Deliverable content:**
- Tiers A/B/C as above
- Fixed JSON schema for display
- Latency numbers
- Explicit: paraphrase = model-only

**Verify:**
- [ ] A human can read the note in &lt; 2 minutes
- [ ] No Tier C item listed under A/B

**Anti-pattern:** writing a second English grammar in rules.

---

## Phase 2 — Pure function + tests (no UI required first)

**Files (when built):**
- Create: `apps/journal-daemon/speech_rules.py` (or `structure_rules.py`)
- Create: `apps/journal-daemon/tests/test_speech_rules.py` (or pytest under app)
- Optional config: `speech_keywords.json` (user-editable tag list)

**Tasks (bite-sized):**

### Task 2.1 — Empty contract

Implement:

```python
def structure_utterance(raw: str, *, keywords: list[str] | None = None) -> dict:
    ...
```

Always returns keys: `raw`, `lines`, `tags`, `fields`, `flags`, `rules_ms`.

### Task 2.2 — Tests for Tier A

Cases:
- empty → flags include `unclear`, lines `[]`
- `"mood 7 walked the dog"` → fields.mood == 7, tags may include walk if listed
- fillers optional
- raw never mutated away

Run: `pytest apps/journal-daemon/tests/test_speech_rules.py -v`  
Expect: pass; assert `rules_ms < 100` on 2KB string.

### Task 2.3 — Benchmark gate

One test or script: 1000× structure on a 500-char noisy transcript; **p95 &lt; 30 ms** on dev machine or mark xfail with measured number.

**Anti-pattern:** spaCy / transformers / NLTK downloads in this path.

---

## Phase 3 — Display in Sesefus UI (display ≠ chat output)

**Depends on reserved (1):** third panel vs Record mode — **implement only the paint path once (1) is chosen.**

**What:**
- Show `raw` and structured blocks **in the window**
- Big **Clear** control (next utterance) — land behavior per reserved (3)
- Never “send to Grok” / never required clipboard product path

**Files:**
- Modify: `ui.html` (structure panel)
- Modify: `ui_serve.py` only if structure runs server-side; **prefer client-side JS port of Tier A** *or* one `POST /api/structure` that calls `structure_utterance` (sync)

**Latency:** API structure call local loopback only; no remote.

**Verify:**
- [ ] Paste rough text → structure appears without model
- [ ] Clear empties face in one click
- [ ] Raw still visible until clear

**Anti-pattern:** streaming tokens in this phase.

---

## Phase 4 — Optional LLM expand (async only)

**Only after** light rules paint is trusted.

- Client or serve calls LM Studio OpenAI compat when user hits **Expand** (explicit), not on every utterance
- Timeout (e.g. 8–15 s) → keep light structure
- Expanded pane separate from light structure (don’t overwrite raw)

**Verify:**
- [ ] With LM Studio down, Expand fails soft; light rules still work
- [ ] First paint time unchanged with Expand idle

---

## Phase 5 — Verification (whole path)

1. Grep: no `stream` product path required for v0 display module  
2. Grep: no scanner `:8765` dependency for structure  
3. Latency: structure path measured under budget  
4. Reliability: 10 real rough ASR pastes — zero silent wrong mood numbers (only extract when explicit)  
5. you/agent: any agent-suggested experiments under `agent/`; requested module code in app tree as product

---

## Open spikes (not grilled further)

| Spike | Why |
|-------|-----|
| STT source (browser Web Speech · Whisper local · Maono path) | Independent of rules budget |
| Reserved (1) module slot | Affects UI layout only |
| Reserved (3) clear vs land | Affects persistence only |
| Where LLM runs (Start9 Debian · brother PC · later) | Phase 4 host only |

---

## Priority cut

| Now (this plan’s value) | Later |
|-------------------------|--------|
| Lock Tier A/B/C + latency numbers | Build UI module |
| Pure `structure_utterance` + tests | Async Expand |
| Display-first contract | Multi-turn will sieve |

**Urgent for Heavy burn (if any):** implement Phase 2 tests + function — smallest proof the budget is real.  
**Not urgent:** hardware liquidation, Surface music, MSI math (other thread).

---

## Requirements brief (interview slice)

**Goal:** Know how complex light rules can get without lagging or lying, so a Sesefus **display** module can structure rough speech before any LLM.

**In scope:** Deterministic structure tiers, latency budgets, reliability law, handoff shape to optional LLM, fit to `journal-daemon`.

**Out of scope:** Chat streaming product · scanner host · forcing answers to reserved (1)(3) · hardware buy path · recreating full English grammar in rules.

**Hard constraints:**
- Display in Sesefus UI, not text-out-as-product
- First paint never waits on LLM
- Light rules ≤ ~100 ms hard; prefer ≤ 30 ms
- Under-structure &gt; wrong structure
- Streamlined Sesefus = `apps/journal-daemon`

**Open spikes:** STT path · module slot (1) · clear/land (3) · LLM host

**Sources / paths:**
- `C:\dev\sesefus\apps\journal-daemon\`
- `C:\dev\sesefus\plans\2026-08-11-journal-alarm-daemon.md`
- This file

**Done when:**
- [x] Written complexity ceiling (Tier A/B/C) + budgets
- [ ] (Build later) `structure_utterance` + tests under budget
- [ ] (Build later) UI displays structure; clear works; LLM optional

---

## One-line thesis

**Light rules = fast skeleton + explicit fields; LLM = slow expand; never make rules do the model’s job.**
