# ETDI — Emotional Time Density Index (v1)

Turns raw voice memos into a single trendable number for perceptual time bias,
with no manual self-ratings.

```
ETDI = √(valence² + arousal² + salience²) / (√3 × duration_minutes)
```

- **valence** −1.0 … +1.0 — negative to positive tone
- **arousal** 0.0 … 1.0 — calm to intense activation
- **salience** 0.0 … 1.0 — personal significance / emotional charge
- **duration_minutes** — actual recording length (3-second floor)

The memo is a point in 3-D emotion space; ETDI is its distance from neutral,
per minute, normalized so a one-minute memo tops out at 1.0. Any single
strong axis registers on its own (a calm-but-significant moment still
scores), and with no history it is the state metric the future drift layer
(see `DRIFT.md`) collapses back to. Flag threshold defaults to **0.30**.
Entries with unknown duration are reported UNSCORED — never inflated
through the ratio.

Higher ETDI = denser emotional signal per unit time → stronger candidate for
subjective time distortion (stretched, compressed, or "heavy" in memory).

## Pipeline (voice memo → number)

1. **Record** — memo lands as audio + `aurgio/transcript/*.json` manifest
   (`heydhd.audio-journal-entry.v0`). Duration and Whisper segment timestamps
   give words/sec, pause count, and total pause time.
2. **Transcribe** — local Whisper (`base`).
3. **Infer** — locked system prompt + strict JSON schema
   (`tools/etdi_inference.py`) against Ollama (default, local-first) or the
   xAI Grok API (`--backend grok`, needs `XAI_API_KEY`). Temperature 0,
   schema-enforced output, clamped on parse.
4. **Score + vault** — ETDI computed and upserted into `etdi_scores`
   (`etdi.db`, next to the archive DBs; `SESEFUS_ETDI_DB` overrides). The
   manifest also gets an `etdi` block so the score lives beside the memo.
5. **Surface** — dashboard server exposes `/api/etdi/trend`, `/api/etdi/flags`,
   `/api/etdi/entries`; the React dashboard has an **ETDI** page (daily trend
   bars + high-density flag table).

## Usage

```bash
# Score all manifests that have transcript text (Ollama on localhost:11434)
python tools/etdi_pipeline.py --scan

# One wav, end to end (Whisper + Ollama)
python tools/etdi_pipeline.py --wav path/to/memo.wav

# Cloud inference instead of local
python tools/etdi_pipeline.py --scan --backend grok

# No model at all (offline lexical gauge, confidence pinned low) — smoke tests
python tools/etdi_pipeline.py --scan --backend heuristic

# Then look at it
python dashboard/dashboard_server.py         # port 3001
# dashboard UI → sidebar → ETDI
```

Env knobs: `SESEFUS_OLLAMA_URL`, `SESEFUS_OLLAMA_MODEL`, `SESEFUS_XAI_MODEL`,
`SESEFUS_ETDI_DB`, `XAI_API_KEY`.

## v2 (later, deliberately not in v1)

- Local SER (SenseVoice / emotion2vec) probabilities injected into the prompt
  for true audio + text fusion.
- Raw audio features stored beside the JSON.
- Occasional self-validation on high-ETDI moments to calibrate.
