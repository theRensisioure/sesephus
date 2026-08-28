# Sesephus — public lineage and reference

**Version 0.1.0 (prerelease)** · [`theRensisioure/sesephus`](https://github.com/theRensisioure/sesephus)

```bash
git clone https://github.com/theRensisioure/sesephus.git
cd sesephus
```

**Sesephus** preserves the public lineage of the journal, alarm, vault, ETDI,
bridge, and dashboard experiments. It is a reference repository: retained code
may still build, but this checkout is not the supported Voice capture product.

The Windows binary is still named `sesefus.exe`. Some older files still say
Sesefus. That is private-lineage spelling. This public lineage is **Sesephus**.
The retired private checkout is not a second current product. Do not confuse
this repo with lighthouse
[`theRensisioure/sesefus`](https://github.com/theRensisioure/sesefus).

Command status in this README follows [docs/CANON.md](docs/CANON.md) §2 — the
single source of truth for what is **WIRED** (works today) versus **STUB**
(prints a canned line, does nothing). Nothing below claims to work unless it does.

**Circadia** (the retained Zig alarm daemon under `core/sesephus/`) is **not
done**. `alarm *` contains wired scheduler logic; `journal` / `rhythm` print
stubs. See [core/sesephus/README.md](core/sesephus/README.md) when studying or
building the retained implementation. The duplicate Python app surfaces have
been retired from this branch.

---

## Current Voice boundary

The sole supported Voice implementation is **Desktop Clippers** at:

```text
C:\Users\bardw\Desktop\corection-goald\journal-clip
```

That external tree owns the microphone, capture, tape, shredding, and cue
projection. This repository points to it only; it does not import, vendor,
submodule, or launch Clippers.

The retained `voice.bat` and `tools/voice.py` describe an earlier push-to-talk
path. They remain unchanged as historical evidence and are explicitly
**unsupported**. [README-TESTERS.md](README-TESTERS.md) records the retired
tester path and is not current launch guidance.

---

## Retained REPL (`ssfs.bat`) — reference behavior

One unified executable `sesefus.exe` (built by `build.zig`, launched by
`ssfs.bat`); role chosen at first run and re-spawned with `--role host|client`.
There is no `host.exe` / `client.exe`.

```bash
ssfs.bat        # builds via zig build, then starts the REPL
```

Syntax is space-separated: first token = module, second = subcommand
(`group create`, `alarm list`, `vault ingest-archive`).

### Wired commands in the retained code

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
| `journal record\|review\|prompt` | No supported in-repo replacement; use external Desktop Clippers for current Voice capture |
| `rhythm *` | **`alarm …`** — the real scheduler |
| `stoic *` | Deferred in this lineage |
| `lead mine\|feed` | Deferred; only `lead qualify` is wired |
| `vault status\|backup\|audit` | Deferred; `--read-vault` inspects the vault |

### Global flags

- `--production` — strict safety mode (honored)
- `--dry-run` / `-n` — simulate without executing (honored)
- `--help` / `-h` — context help
- `--json`, `--expert` — **parsed but currently inert**; reserved, not usable yet

---

## Retained vault implementation

Voice data is ingested into an encrypted local database (`sesephus_vault.db`,
ChaCha20-Poly1305). Default location `V:\sesephus_vault.db`, falling back to
`./sesephus_vault.db`; override with `--vault <path>`. Known caveat: the vault
password is currently a hardcoded default — operator-set passwords are a
to-do, not a feature.

---

## Reference build

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
