# Sesephus — Canonical Reference (One Language)

> The single source of truth for **how this public repo describes itself**: names,
> what actually ships vs. what's staged, the ETDI metric, ports, and the storage
> model. Every doc, cheat sheet, showcase artifact, and dashboard string should
> conform to this file. Where a claim here and a claim elsewhere disagree, **this
> file wins** — or this file is wrong and should be fixed first, then the rest
> re-derived from it.
>
> This tree is the **public lineage/reference repository**
> (`theRensisioure/sesephus`), not the supported Voice capture product.
> Command-status rows below describe retained code. It is not API docs —
> see `docs/CLI.md`, `docs/ETDI.md`, `docs/DRIFT.md` for depth.

---

## 1 · The name map

Three spellings are alive in the tree at once. This is the intended map;
everything else is drift.

| Term | What it is | Where it's correct |
|---|---|---|
| **Sesephus** | **This public lineage/reference repository.** Retained journal, alarm, vault, and UI history. | All new prose, headings, this GitHub |
| **Sesefus** | Private-tree spelling (other mouth). Binary is still `sesefus.exe`. | Binary filename, leftover docs, `ssfs.bat` launch |
| **Neurialab** | The company / umbrella. | Company-level prose only |
| **ssfs** | The CLI wrapper (`ssfs.bat` → `sesefus.exe`) **and** the config-driven storage layer (`ssfs/`, `drive-mapping.json`). A layer *of* this product. | CLI invocation, storage subsystem |
| **sesefhus** | A third spelling, used **only** as the archive-folder name. It is *load-bearing* — it matches `drive-mapping.json` `archiveRoot`. **Do not "fix" it** without a coordinated migration. | `Archive\sesefhus` paths only |

Load-bearing **code** tokens (changing them is a migration, not a copy-edit):
directory `core/sesephus/`, vault file `sesephus_vault.db`, DB magic `SESEPHUS`,
default path `V:\sesephus_vault.db`, and the Windows binary `sesefus.exe`.

**There is no three-tier `ssfs ⊂ sesefus ⊂ sesephus` nesting and no future
"magnum opus" shell.** Nested-shells is wreckage. Do not revive it.

Repo slug: **`theRensisioure/sesephus`**. Not `Zychs/sesefus` (private product).
Not `theRensisioure/sesefus` (CSS lighthouse / doctrine preview — different repo).

---

## 2 · Retained command status

The two cheat sheets contradict each other here; this is the arbitration, read
from the retained Zig handlers. These labels describe code reachability, not a
claim that Sesephus is the current capture product. Use exactly three status
words project-wide.

- **WIRED** — real logic runs today.
- **STUB** — the handler only prints a canned line (`_ = allocator; _ = io;`). No effect.
- **DEAD** — implemented but *unreachable*; the dispatcher never routes to it.

| Command | Status | Evidence |
|---|---|---|
| `status` | **WIRED** | host.zig |
| `journal record\|review\|prompt` | **STUB** | commands/journal.zig:4-16 (print only) |
| `rhythm schedule\|status\|next` | **STUB** — `status` prints hardcoded `ALIGNED`, `next` prints `4 hours` | commands/rhythm.zig:4-17 |
| `stoic daily-reflection\|virtue-check\|obstacle` | **STUB** | commands/stoic.zig:4-17 |
| `lead qualify` | **WIRED** — spawns `python tools/qualify_post.py …` | commands/lead.zig:40-84 |
| `lead mine\|feed` | **STUB** | commands/lead.zig:92-116 |
| `aytree open\|map\|tree\|serve\|status` | **WIRED** — spawns `python tools/aytree_launch.py …` | commands/aytree.zig |
| `tree` | **WIRED** — alias of `aytree` | host.zig dispatch |
| `vault ingest-archive` | **WIRED** — spawns `python tools/ingress_memos.py` | commands/vault.zig:56-68 |
| `vault status\|backup\|audit` | **STUB** | commands/vault.zig:44-72 |
| `group create\|list\|rename\|edit\|delete` | **WIRED** — in-memory CRUD | host.zig:2129-2290 |
| `alarm schedule\|group\|list\|toggle\|bulk\|interval\|adjust` | **WIRED** — the live scheduler; feeds the 50 ms Timekeeper thread | host.zig:1748-2127, 711-774 |
| `backup [dest]`, `exit`, `help` | **WIRED** | host.zig |
| `--read-vault`, `--extract <idx> <out.wav>` | **WIRED** (host flags) | host.zig:162-411 |

**`alarm` is not legacy.** It is the real, current scheduler. The old standalone
`core/alarm_engine.zig` artifact was removed in #67 (unwired, superseded by the
live handler in `host.zig`).

**REPL syntax is space-separated**, first token = module, second = subcommand:
`group create`, `alarm group`, `vault audit`. The **underscore forms** in the startup
banner (`group_create`, `alarm_group`, `vault_audit`) are **stale** and resolve to
`Unknown module`. Banner should be regenerated to the space forms.

**Binary:** one unified executable `sesefus.exe` (built by `build.zig`, launched by
`ssfs.bat`), role chosen at first run (stdin prompt → `runtime.json`) and re-spawned
with `--role host|client`. **There is no `host.exe` / `client.exe`.**

Global flags `--production`, `--dry-run`/`-n` are honored. `--json` and `--expert`
are **parsed but currently inert** (reserved) — don't advertise them as working.

---

## 3 · ETDI — the one metric

**Emotional Time Density Index.** One number per memo. This is the flagship figure in
the showcase; it must be stated identically everywhere.

```
ETDI = √(valence² + arousal² + salience²) / (√3 × duration_minutes)
```

- Euclidean **norm**, not a product. A one-minute memo tops out at 1.0.
- **Flag threshold: 0.30.** (`etdi_store.py:128`, `dashboard_server.py:128,253`, `docs/ETDI.md:19`.)
- **Unknown/zero duration → UNSCORED** (`compute_etdi` returns `None`). It does **not**
  divide by the 3-second floor and inflate. The `MIN_DURATION_MINUTES = 0.05` (3 s)
  floor is a lower-bound clamp applied **only when a duration is already known**.
- Implemented at `tools/etdi_inference.py:180-181`; matches `docs/ETDI.md`.

**Superseded — purge on sight:** the old product form `(|valence| × arousal ×
salience) / minutes` at threshold **0.15**. It survives only in the *Whole Machine*
artifact, `EtdiPanel.jsx:53`, and `DRIFT.md:84`. Recalibration to the norm form @0.30
landed in **PR #30**.

**Inference backends are two separate systems — never conflate them:**

| Purpose | Engine | Default model |
|---|---|---|
| ETDI emotion inference | Ollama (local) / Grok (xAI cloud) / `heuristic` (offline lexical, confidence 0.2) | `qwen2.5:7b-instruct` |
| `lead qualify` relevance | local vLLM OpenAI endpoint (`LOCAL_LLM_URL`, default `:8000`) | `Crownelius/Crow-9B-HERETIC-4.6` |
| Transcription | Whisper | `base` |

`--backend` values are exactly `ollama` (default) · `grok` · `heuristic`. "lexical
fallback" is a description, not a flag value.

Row-id prefixes: `aje-*` = audio-journal-entry manifests; `wav-*` = memos scored
directly from a `.wav` with no manifest. `aje-test-*` / `aje-demo-*` are hand-made
fixtures, not pipeline output.

---

## 4 · Runtimes & ports (the Fleet)

Three runtimes, supervised as one unit by `fleet.bat` → `tools/fleet.ps1`.

| Runtime | Role | Start | Port(s) |
|---|---|---|---|
| **Engine** (Zig) | Host daemon + edge clients; vault, alarms, TCP protocol | `ssfs.bat --role host` | **TCP 5000** (clients) + **HTTP 3000** (embedded dashboard `GET /` + `/api/status`) |
| **Bridge** (Python) | FastAPI: Whisper transcribe, ETDI API, `/api/machine` | `python dashboard/dashboard_server.py` | **3001** |
| **Glass** (React/Vite) | The face; ETDI page, shipments | `cd dashboard/ui && npm run dev` | **5173** (proxies `/api` → 3001) |

- The Engine's **HTTP 3000** serves the embedded `dashboard.html` and `/api/status`;
  the Bridge polls it there. Port 3000 is easy to forget — include it.
- **`127.0.0.1:3001/` is a 404** — the Bridge is API-only. The UI is Glass at **:5173**.
- The vault is a **file**, not a service — it has no port. Don't label a vault stage
  "port 3000".

---

## 5 · Capture path

- **Current supported Voice:** Desktop Clippers at
  `C:\Users\bardw\Desktop\corection-goald\journal-clip`. It owns microphone,
  capture, Whisper transcription, tape, shredding, and cue projection.
- **Historical and unsupported:** `voice.bat` → `tools/voice.py`. The files
  remain unchanged for lineage; they are not current tester or launch guidance.
- **Reference implementation:** the Zig edge client via WinMM (`client.zig`
  `record_audio` → `audio_record.zig` `waveIn`) streaming WAV over TCP.

Clippers remains external. Do not import, vendor, submodule, or launch it from
this repository. Artifact Scanner is optional post-capture tooling, never a
requirement for Voice.

---

## 6 · Storage & vault

- **Default vault:** `V:\sesephus_vault.db`, falling back to `./sesephus_vault.db`
  when the drive/dir is unreachable. Overridable with `--vault <path>`. (host.zig:51.)
- **Encryption:** ChaCha20-Poly1305 AEAD; key derivation PBKDF2-HMAC-SHA256
  (10 000 iterations, 32-byte key). (crypto.zig.)
- **Known caveat (be honest in the deck, don't hide it):** the vault password is a
  hardcoded literal in `host.zig:198`
  (`"sesephus_default_vault_secure_password_string_2026"`). Operator-set passwords are
  a to-do, not a feature. The `crypto.zig` RNG is also a weak time-seeded PRNG.
- **`ssfs/drive-mapping.json` is the *declared* single source of truth for drive
  letters** (vault `V:`, coldArchive `E:`, worktrees `T:`). Honored by the JS/Python
  tools; **not yet enforced in the Zig layer** (`host.zig`, `runtime_config.zig`,
  `wav_db.zig` still hardcode `V:`/`E:`). Describe it as "declared SSOT, native layer
  not yet migrated," not as absolute.
- **`tools/ssfs_config.py` and `tools/sesefus_config.py` are NOT duplicates** and
  neither should be deleted: `ssfs_config.py` resolves drive letters / archive root
  from `drive-mapping.json`; `sesefus_config.py` loads app settings (dirs, backend,
  models) from `sesefus.config.json` (generated on demand). Four modules import the
  latter.

---

## 7 · Suite modules (siblings & attention)

Sesephus is the **public lineage/reference repository** for the journal, alarms,
vault, bridge, and glass experiments. Related current tools live as external
checkouts or optional paths — not as submodules that must be vendored here.

| Module | Role | Status | How to open |
|---|---|---|---|
| **Sesephus** (this repo) | Public lineage/reference: retained alarms, vault, bridge, Glass, and historical capture code | **REFERENCE** | No supported Voice door; reference builds only |
| **Desktop Clippers** (external) | Sole supported Voice capture: mic → Whisper → tape → shred → cue projection | **CURRENT** | `C:\Users\bardw\Desktop\corection-goald\journal-clip` |
| **AyTree** | Suite **Version Control / derivation map** — directory lineages, notes, spatial structure. **Not** full git VCS. Dyslexia-first. | **WIRED** (external) | `aytree.bat` · `python tools/aytree_launch.py open` · REPL `aytree open` |
| **LeadLogic-Engine** | Employment / lead domain (qualify, mine). **Keep**; not the structure/VC lead. | **WIRED** (external + `lead qualify`) | `lead qualify` spawns `tools/qualify_post.py` |

**Attention rule:** day-to-day “open this first” for *how work folders relate*
is **AyTree**, not LeadLogic. LeadLogic remains the lead domain for *income /
qualification*. Do not delete LeadLogic or collapse it into AyTree.

**AyTree resolution (no suite path roster in product logic):**

1. `AYTREE_ROOT` env  
2. `sesefus.config.json` → `aytree_root`  
3. Sibling of this repo: `../AyTree` or `../aytree`  

Port: `aytree_port` (default **8000**) — same default as local vLLM for
`lead qualify`; if both run, set `aytree_port` or move vLLM. Surfaces:
`/derivation` (lineage map), `/` (tree tool). Design: AyTree
`docs/specs/derivation-map-v1.md`.

**CLI (this binary):**

| Command | Status | Evidence |
|---|---|---|
| `aytree open\|map\|tree\|serve\|status` | **WIRED** | `commands/aytree.zig` → `tools/aytree_launch.py` |
| `tree` (alias of `aytree`) | **WIRED** | host.zig dispatch |

---

## 8 · Repo meta

- **File count:** the reconciliation review branch has **275 tracked files**:
  212 in the reference tree and 63 under `archival/`. Earlier 226, 236, and
  245 figures are dated pre-retirement snapshots.
- The *Branch Audit* and *Session Ledger* artifacts are **dated historical records**.
  Align their *terminology* to this canon; do **not** rewrite their event history.
  (For reference: the `voice-control-integration-635p5x` branch was merged via **PR
  #30**; the norm formula and `voice.py` shipped with it.)

---

## 9 · Stale spots to purge (checklist)

Everything below contradicts §1–§8 and should be fixed at the source so the artifacts
can be regenerated cleanly.

- [ ] `dashboard/ui/src/components/EtdiPanel.jsx:53` — **live UI** still prints the old
      product formula. **Highest priority: it's on screen in the demo.**
- [ ] `docs/DRIFT.md:84` — still says `0.15`; should be `0.30`.
- [x] `README.md:1` — identifies Sesephus as the public lineage/reference
      repository and points current Voice to external Desktop Clippers.
- [ ] `overallreadmee.md:1` — "Arcadium & Circadia (AuraEngine / Sesephus Suite)";
      pre-rebrand naming.
- [ ] `docs/manifest.json` — points at phantom `core/sesephus/circadia.zig` &
      `arcadium.zig` (neither exists); version `0.1.0`, repo `t:/sesephus-database`
      all stale.
- [ ] `host.zig:266-282` — startup banner advertises underscore commands + the DEAD
      vault ops as if usable.
- [ ] `tools/archive_schema.py:1` — docstring says `T:/Archive/sesefhus`; the code now
      derives `E:` from `drive-mapping.json`.
- [x] `core/alarm_engine.zig` and the second `handleVaultCommand` in `host.zig` —
      removed (#67).

---

## 9 · The six artifacts, at a glance

| Artifact | Verdict | Fix priority |
|---|---|---|
| **CLI Cheatsheet** (01) | Most accurate on real-vs-stub. Fixes are naming (`host.exe`→unified `sesefus`, `Sesephus`→`Sesefus`, `zychs`→`Zychs`) + "alarm is not legacy" + "DEAD not 'not implemented'". | Med |
| **Command Cheatsheet** (02) | Systematically over-optimistic — marks stubs "wired," underscore syntax, inverts legacy. Its own closing "Stub gap" note is the correct part. | **High** |
| **drift architecture** (03) | Conceptual; preserve the philosophy. Only the `magnum opus` nesting and the non-canon drift-domain list need alignment. | Med |
| **Branch Audit** (04) | Accurate history — don't rewrite. One live error: "delete `sesefus_config.py`" is wrong (would break 4 importers). | Low |
| **Session Ledger** (05) | Accurate for its date. Align stale status ("not yet in code" → shipped) + the false null-duration "inflates" trap. | Low |
| **The Whole Machine** (06) | Flagship showcase — but carries the wrong ETDI formula @0.15, the interactive widget computes `0.1820` (product) instead of `≈0.36` (norm), and shows `journal record` as working. | **High** |
