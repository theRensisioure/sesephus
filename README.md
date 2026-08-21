# Sesephus — a voice journal that notices drift

**Version 0.1.0 (prerelease)** · public repo [`theRensisioure/sesephus`](https://github.com/theRensisioure/sesephus).

**Sesephus** is an offline-first voice journal that notices when you're drifting —
from your sleep, your mood, your own baseline — before you do. You talk to it;
it transcribes locally, scores the entry (ETDI), and keeps everything on your
machine.

The Windows binary is still named `sesefus.exe`. Some docs still say Sesefus.
That is the private-tree spelling. This public cut is **Sesephus**.

Command status in this README follows [docs/CANON.md](docs/CANON.md) §2 — the
single source of truth for what is **WIRED** (works today) versus **STUB**
(prints a canned line, does nothing). Nothing below claims to work unless it does.

**Circadia** (the Zig alarm daemon under `core/sesephus/`) is **not done**.
`alarm *` is the live scheduler. `journal` / `rhythm` print stubs. Operator
door: [core/sesephus/README.md](core/sesephus/README.md). Python
`apps/journal-daemon/` is dogfood, not that Zig binary.

---

## 🎙️ The primary path: `voice.bat`

The real journal loop is the Python capture path, not the REPL:

```bash
install.bat     # once: venv, Whisper, dependencies
voice.bat       # push-to-talk journal loop
```

Talk for a minute. It transcribes (local Whisper), scores the entry, and stores
it. Inside the loop, speak the commands:

- **"review last"** — read back your last entry's score
- **"score"** — re-score everything
- **"dashboard"** — open the web dashboard (optional; needs the dev servers)
- **"goodbye"** — stop

Recordings live in `aurgio/recordings/`, transcripts and scores in `aurgio/`.
Nothing is uploaded anywhere by default. See [README-TESTERS.md](README-TESTERS.md)
for the full tester walkthrough and privacy notes.

---

## 🖥️ The REPL (`ssfs.bat`) — what actually works today

One unified executable `sesefus.exe` (built by `build.zig`, launched by
`ssfs.bat`); role chosen at first run and re-spawned with `--role host|client`.
There is no `host.exe` / `client.exe`.

```bash
ssfs.bat        # builds via zig build, then starts the REPL
```

Syntax is space-separated: first token = module, second = subcommand
(`group create`, `alarm list`, `vault ingest-archive`).

### Wired commands (real logic runs)

| Command | What it does |
|---|---|
| `status` | Current engine state |
| `alarm schedule\|group\|list\|toggle\|bulk\|interval\|adjust` | The live scheduler — feeds the 50 ms Timekeeper thread |
| `group create\|list\|rename\|edit\|delete` | Alarm-group CRUD |
| `lead qualify` | Spawns `python tools/qualify_post.py …` |
| `aytree open\|map\|tree\|serve\|status` | Suite **derivation map** (AyTree) — spawns `tools/aytree_launch.py` |
| `tree` | Alias of `aytree` |
| `vault ingest-archive` | Spawns `python tools/ingress_memos.py` |
| `dialogue start\|review [appliance]` | Dialogic journal loop with spoken output |
| `backup [dest]`, `exit`, `help` | Utility |
| `--read-vault`, `--extract <idx> <out.wav>` | Host flags: inspect / extract vault audio |

**AyTree** is the suite Version Control / directory-lineage module (sibling
checkout). Quick open without the REPL: `aytree.bat` or
`python tools/aytree_launch.py open`. Set `AYTREE_ROOT` or `aytree_root` in
`sesefus.config.json` if it is not a sibling of this repo. See
[docs/CANON.md](docs/CANON.md) §7.

### Not wired yet (honest list)

These commands currently **print a canned line and do nothing**. Do not build
workflows on them; each has a real alternative or a deferral (CANON §2, and the
"End the stubs" plan tracks their fate):

| Stub | Use instead |
|---|---|
| `journal record\|review\|prompt` | **`voice.bat`** — the real journal path |
| `rhythm *` | **`alarm …`** — the real scheduler |
| `stoic *` | Deferred; voice journal + manual reflection for now |
| `lead mine\|feed` | Deferred; only `lead qualify` is wired |
| `vault status\|backup\|audit` | Deferred; `--read-vault` inspects the vault |

### Global flags

- `--production` — strict safety mode (honored)
- `--dry-run` / `-n` — simulate without executing (honored)
- `--help` / `-h` — context help
- `--json`, `--expert` — **parsed but currently inert**; reserved, not usable yet

---

## 🔐 Vault

Voice data is ingested into an encrypted local database (`sesephus_vault.db`,
ChaCha20-Poly1305). Default location `V:\sesephus_vault.db`, falling back to
`./sesephus_vault.db`; override with `--vault <path>`. Known caveat: the vault
password is currently a hardcoded default (issue #63) — operator-set passwords
are a to-do, not a feature.

---

## ⚙️ Building

```bash
# Windows: batch wrapper runs zig build and dispatches
ssfs.bat <args>

# Anywhere: build directly (Zig 0.16)
cd core/sesephus && zig build
```

For the machine-readable workspace layout see `docs/manifest.json`; architecture
and module boundaries in `overallreadmee.md`; command reference in
[docs/CLI.md](docs/CLI.md) (stale — CANON §2 arbitrates); progress in
[ROADMAP.md](ROADMAP.md).
