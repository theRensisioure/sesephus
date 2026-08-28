# Circadia — Zig alarm daemon

**Status: not done.**  
This is the alarm engine inside **Sesephus** (`theRensisioure/sesephus`). The scheduler exists. The Circadia product does not.

One binary: `sesefus.exe` (`zig build` here). Role is `--role host` or `--role client`.  
**There is no `host.exe` or `client.exe`.** Old docs and `run_demo.bat` that say otherwise are dated.

Canon for WIRED vs STUB: [`docs/CANON.md`](../../docs/CANON.md) §2. If this file and CANON disagree, CANON wins.

---

## What it is

Circadia is the **timekeeper**: schedule a cue, fire it on a connected client, optionally kick a capture.  
Sesephus is the product brand in this repo. Circadia is not a second app and not a finished shippable.

Host: HTTP `127.0.0.1:3000` (embedded `dashboard.html` + `/api/status`) and TCP **5000** (length-prefixed JSON frames to clients).  
Client: register, wait for frames, play / record / report.

---

## Honest surface (2026-08-12)

**Wired today**

- `alarm schedule | group | list | toggle | bulk | interval | adjust` — live scheduler, 50 ms Timekeeper in `host.zig`
- `group create | list | rename | edit | delete` — in-memory subgroups
- `status`, `help`, `backup`, `exit`
- `--read-vault` / `--extract` host flags
- Host↔client TCP + WAV upload path when the client actually records (WinMM on Windows; synthetic fallback elsewhere)

**Stubs (print a line, do nothing)**

- `journal record | review | prompt`
- `rhythm schedule | status | next` — `status` prints fake `ALIGNED`; `next` prints fake `4 hours`. Use `alarm`, not `rhythm`.

**Not this tree**

- Artifact Scanner is an **optional finder**, not the Circadia host or a Voice
  requirement.
- `apps/journal-daemon/` was retired from this tree. Its historical
  Python dogfood code remains in Git history and the dated vault preserve.
- `apps/record-widget/` was retired with the other duplicate/stalled surfaces.

Direction (not shipped): `plans/2026-08-12-audio-journal-zig-daemon.md`.

---

## Build and run

Zig 0.16. From this directory:

```bat
zig build
zig-out\bin\sesefus.exe --role host
zig-out\bin\sesefus.exe --role client --name laptop-01
```

First run without `--role` prompts and writes `runtime.json`. `--reset-role` clears that.

REPL (from repo root): `ssfs.bat` — same binary.

Alarm example (host REPL):

```
alarm schedule laptop-01 5 play_sound 1.5
```

Not the old `alarm laptop-01 5 record_audio 5.0` one-liner.

---

## Vault

Default path was `V:\sesephus_vault.db`; live fallback is `./sesephus_vault.db`. Override `--vault <path>`.  
Password is still a hardcoded default (issue #63) — do not document operator-set secrets as a feature.

---

## Tests

```bat
python test_integration.py
python test_circadia_advanced.py
```

These exercise the engine. Passing them does not mean Circadia is a finished product.

---

## Dated claims — do not restore

- `CLEANUP.md` / `derivation-external-view-*` — not in this folder
- Split `host.exe` + `client.exe` as the ship surface
- `journal` / `rhythm` as working circadian product commands
- Circadia “implemented” inside Artifact Scanner suite cards
- `V:\` as a required drive
