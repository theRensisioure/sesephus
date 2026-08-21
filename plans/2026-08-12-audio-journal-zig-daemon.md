# Plan — Secure Sesefus as built Zig daemon (audio journal spearhead)

**Date:** 2026-08-12  
**Repo:** [Zychs/sesefus](https://github.com/Zychs/sesefus) · local `C:\dev\sesefus`  
**Goal (locked):** Secure **Sesefus** as a **built Zig daemon** that runs via **Win-key search → `Sesefus.exe`**, reuses the **best of the GitHub product** (alarm scheduler, host/client, vault honesty, zero-telemetry voice journal identity), **constrained to the recorder path specified below** — not a second microphone app, not Artifact Scanner suite host.

**Mode:** make-plan only until execute is requested.

---

## 0 · Product identity (re-locked)

| Role | What |
|------|------|
| **Spearhead** | **Audio journal** — the product people buy/download |
| **Capture** | **Outsourced** to Microsoft **Sound Recorder** (store app). We lean in; we do not re-fight codecs/mics |
| **Alarms** | **Infrastructure / distribution layer** — not the brand face. BA sampling windows across **time and space** (host↔client, scripts) |
| **Not spearhead** | “Alarm app” alone · in-house record widget · SHA thrash UI · suite card rack |

**One sentence:** Sesefus is the journal that *notices and schedules*; Windows records; vault keeps.

---

## 1 · Lessons from GitHub development hell (do not re-live)

Drawn from open issues, CANON, README, and recent merges on `Zychs/sesefus`:

### Honesty / stubs
- **#74 umbrella — End the stubs:** no command surface may lie (CANON §2 WIRED vs STUB).  
- **#66–#73** honesty program: Glass must not mock; rhythm purge → **alarm is the one scheduler** (#69); **journal \* → redirect to real capture path** (#68, historically `voice.bat`).  
- **#42** Circadia fabricated mock alarms when backend down — **never invent live alarm state**.

### Storage / vault (journal trust)
- **#76–#83** vault scan, startup self-check, backups that verify, key-loss, resolver via drive-mapping, single SSOT vault.  
- **#77** prove store-and-retrieve **before** accepting a journal entry.  
- **#63** hardcoded vault password hell — no default crypto theater.

### Dead weight already cut
- **#67** purge DEAD: duplicate vault handler, **`alarm_engine.zig`**, SaturnNav orphans — do not resurrect parallel alarm engines.

### Capture path history
- README already names **audio journaling** as primary product topic.  
- Wired: `alarm *` (Timekeeper), `vault ingest-archive`, host/client role, dialogue, vault extract.  
- Stub: old `journal *` REPL — **do not re-wire in-house record**; redirect to Sound Recorder + vault land.

### Scanner suite (not this product host)
- Artifact Scanner docking plan: **true reparent (`SetParent`) of foreign HWNDs is not the product path.** Winning pattern: **adjacency + `SetWindowPos`** (intent-prefabs), or iframe only for **own** loopback URLs.  
- Terminal dock removed from scanner; do not re-import suite hell into Sesefus.exe.

---

## 2 · Recorder path (constraint — non-negotiable)

```text
1. User intent: free-form or alarm-fired journal beat
2. Sesefus opens / cues Microsoft Sound Recorder
   CLI:  shell:AppsFolder\Microsoft.WindowsSoundRecorder_8wekyb3d8bbwe!App
   House: %USERPROFILE%\jwrangle\tools\sound-recorder.cmd
3. Files land: %USERPROFILE%\Documents\Sound Recordings\*.m4a
4. Sesefus vault land: symlink or hardlink/copy-into vault path
   (prefer link-out when same volume; copy+manifest when not)
5. Optional sidecar meta (activity / mood dims) — after capture, not instead of MS UI
6. Transcription: parked until vault self-check green (#77 class)
```

**Do not build:** competing capture UI, C++/Zig microphone widget as spearhead (abandoned `apps/record-widget`).

---

## 3 · Window “frame / embed” technique — verdict

| Technique | Verdict |
|-----------|---------|
| **SetParent foreign app (Sound Recorder) into our HWND** | **Practically not a product path** — Win32 reparent of modern UWP/WinUI store apps is fragile/broken; fails across elevations; banned by earlier docking honesty |
| **Own window embeds own webview/iframe** | OK for **our** UI only |
| **Adjacency frame** (`SetWindowPos` slot next to Sesefus chrome) | **Allowed / preferred** for “frame technique” feel — same as intent-prefabs |
| **On alarm: launch Sound Recorder + place beside tray/cue window** | **v1 shippable** |

**Plan language:** “frame” means **chrome + adjacent placement + focus handoff**, not true embed.

---

## 4 · Architecture (Zig daemon + Win search)

### 4.1 Ship surface
- **Binary:** `Sesefus.exe` (Zig build artifact, renamed/copied for Start Menu).  
- **Launch:** Win-key search **Sesefus** → shortcut → `Sesefus.exe` (not pythonw journal-daemon).  
- **Roles:** single exe, `--role host|client` (existing host.zig pattern) — keep; do not reintroduce host.exe/client.exe.

### 4.2 Modules (constrained)

```text
Sesefus.exe (Zig)
├── journal   — orchestrate capture (open Sound Recorder, watch inbox, vault link)
├── alarm     — ONE scheduler (existing Timekeeper) + distribute to clients
├── device    — probe primary-output endpoints; classify activity
├── net       — host↔client presence / foreign SSID signals (best of fleet/host)
└── vault     — resolve store, ingest/link recordings, refuse if self-check fails
```

Python `voice.bat` / Whisper may remain a **sidecar** for transcription later; v0 journal path does not depend on Whisper.

### 4.3 Alarms across time and space
- **Time:** schedule groups/intervals (reuse wired `alarm *` semantics; no second engine).  
- **Space:** host publishes fire events; **clients** on other machines run thin agent (same exe `--role client` or script) to:
  - show cue  
  - optionally open Sound Recorder  
  - report back: completed / missed / deferred  
- **Scripts:** allow external `on-alarm.ps1` / hooks for power users (host-client relationship, not only GUI).

### 4.4 Audio device probe + silence reasons (monitored)

Host probes **primary render** devices across reachable clients (and local):

| Class | Meaning |
|-------|---------|
| **active** | endpoint present, default or selected, healthy |
| **dead** | missing, disabled, error |
| **silence-needed** | reason must be **defined and monitored** (not a vibe) |

**Silence reasons (enum — store + log):**

| Code | Meaning |
|------|---------|
| `offline` | client unreachable |
| `foreign_ssid` | client on non-home SSID vs host policy |
| `preoccupied` | healthy busy signal (user-defined: full-screen app, call, etc.) |
| `dnd_sleepish` | DND / sleep schedule / quiet hours |

Only when a reason is **active and still true** may the system suppress cue audio on that device. Reasons expire or re-check on interval.

### 4.5 Vault symlink from Sound Recordings
- Watch inbox mtime.  
- On new `.m4a`: create **vault-relative** entry:
  - same volume → **hardlink or symlink** into vault journal dir  
  - else → **copy + MANIFEST** (drive-mapping rules; never silent dual-SSOT)  
- Startup: vault self-check before accepting new lands (#77).

---

## 5 · What to take from the best of the repo

| Keep / revive carefully | Leave parked |
|-------------------------|--------------|
| Zig `alarm *` + Timekeeper | Stub `journal *` as capture |
| Host/client role model | SaturnNav / LeadLogic as product face |
| Vault ingest-archive pattern | Glass mock Circadia (#42) |
| CANON honesty + zero-telemetry identity | In-scanner suite host |
| `voice.bat` as optional later ASR | Parallel `alarm_engine.zig` |
| drive-mapping / ssfs storage contract | Fake encryption defaults |

---

## 6 · Phased build (execute order)

### Phase 0 — Product law freeze (docs only)
- Update CANON / README primary path: **Sound Recorder + vault land**, not in-house record.  
- Mark `apps/record-widget` abandoned; `apps/journal-daemon` Python UI non-canonical.  
- Document silence-reason enum + frame = adjacency.

### Phase 1 — `Sesefus.exe` install surface
- `zig build` → `Sesefus.exe` in dist.  
- Start Menu shortcut “Sesefus” (searchable).  
- Cold start: host role, vault self-check, tray or tiny matrixentropic (film-green) status window.

### Phase 2 — Journal orchestration (spearhead loop)
- Command / tray: **Record** → launch Sound Recorder.  
- Inbox watcher → vault link/copy → entry appears in journal list (paths + times only).  
- Free-form anytime; no dims required for v0.

### Phase 3 — Alarm distribution (support spearhead)
- Local fire → cue + optional open Sound Recorder + adjacency frame.  
- Client registration + fire fan-out.  
- Missed/completed ack.

### Phase 4 — Device probe + silence monitor
- Enumerate endpoints on host + client reports.  
- Silence reasons monitored; log decisions.  
- Policy config: home SSIDs, quiet hours, preoccupied rules (start minimal).

### Phase 5 — Hardening from issue hell
- Wire vault backup/audit honesty (#70 class).  
- Stub regression guard (#73).  
- No mock alarm UI.

---

## 7 · Non-goals (this plan)

- Competing with Sound Recorder on capture quality  
- True SetParent embed of MS Sound Recorder  
- Scanner suite as Sesefus runtime  
- LeadLogic / SaturnNav in the journal binary  
- Transcription as launch blocker  

---

## 8 · Success criteria

1. Win-key **Sesefus** starts a **built Zig** `Sesefus.exe` that stays honest (no stub lies on journal path).  
2. User can complete a journal beat with **only MS Sound Recorder + Sesefus vault land**.  
3. Alarms fire locally; optional client fire; silence only with a **named monitored reason**.  
4. New takes under Sound Recordings appear under vault via **link or copy+manifest**.  
5. “Frame” = adjacency placement of recorder next to cue — documented as intentional, not failed embed.  
6. Issues #42/#67/#74-class failures do not regress.

---

## 9 · Immediate next execute slice (when you say go)

1. Branch from clean product tip (not record-widget thrash): e.g. `release/sesefus-journal-daemon`.  
2. Phase 0 doc freeze + Start Menu `Sesefus.exe` from existing Zig build.  
3. Phase 2 minimal: `record` action → `sound-recorder.cmd` + inbox→vault link.  
4. Phase 3 thin: one local alarm → cue + open recorder + SetWindowPos adjacency.

---

## 10 · Goal restated

> Secure Sesefus as a **built Zig daemon**, launched by **Win-key search (`Sesefus.exe`)**, using the **best of github.com/Zychs/sesefus** (alarms, host/client, vault, honesty), **constrained to outsourced Sound Recorder + vault land**, with alarms as **distribution infrastructure** for the **audio journal** spearhead — not the product face, and not a second recorder.
