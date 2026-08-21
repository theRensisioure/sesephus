# Artifact Sieve — Gemini / Takeout chat dumps into the knowledge graph

A branch of `shredder/sieve.py` (sibling to `shredder/image_sieve.py`). Where
the text sieve shreds loose files into paragraph/block `DebrisChunk`s, and the
image sieve comprehends screenshots, **`shredder/artifact_sieve.py`** opens a
**directory of export artifacts** — Google Takeout Gemini JSON/HTML, My
Activity dumps, AI Studio applet history, and related chat-export shapes —
linearizes conversation DAGs, and ships embeddable chunks to the same
`ingest/debris_shards.jsonl` Forge path.

```
Takeout/Gemini  →  parse (mapping DAG / list / HTML)
                →  linearize conversation
                →  DebrisChunk
                →  ingest/debris_shards.jsonl
                →  Forge (nomic-embed-text)
                →  ingest/vector_shards.jsonl
```

## Why a separate sieve

Text `sieve.py` skips binaries and walks every file as loose prose. Gemini
exports are **structured graphs** (branching edits/regenerations live in a
`mapping` object), often one giant `conversations.json` or a zip of per-chat
files. Comb them with a parser that understands the dump, not a paragraph
splitter that would slice JSON keys into noise.

## Formats handled

| Shape | Notes |
|---|---|
| Takeout `conversations.json` | `conversations[]` with optional `mapping` DAG |
| Per-chat Gemini Apps JSON | Single conversation objects |
| My Activity JSON | Activity titles / products |
| AI Studio `applet_access_history.json` | Applet name + description cards |
| Mongo-style `$set.messages` | Same family as `utils/prune_chat.py` |
| HTML Takeout pages | Tag-stripped text document |
| Zip bundles | Members whose paths look like Gemini/Activity |

Mapping DAGs are linearized **leaf → root** (deepest final branch), then
reversed to chronological order — same strategy as the research note in
`research-corpus/engine/llm-sovereignty/preserving-cognitive-fidelity.md`.

## CLI

```bash
# Inventory the opened directory (scanner JSON)
python shredder/artifact_sieve.py --scan-only --root "C:\Users\…\Downloads\takeout-…\Takeout\Gemini"

# Shred whole conversations (default unit)
python shredder/artifact_sieve.py --root "…\Takeout\Gemini"

# One DebrisChunk per message turn (finer search grain)
python shredder/artifact_sieve.py --root "…\Takeout\Gemini" --unit turn

# Smoke the walk without writing
python shredder/artifact_sieve.py --root "…\Takeout\Gemini" --dry-run

# Then vectorize like every other shard
python utils/forge.py
```

Dedup state lives in `ingest/artifact_sieve_state.json` (file sha256 + unit).
Pass `--force` to re-shred after improving the parser.

Config key: `artifact_roots` in `sesefus.config.json` (list of absolute paths).
When empty, CLI defaults to existing `~/Downloads`, `~/Documents/Takeout`, etc.

## Dashboard — artifact scanner view

Shipment **Sieve** (`/shipments/sieve`) is the scanner UI:

1. Paste the path to the directory Google gave you (unzipped Takeout).
2. **Scan directory** — lists dump files, detected format, conversation/message counts, sample titles.
3. **Shred through sieve** — ships chunks to `ingest/debris_shards.jsonl`.

API (local FastAPI on :3001):

| Method | Path | Body |
|---|---|---|
| GET | `/api/sieve/defaults` | — |
| POST | `/api/sieve/scan` | `{ "root": "…", "shallow": false }` |
| POST | `/api/sieve/shred` | `{ "root": "…", "unit": "conversation"\|"turn", "force": false, "dry_run": false }` |

## Export recipe (Google)

1. [takeout.google.com](https://takeout.google.com) → Deselect all.
2. Enable **Gemini** (and/or **My Activity** filtered to Gemini if you want that shape).
3. Prefer **JSON** where offered; HTML still parses as stripped documents.
4. Unzip the email download; point the sieve at `Takeout/Gemini` (or the zip itself if member paths match).
