# Image Sieve — screenshots into the same knowledge graph as text

A branch of `shredder/sieve.py`. Where the text sieve shreds files into
paragraph/block `DebrisChunk`s, `shredder/image_sieve.py` shreds **Windows
screenshots** by asking a vision-capable model to comprehend what's on
screen — the app context and the *abstract notion* the screen represents,
not a literal OCR dump.

Each screenshot becomes one `DebrisChunk`, identical in shape to text/code
chunks, so it flows through the exact same downstream pipeline with zero
changes to `utils/forge.py` or `docs/GUIDE_Vector_Engagement.md`:

```
screenshot → vision model (locked prompt + JSON schema) → synthesis paragraph
           → DebrisChunk → ingest/debris_shards.jsonl → Forge (nomic-embed-text)
           → ingest/vector_shards.jsonl → semantic search
```

The `content` field (what gets embedded) is the model's `synthesis` — a
40–80 word natural-language paragraph. The full structured reading
(`app_context`, `abstract_notion`, `concepts`, `confidence`, the image's own
sha256) rides along in `metadata` for programmatic use later.

## Why abstract notion, not OCR

A literal transcript of on-screen text is cheap but shallow — it tells you
*what the pixels say*, not *what you were doing*. The locked prompt asks the
model to name the app/window, then infer the underlying task or idea, the
same way a person glancing at your shoulder would describe it: "debugging a
Zig build error" rather than "error: expected type expression, found ';'".

## Usage

```bash
# Local-first (Ollama on your 5080; pull a vision model first, e.g.
# `ollama pull llama3.2-vision`)
python shredder/image_sieve.py

# Cloud vision instead
python shredder/image_sieve.py --backend grok

# No model at all — smoke test the scan/dedup/ship plumbing
python shredder/image_sieve.py --backend stub --root path/to/screenshots

# Specific folder(s), not the default Windows screenshot locations
python shredder/image_sieve.py --root "D:\Clippings"

# Then vectorize exactly like text/code shards (unchanged)
python utils/forge.py
```

Screenshots are deduped by the **image's own sha256** in
`ingest/image_sieve_state.json`, so re-running the sieve skips anything
already read — screenshots don't change, and vision calls aren't free.
Pass `--force` to re-read anyway (e.g. after improving the prompt).

Output defaults to `ingest/debris_shards.jsonl` — the same file `sieve.py`
ships to — so a plain `python utils/forge.py` picks up screenshots alongside
text and code with no extra step. Use `--output` to keep them in a separate
file instead.

## Env knobs

`SESEFUS_OLLAMA_URL`, `SESEFUS_OLLAMA_VISION_MODEL` (default
`llama3.2-vision`), `SESEFUS_XAI_URL`, `SESEFUS_XAI_VISION_MODEL` (default
`grok-2-vision-1212`), `XAI_API_KEY`.

## Backends

- **ollama** (default) — local-first, same posture as `tools/etdi_pipeline.py`.
- **grok** — xAI vision API, `response_format: json_schema`, strict.
- **stub** — no model, no network. Reads file name/size only, ships a
  zero-confidence placeholder chunk. Exists purely to exercise the scan →
  dedup → ship path without a vision backend on hand.
