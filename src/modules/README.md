# Modules

Pluggable self-help modules. Each exposes `Config` + `start(allocator, config)`.

| Module | Status |
|--------|--------|
| `alarms/` | Planned — extract from `core/sesephus` |
| `capture/` | Planned — AlarmConf 30/60/90s |
| `memos/` | Planned — dual DB + ingest queue |

`music_player` lives at `src/music_player.zig` (stable reference — not under this dir until wired).

## External suite modules (not under this dir)

| Module | Role | Entry |
|--------|------|--------|
| **AyTree** | Version Control / derivation map (sibling repo) | `aytree.bat` · `tools/aytree_launch.py` · REPL `aytree open` |
| **LeadLogic** | Employment / lead qualify | `lead qualify` · external engine |

See `docs/CANON.md` §7 for attention rules and path resolution.