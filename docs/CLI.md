# Sesephus CLI Command Reference (0.1.0)

> ⚠️ **[CANON.md](CANON.md) §2 is authoritative.** `journal`, `rhythm`, `stoic`,
> `lead mine|feed`, and most of `vault` are **STUBS**. `journal` prints STUB +
> the Clippers pointer; finish path is consume `takes.jsonl` schema=1 — it does
> not record. `voice.bat` and `tools/voice.py` are historical and unsupported.
> Current Voice is the external Desktop Clippers tree at
> `C:\dev\journal-clippers\audio-journal-system`; this repository does
> not launch it. The retained scheduler logic is `alarm`.

**Sesefus** is an audio-first personal growth engine that combines circadian rhythm enforcement, encrypted audio journaling, and intelligent agentic support to cultivate Stoic resilience and negentropic refinement.

All user and dashboard interactions must route through this Zig CLI (or its mirrored HTTP API) to ensure production safety and guardrails.

---

## Global Options

The CLI supports the following global flags across all commands:

* `--production`: Enables strict safety mode. Destructive actions (like deleting groups or journals) will prompt for confirmation or require explicit override flags.
* `--dry-run` or `-n`: Test mode. Output what *would* happen without executing the state change.
* `--help` or `-h`: Show the command usage help text.
* `--json`: **Parsed but currently inert** (reserved) — no command emits JSON yet.

---

## Core Modules

### `status`
Speaks or prints the current state of the engine, connected clients, and the next scheduled rhythm cue.

```bash
ssfs status
```

---

### `journal`
**STUB.** Not a recorder. Capture owner is external Desktop Clippers at
`C:\dev\journal-clippers\audio-journal-system`. Finish path: consume Clippers
`takes.jsonl` (`schema=1` — keep text; wav already destroyed). Optional
`--tape <takes.jsonl>` exercises that reader. Historical `voice.bat` is
unsupported.

* `ssfs journal record` — STUB. Does not start a session.
* `ssfs journal review [--tape takes.jsonl]` — STUB. May consume a tape row; no mic.
* `ssfs journal prompt` — STUB. Will not invent a stoic prompt.

---

### `rhythm`
**STUB.** Deferred to live `alarm *`. Does not print fake ALIGNED state or a
fake countdown.

* `ssfs rhythm schedule morning` — STUB; use `alarm schedule`.
* `ssfs rhythm schedule evening` — STUB; use `alarm schedule`.
* `ssfs rhythm next` — STUB; use `alarm list`.

---

### `stoic`
Voice-based stoic practice and reflection.

* `ssfs stoic daily-reflection` - Guided evening audio review based on Stoic principles.
* `ssfs stoic virtue-check <virtue>` - Quick voice check-in on a specific virtue (e.g., `courage`, `wisdom`, `justice`, `temperance`).
* `ssfs stoic obstacle` - Speak your current obstacle and receive reframing logic.

---

### `lead`
Intelligent voice-fed content and data mining.

* `ssfs lead mine stoic` - Find high-signal stoic ideas to journal about.
* `ssfs lead feed journal` - Turn good ingested input into new journal prompts.
* `ssfs lead qualify <post_text>` - **WIRED** — score a post via `tools/qualify_post.py`.

---

### `aytree` (suite Version Control / derivation map)

External sibling module **AyTree** — directory lineages + notes + spatial structure.
Not full git VCS. Does not replace LeadLogic’s employment domain.

* `ssfs aytree open` / `ssfs aytree map` — **WIRED** — open lineage map (`/derivation`)
* `ssfs aytree tree` — **WIRED** — open in-repo tree tool
* `ssfs aytree serve` — **WIRED** — AyTree server foreground
* `ssfs aytree status` — **WIRED** — probe local server
* `ssfs tree …` — alias of `aytree`
* Windows: `aytree.bat` from repo root

Resolve path: `AYTREE_ROOT` · `sesefus.config.json` `aytree_root` · sibling `../AyTree`.
See [CANON.md](CANON.md) §7.

---

### `vault`
Your private, encrypted voice history management.

* `ssfs vault status` - Check how full your journal vault is and see metadata.
* `ssfs vault key-verify <hex_key>` - Verify the decryption key against the vault.
* `ssfs vault backup [dest_path]` - Safely backup the encrypted vault database.

---

### Wired Modules (the ones that actually work)

Contrary to the sections above, these are **not** legacy — they are the live,
WIRED command surface (CANON §2):

* `ssfs alarm schedule|group|list|toggle|bulk|interval|adjust ...` — the real scheduler
* `ssfs group create|list|rename|edit|delete ...` — alarm-group CRUD
* `ssfs lead qualify`, `ssfs vault ingest-archive`, `ssfs dialogue start|review`

---

*Historical command reference. Do not use it as current Voice launch guidance.*
