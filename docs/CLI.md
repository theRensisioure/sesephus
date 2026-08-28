# Sesefus CLI Command Reference

> ⚠️ **STALE — [CANON.md](CANON.md) §2 is authoritative.** Most module commands
> documented below (`journal`, `rhythm`, `stoic`, `lead mine|feed`, most of
> `vault`) are **STUBS**: they print a canned line and do nothing. `voice.bat`
> and `tools/voice.py` are historical and unsupported. Current Voice is the
> external Desktop Clippers tree at
> `C:\Users\bardw\Desktop\corection-goald\journal-clip`; this repository does
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
Historical command shape for Sesephus audio journaling. The handler is a stub;
this is not the current Voice path.

* `ssfs journal record [minutes]` - Start a voice journal. Defaults to 3-10 minutes.
* `ssfs journal review last` - Listen to your last entry.
* `ssfs journal prompt stoic` - Get a spoken stoic reflection prompt.

---

### `rhythm`
Circadian anchors through predictable, rhythmic sound and voice cues.

* `ssfs rhythm schedule morning` - Set the morning ritual alarm sequence.
* `ssfs rhythm schedule evening` - Set the evening wind-down cue.
* `ssfs rhythm next` - Ask the system: "What is my next growth anchor?"

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
