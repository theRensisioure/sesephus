# The Covenant — Sesefus's constraint-first contract

> Companion to `CANON.md` (terminology/status) — this file is the *architectural
> promise*. Where a build decision and this file disagree, one of them must be
> fixed before merging.

## The axiom

**The maker may concede to cloud; the user never must.**

Offline-first is not a preference. It is a promise that a vulnerable user will
not depend on infrastructure that can fail, surveil, or demand a fluency they
lack or are losing. The design target is the *intersection* of dyslexia and
early-dementia constraints — one thing at a time, never punished for
forgetting, never assumes fluent reading, stable across time, works with the
network unplugged. Design for that seam and it serves both.

The CLI thesis: the terminal, done right, may be the *most* accessible surface,
not the least. Honest, fast, deterministic, offline, yours — the properties
that protect a fragile user. The enemy was never the command line; it was the
maximalist GUI.

## The spine — one loop, three profiles

One dialogic turn-taking loop over the encrypted vault, rendered through the
DyslexiUI reading layer, with I/O modality as a single swappable knob:

| Profile | In | Out | Status |
|---|---|---|---|
| **memoir** (maker) | typed dialogue | calm text (DyslexiUI measure/spacing) | **WIRED** — `dialogue start` / `dialogue review` |
| **appliance** (user) | voice (existing mic capture) | spoken (offline OS TTS) + optional screen | **PARTIAL** — TTS-out and the loop are WIRED (`dialogue start appliance`); voice-in is still the separate capture path, not yet plumbed into the loop |
| **import** | existing writing → vault `sources/` | — | **INTENT** — nothing moved until integrity is verified before and after |

Implementation anchors: `core/sesephus/src/commands/dialogue.zig` (the loop),
`core/sesephus/src/speech.zig` (spoken output), `database.zig` `JournalEntry`
prose fields (`entry_kind`/`text`/`prompt`/`session_id` — same encrypted frame
format as audio), `dashboard/ui/src/dyslexiui-tokens.css` (canonical reading
tokens; Dyslexistree / gui-dyslexia-encode / the Grok layer are design sources
that defer to it).

Spoken output uses only synthesizers the OS ships — SAPI via PowerShell on
Windows, `espeak-ng`/`espeak` on Linux (the Pi appliance target), `say` on
macOS. No network, no bundled model, no new runtime dependency. Speech is
additive: text always prints first, and a missing synth degrades to text with
one quiet notice — it never blocks the loop.

## The boundary (hard rule)

**The user-facing path imports zero cloud and zero GUI-maximalism.** The
following are maker-side / experimental and must stay unreachable from the
covenant path — never imported by, spawned from, or required for `dialogue`,
the vault, or the appliance profile:

- xAI/Grok backends in `tools/etdi_inference.py` and `shredder/image_sieve.py`
  (opt-in maker tooling; the user path may never select them)
- `docs/vision.md` cloud-escalation, LoRA fine-tuning, and quantization
  ambitions (vision prose, not covenant scope)
- the three dashboards (React/Vite `dashboard/ui`, embedded `dashboard.html`,
  Tauri `aether-dashboard-v2`) — displays may *read* vault text through the
  DyslexiUI tokens, but the loop must complete without any of them running

A PR that makes the user path depend on any of these violates the covenant and
should be rejected regardless of what it adds.

## Verification (run these, don't argue)

1. **Eyes-free:** with a speech engine installed, run
   `dialogue start appliance` with the display off; a full capture → `dialogue
   review appliance` reflect cycle must be completable by ear.
2. **Unplugged:** cut all non-loopback network; the loop, vault persistence,
   and review must function end-to-end with zero external calls.
3. **Memoir:** type a dialogue turn; confirm it lands in the encrypted vault
   (`--read-vault`) and renders back inside the DyslexiUI measure.

## Hardware intent

A Raspberry Pi Zero 2 W single-purpose appliance — boots into the dialogue
loop, no login, no updates, no cloud, no "which app do I open" — is the
covenant made physical. The appliance profile is its software; the Pi itself
is unbuilt intent, tracked here so nobody mistakes it for shipped.
