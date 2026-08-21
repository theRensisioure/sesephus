# Plan — Sesefus dual-module small app · journal + alarms (daemon)

**Date:** 2026-08-11  
**Mode:** product lock + build map (foundation week)  
**Status:** direction locked · Zig `journal`/`rhythm` remain **STUB** in CANON · scanner suite is **not** the host

---

## Honesty: Arcadium / Circadia “into Artifact Scanner”

**Not unblocked as real integration.** On disk today:

| Claim | Reality |
|-------|---------|
| Suite rack cards show Arcadium / Circadia implementation | Spike only (`spikes/001-suite-card-rack`) · Parked · not product host |
| Scanner loads Sesefus modules | **No** — SEED: scanner is finder; `?window=sesefus` is frame/inventory, not suite glue |
| Rails flips to Sesefus audio journal | **Wish / week prose** — live Rails = Todo ↔ jwrangle only (smoked) |
| CANON `journal` / `rhythm` | **STUB** (print lines; no record, no schedule) |

So you did **not** unlock Arcadium/Circadia inside the scanner host. Names can live as **product faces of this small app**; do not wait on suite/server mechanics.

---

## Product spine (this plan)

**Ditch for this surface:** Artifact Scanner / suite **as runtime host** for alarms + record (no pywebview suite card required to journal; no serve-on-8765 dependency for capture).

**Build:** Sesefus as a **dual-module small app** that runs as a **daemon** (always-on background process + tiny UI or tray later):

| Module | Job | BA role |
|--------|-----|---------|
| **Record** (audio journal) | Free-form capture → durable land (copy into stamp) | Richness, narrative, raw material |
| **Alarms** (sampling windows) | Enforce consistent time points / prompts | Consistency so patterns become visible |

**Optional third face (not a third daemon):** **Review** — read several days of lands + dimension sidecars; correlations are a **report step**, not a second host.

Rename map (prose only until code tokens exist):

- **Circadia-ish** → Alarms / rhythm sampling (windows, next cue, status)  
- **Arcadium-ish** → Record / activity richness (free-form audio + post-hoc BA dims)  
- **Sesefus** → the small app brand that owns both modules

---

## Free-form + classic BA (both, not either/or)

| Need | Mechanism |
|------|-----------|
| Richness | Pure free-form audio at any time (`record now`) |
| Consistency | Alarm windows fire → optional short capture or “missed” mark |
| Dimensions (after the fact, lightweight) | Sidecar per entry (JSON), filled at end of capture or later review: (1) rough **activity category**, (2) **duration/context**, (3) **mood / pleasure / mastery** as 0–10 (spoken number OK → parse later; for v0 type or say and store raw) |
| Review | Multi-day pass over lands + sidecars → notice inactive stretches ↔ low mood, micro-lifts, etc. |

**v0 dimensions schema (sidecar `meta.json` next to audio or in stamp):**

```json
{
  "activity": "string or null",
  "duration_min": null,
  "context": "string or null",
  "mood": null,
  "pleasure": null,
  "mastery": null,
  "sampled_by": "alarm|freeform",
  "alarm_id": null,
  "note": ""
}
```

Transcription stays **parked** (durable land law). Review can use filenames + meta + optional later ASR.

---

## Architecture (v0)

```
sesefus/apps/journal-daemon/     # small app home (Python first for dogfood speed)
  daemon.py                      # long-lived: alarm loop + optional tray later
  record.py                      # one-shot or daemon-triggered capture
  alarms.json                    # schedule SSOT (user-editable)
  schema.md                      # dimensions + land layout
  README.md

Capture path:  %USERPROFILE%\test-write\journal\   (or config)
Land path:     durable-archive via artifact-scanner scripts/durable_land.py
               OR local lands under ~/jwrangle/durable-archive (same roots)
```

**Runtime rules**

- Daemon owns **alarms only** at first (poll schedule, fire toast/sound/log, optional auto-start record window).  
- Record can be CLI without daemon (`record.py`) for free-form.  
- **No** dependency on `:8765` for capture.  
- Scanner may **later** open lands as files (finder) — inventory, not host.  
- Zig `journal`/`rhythm` stay stub until this dogfood proves the UX; then either wire or replace honestly in CANON.

---

## Phases

### Phase 0 — Lock (this file + day board) ✓ intent

- Scanner host mechanics **out** for journal/alarms runtime  
- Dual module = record + alarms; review = offline step  
- BA dims in sidecar; free-form allowed anytime  

### Phase 1 — Skeleton dogfood (build next)

1. `apps/journal-daemon/` README + `alarms.json` sample (e.g. 3 fixed windows)  
2. `record.py` — write wav or placeholder + `meta.json` into capture inbox  
3. `daemon.py` — loop: next alarm, log fire, optional prompt file  
4. Land: call durable_land or copy into stamp after session  

**Exit:** one free-form land + one alarm-fired log without scanner running.

### Phase 2 — Dimensions UX

- End-of-record prompt (CLI questions or single spoken line parse later)  
- Fill mood/pleasure/mastery 0–10  
- `review.py` — last N days table (no ML)

### Phase 3 — Honesty in CANON / suite language

- Document dual-module app as the real Circadia/Arcadium stand-in  
- Suite card rack: **pointer only** or drop until app ships faces  
- Do not claim WIRED journal/rhythm until true  

### Phase 4 — Optional tray / Windows service

- Startup login item; tray record + next alarm  
- Still not scanner-hosted  

---

## Anti-patterns

- Loading journal into scanner suite as requirement to record  
- Fake Arcadium/Circadia “implementation” cards with no daemon  
- Full transcription/embeddings before durable capture works  
- Dual public/private vault theater  
- Making review a second always-on product before land+dims exist  

---

## Relation to foundation week

| Track | Role |
|-------|------|
| Durable archive land | **Sink** for journal files (already smoked) |
| Rails smoke | Separate; optional later open-of-lands |
| Will-sieve UI | Spearhead prose; daemon is the **proving course** for audio |
| check-names Fortnite titles | Habitat for chats; not this app |

---

## Done when (v0)

- [ ] Free-form record lands without scanner  
- [ ] Alarm fires on schedule (log + optional capture cue)  
- [ ] Sidecar can hold 3 BA dimensions  
- [ ] Multi-day review list exists (even markdown)  
- [ ] Docs say: Arcadium/Circadia not scanner-hosted; this app is the dual module  
