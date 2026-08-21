#!/usr/bin/env python3
"""v1 ETDI pipeline: voice memo -> Whisper transcript -> emotion JSON -> ETDI -> vault.

Modes:
  --wav FILE          Transcribe an audio file locally with Whisper, then score it.
  --wav FILE --into-manifest M.json
                      Transcribe, backfill M.json (transcript + segments +
                      durationSeconds), then score it under its own entry id.
  --manifest FILE     Score a single aurgio manifest (uses its transcript.text).
  --scan DIR          Score every manifest in a directory (default: aurgio/transcript).

The emotion call goes to Ollama by default (--backend ollama), the xAI Grok API
with --backend grok, or a crude offline lexical gauge with --backend heuristic
(no model required; useful for smoke tests and machines without the 5080).

--dry-run reports what would be scored without calling Whisper or any model.

Entries whose duration cannot be determined are reported as UNSCORED and
skipped before any inference runs — a missing duration must never inflate
the score through the ratio.

Each score is upserted into the etdi_scores table (see etdi_store.py) and an
"etdi" block is written back into the memo's manifest JSON so the number lives
alongside the memo itself.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from etdi_inference import (
    audio_stats_from_segments,
    compute_etdi,
    infer_emotion,
    validate_emotion,
)
import etdi_store

DEFAULT_SCAN_DIR = Path(__file__).resolve().parent.parent / "aurgio" / "transcript"

NEGATIVE_WORDS = ("anxious", "angry", "afraid", "scared", "sad", "tired", "frustrated",
                  "overwhelmed", "stressed", "hopeless", "worried", "hurt")
POSITIVE_WORDS = ("happy", "grateful", "excited", "proud", "calm", "hopeful",
                  "love", "great", "amazing", "relieved")
AROUSAL_WORDS = ("!", "urgent", "now", "can't", "cannot", "need to", "must",
                 "racing", "panic", "excited", "furious")


def heuristic_emotion(transcript: str) -> dict:
    """Offline stand-in for the LLM call: crude lexical valence/arousal gauge."""
    text = transcript.lower()
    neg = sum(text.count(w) for w in NEGATIVE_WORDS)
    pos = sum(text.count(w) for w in POSITIVE_WORDS)
    aro = sum(text.count(w) for w in AROUSAL_WORDS)
    total = max(neg + pos, 1)
    valence = (pos - neg) / total if (pos or neg) else 0.0
    arousal = min(0.9, 0.2 + 0.15 * aro)
    salience = min(0.9, 0.1 + 0.2 * (neg + pos))
    return validate_emotion({
        "valence": valence,
        "arousal": arousal,
        "salience": salience,
        "primary_emotion": "negative_lean" if neg > pos else ("positive_lean" if pos > neg else "neutral"),
        "time_distortion_likelihood": min(0.9, abs(valence) * arousal + 0.1),
        "rationale": "offline lexical gauge, not a model inference",
        "confidence": 0.2,
    })


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def transcribe_wav(wav_path: Path) -> tuple[str, list[dict], float | None]:
    import whisper  # local model; heavy import kept out of module load

    model = whisper.load_model("base")
    result = model.transcribe(str(wav_path))
    segments = [
        {"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")}
        for s in result.get("segments", [])
    ]
    duration = segments[-1]["end"] if segments else None
    return result.get("text", "").strip(), segments, duration


def score_memo(entry_id: str, transcript: str, segments: list[dict],
               duration_seconds: float | None, recorded_at: str | None,
               backend: str, model: str | None) -> dict | None:
    """Return a full score record, or None when the entry is unscorable.

    The duration check runs BEFORE any model call — no inference is paid for
    an entry whose score would be meaningless anyway.
    """
    stats = audio_stats_from_segments(segments, duration_seconds)
    if not stats.get("duration_seconds"):
        return None
    if backend == "heuristic":
        emotion = heuristic_emotion(transcript)
        used_model = "lexical-gauge"
    else:
        emotion = infer_emotion(transcript, stats, backend=backend, model=model)
        used_model = model or "default"
    etdi = compute_etdi(emotion["valence"], emotion["arousal"], emotion["salience"],
                        stats.get("duration_seconds"))
    return {
        "entry_id": entry_id,
        "recorded_at_utc": recorded_at,
        "duration_seconds": stats.get("duration_seconds"),
        "words_per_second": stats.get("words_per_second"),
        "pause_count": stats.get("pause_count"),
        "pause_total_seconds": stats.get("pause_total_seconds"),
        **emotion,
        "etdi": etdi,
        "backend": backend,
        "model": used_model,
        "raw_json": json.dumps(emotion),
    }


def annotate_manifest(manifest_path: Path, data: dict, record: dict) -> None:
    """Write the etdi block into the already-parsed manifest dict and save it."""
    data["etdi"] = {
        "score": record["etdi"],
        "valence": record["valence"],
        "arousal": record["arousal"],
        "salience": record["salience"],
        "primary_emotion": record["primary_emotion"],
        "time_distortion_likelihood": record["time_distortion_likelihood"],
        "confidence": record["confidence"],
        "backend": record["backend"],
        "scoredAtUtc": datetime.now(timezone.utc).isoformat(),
    }
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def process_manifest(manifest_path: Path, args, conn) -> bool:
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[skip] {manifest_path.name}: unreadable ({exc})")
        return False
    entry_id = data.get("entryId") or manifest_path.stem
    transcript = (data.get("transcript") or {}).get("text") or ""
    segments = (data.get("transcript") or {}).get("segments") or []
    duration = (data.get("audio") or {}).get("durationSeconds")
    recorded_at = (data.get("audio") or {}).get("capturedAtUtc")
    if not transcript.strip():
        print(f"[skip] {entry_id}: no transcript text (run whisper ingest first)")
        return False
    if args.dry_run:
        print(f"[dry-run] would score {entry_id} via {args.backend}")
        return True
    record = score_memo(entry_id, transcript, segments, duration, recorded_at,
                        args.backend, args.model)
    if record is None:
        print(f"[unscored] {entry_id}: duration unknown — fill audio.durationSeconds "
              f"or transcript.segments before scoring")
        return False
    print(f"[score] {entry_id} etdi={record['etdi']} "
          f"({record['primary_emotion']}, conf={record['confidence']})")
    etdi_store.upsert_score(conn, record)
    annotate_manifest(manifest_path, data, record)
    return True


def backfill_manifest(manifest_path: Path, transcript: str, segments: list[dict],
                      duration: float | None) -> None:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data.setdefault("transcript", {})
    data["transcript"].update({
        "status": "complete",
        "engine": "whisper-base",
        "text": transcript,
        "segments": segments,
    })
    data.setdefault("audio", {})
    if duration and not data["audio"].get("durationSeconds"):
        data["audio"]["durationSeconds"] = round(duration, 2)
    manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[backfill] {manifest_path.name}: transcript + duration written")


def process_wav(wav_path: Path, args, conn) -> bool:
    if args.dry_run:
        target = f" -> backfill {args.into_manifest.name}" if args.into_manifest else ""
        print(f"[dry-run] would transcribe {wav_path.name} with whisper{target}, "
              f"then score via {args.backend}")
        return True
    print(f"[whisper] transcribing {wav_path.name} ...")
    transcript, segments, duration = transcribe_wav(wav_path)
    if not transcript:
        print(f"[skip] {wav_path.name}: empty transcript")
        return False

    if args.into_manifest:
        backfill_manifest(args.into_manifest, transcript, segments, duration)
        return process_manifest(args.into_manifest, args, conn)

    # sha8 keeps two different recordings with the same filename from colliding
    entry_id = f"wav-{wav_path.stem}-{file_sha256(wav_path)[:8]}"
    recorded_at = datetime.fromtimestamp(wav_path.stat().st_mtime, tz=timezone.utc).isoformat()
    record = score_memo(entry_id, transcript, segments, duration, recorded_at,
                        args.backend, args.model)
    if record is None:
        print(f"[unscored] {entry_id}: whisper produced no usable duration")
        return False
    print(f"[score] {entry_id} etdi={record['etdi']} "
          f"({record['primary_emotion']}, conf={record['confidence']})")
    etdi_store.upsert_score(conn, record)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Score voice memos with ETDI")
    parser.add_argument("--wav", type=Path, help="audio file to transcribe + score")
    parser.add_argument("--into-manifest", type=Path,
                        help="with --wav: backfill this manifest's transcript/duration, then score it")
    parser.add_argument("--manifest", type=Path, help="single manifest JSON to score")
    parser.add_argument("--scan", type=Path, nargs="?", const=DEFAULT_SCAN_DIR,
                        help=f"scan a manifest directory (default {DEFAULT_SCAN_DIR})")
    parser.add_argument("--backend", choices=("ollama", "grok", "heuristic"),
                        default="ollama")
    parser.add_argument("--model", help="override model name for the chosen backend")
    parser.add_argument("--db", type=Path, help="override etdi.db path")
    parser.add_argument("--dry-run", "-n", action="store_true")
    args = parser.parse_args()

    if args.into_manifest and not args.wav:
        parser.error("--into-manifest requires --wav")
    if not (args.wav or args.manifest or args.scan):
        args.scan = DEFAULT_SCAN_DIR

    conn = etdi_store.connect(args.db)
    scored = 0
    if args.wav:
        scored += process_wav(args.wav, args, conn)
    if args.manifest:
        scored += process_manifest(args.manifest, args, conn)
    if args.scan:
        manifests = sorted(Path(args.scan).glob("*.json"))
        print(f"Scanning {len(manifests)} manifest(s) in {args.scan}")
        for m in manifests:
            try:
                scored += process_manifest(m, args, conn)
            except Exception as exc:  # noqa: BLE001 — batch scoring reports per-file errors
                print(f"[error] {m.name}: {exc}")
    print(f"Done. scored={scored} dry_run={args.dry_run} db={args.db or etdi_store.default_db_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
