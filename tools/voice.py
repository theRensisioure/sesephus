#!/usr/bin/env python3
"""Sesefus voice loop — push-to-talk control and journaling. The 0.9.3 path.

Just speak. Short utterances (five words or fewer) are commands:

    status                     is anything alive? how many memos scored?
    review last                read back the last scored entry
    score / scan               score every manifest with a transcript
    dashboard                  open the web dashboard
    quit / exit / goodbye      stop the loop

Anything longer is a journal entry: recorded, transcribed locally with
Whisper, written to aurgio/transcript/ as a full manifest (transcript,
segments, AND duration — voice-born memos never hit the duration trap),
then scored with ETDI on the spot.

Push-to-talk is deliberately boring: Enter to start, Enter to stop.

Test hooks (how this gets verified without a microphone):
    --file memo.wav     skip the mic, run the identical post-capture path
    --say "text"        skip audio and Whisper entirely (use with --duration)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import types
import urllib.request
import wave
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

import etdi_pipeline
import etdi_store
from sesefus_config import load_config

CFG = load_config()
SAMPLE_RATE = 16000
COMMAND_MAX_WORDS = 5

QUIT_WORDS = {"quit", "exit", "goodbye", "stop"}


# ---------- capture ----------

def record_ptt(recordings_dir: Path) -> Path | None:
    """Enter to start, Enter to stop. Returns the saved wav path."""
    import sounddevice as sd  # heavy/hardware import kept out of module load

    input("  [enter] to start recording... ")
    frames: list[bytes] = []

    def callback(indata, _frames, _time, status):
        if status:
            print(f"  [mic] {status}", file=sys.stderr)
        frames.append(bytes(indata))

    stream = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                               dtype="int16", callback=callback)
    with stream:
        input("  recording — [enter] to stop... ")

    if not frames:
        print("  [mic] nothing captured")
        return None

    recordings_dir.mkdir(parents=True, exist_ok=True)
    wav_path = recordings_dir / f"{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(b"".join(frames))
    return wav_path


def wav_duration_seconds(wav_path: Path) -> float | None:
    try:
        with wave.open(str(wav_path), "rb") as w:
            rate = w.getframerate()
            return round(w.getnframes() / rate, 2) if rate else None
    except (wave.Error, OSError):
        return None


def transcribe(wav_path: Path) -> tuple[str, list[dict]]:
    import whisper

    model = whisper.load_model(CFG["whisper_model"])
    result = model.transcribe(str(wav_path))
    segments = [
        {"start": s.get("start"), "end": s.get("end"), "text": s.get("text", "")}
        for s in result.get("segments", [])
    ]
    return result.get("text", "").strip(), segments


# ---------- manifest + scoring ----------

def write_manifest(transcript_dir: Path, wav_path: Path | None, transcript: str,
                   segments: list[dict], duration: float | None) -> Path:
    now = datetime.now(timezone.utc)
    digest = (etdi_pipeline.file_sha256(wav_path) if wav_path
              else hashlib.sha256(transcript.encode()).hexdigest())
    entry_id = f"aje-{now.strftime('%Y%m%d-%H%M%S')}-{digest[:10]}"
    manifest = {
        "schemaVersion": "heydhd.audio-journal-entry.v0",
        "entryId": entry_id,
        "mode": "voice-ptt",
        "source": {
            "sourcePath": str(wav_path) if wav_path else "spoken (no audio kept)",
            "sourceName": wav_path.name if wav_path else "",
            "sha256": digest,
            "sizeBytes": wav_path.stat().st_size if wav_path else 0,
        },
        "audio": {
            "capturedAtUtc": now.isoformat(),
            "durationSeconds": duration,
            "sampleRateHz": SAMPLE_RATE if wav_path else None,
            "channels": 1 if wav_path else None,
            "originalExtension": wav_path.suffix if wav_path else "",
            "copiedRawPath": str(wav_path) if wav_path else "",
        },
        "transcript": {
            "status": "complete",
            "engine": f"whisper-{CFG['whisper_model']}" if wav_path else "spoken-text",
            "text": transcript,
            "segments": segments,
        },
        "ingestion": {
            "pipelineVersion": "voice-0.9.3",
            "ingestedAtUtc": now.isoformat(),
        },
    }
    transcript_dir.mkdir(parents=True, exist_ok=True)
    out = transcript_dir / f"{entry_id}.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


def score_manifest(manifest_path: Path, backend: str, model: str | None, db: Path | None) -> None:
    args = types.SimpleNamespace(backend=backend, model=model, dry_run=False)
    conn = etdi_store.connect(db)
    try:
        etdi_pipeline.process_manifest(manifest_path, args, conn)
    finally:
        conn.close()


# ---------- intents ----------

def normalize(text: str) -> list[str]:
    return [w.strip(".,!?;:'\"").lower() for w in text.split() if w.strip(".,!?;:'\"")]


def match_intent(transcript: str) -> str:
    """Short utterances are commands; anything longer is a journal entry."""
    words = normalize(transcript)
    if not words or len(words) > COMMAND_MAX_WORDS:
        return "journal"
    joined = set(words)
    if joined & QUIT_WORDS:
        return "quit"
    if "status" in joined:
        return "status"
    if "review" in joined:
        return "review"
    if joined & {"score", "scan"}:
        return "score"
    if "dashboard" in joined:
        return "dashboard"
    return "journal"


def do_status(db: Path | None) -> None:
    def ping(url: str) -> str:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return "up"
        except Exception:
            return "down"
    print(f"  dashboard api (:3001): {ping('http://127.0.0.1:3001/api/etdi/trend')}")
    print(f"  ollama (:11434):       {ping('http://127.0.0.1:11434/api/tags')}")
    conn = etdi_store.connect(db)
    try:
        entries = etdi_store.recent_entries(conn, 1)
        count = conn.execute("SELECT count(*) FROM etdi_scores").fetchone()[0]
    finally:
        conn.close()
    print(f"  scored memos in vault: {count}")
    if entries:
        e = entries[0]
        print(f"  latest: {e['entry_id']} etdi={e['etdi']} ({e['primary_emotion']})")


def do_review(db: Path | None) -> None:
    conn = etdi_store.connect(db)
    try:
        entries = etdi_store.recent_entries(conn, 1)
    finally:
        conn.close()
    if not entries:
        print("  vault is empty — speak a journal entry first")
        return
    e = entries[0]
    print(f"  {e['entry_id']}  ({(e['recorded_at_utc'] or '')[:16]})")
    print(f"  etdi {e['etdi']} · {e['primary_emotion']} · valence {e['valence']} "
          f"arousal {e['arousal']} salience {e['salience']}")


def do_score(backend: str, model: str | None, db: Path | None) -> None:
    args = types.SimpleNamespace(backend=backend, model=model, dry_run=False)
    conn = etdi_store.connect(db)
    try:
        manifests = sorted(Path(CFG["transcript_dir"]).glob("*.json"))
        scored = sum(bool(etdi_pipeline.process_manifest(m, args, conn)) for m in manifests)
        print(f"  scored {scored} of {len(manifests)} manifest(s)")
    finally:
        conn.close()


# ---------- main loop ----------

def handle_utterance(transcript: str, segments: list[dict], duration: float | None,
                     wav_path: Path | None, args) -> bool:
    """Route one utterance. Returns False when the loop should stop."""
    intent = match_intent(transcript)
    print(f"  [{intent}] \"{transcript[:70]}{'...' if len(transcript) > 70 else ''}\"")
    if intent == "quit":
        print("  goodbye — the vault remembers.")
        return False
    if intent == "status":
        do_status(args.db)
    elif intent == "review":
        do_review(args.db)
    elif intent == "score":
        do_score(args.backend, args.model, args.db)
    elif intent == "dashboard":
        print(f"  opening {CFG['dashboard_url']}")
        webbrowser.open(CFG["dashboard_url"])
    else:  # journal
        manifest = write_manifest(Path(CFG["transcript_dir"]), wav_path,
                                  transcript, segments, duration)
        print(f"  [journal] {manifest.name}")
        score_manifest(manifest, args.backend, args.model, args.db)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Sesefus push-to-talk voice loop")
    parser.add_argument("--file", type=Path, help="wav file instead of the mic (test hook)")
    parser.add_argument("--say", help="text instead of audio+whisper (test hook)")
    parser.add_argument("--duration", type=float, help="duration seconds for --say")
    parser.add_argument("--backend", choices=("ollama", "grok", "heuristic"),
                        default=CFG["backend"])
    parser.add_argument("--model", help="override inference model")
    parser.add_argument("--db", type=Path, help="override etdi.db path")
    args = parser.parse_args()

    if args.say is not None:
        handle_utterance(args.say, [], args.duration, None, args)
        return 0
    if args.file:
        duration = wav_duration_seconds(args.file)
        transcript, segments = transcribe(args.file)
        if not transcript:
            print("  [skip] empty transcript")
            return 1
        handle_utterance(transcript, segments, duration, args.file, args)
        return 0

    print("==================================================")
    print("  SESEFUS VOICE — just speak. short = command,")
    print("  long = journal. say 'goodbye' to stop.")
    print("==================================================")
    recordings_dir = Path(CFG["recordings_dir"])
    while True:
        try:
            wav_path = record_ptt(recordings_dir)
        except KeyboardInterrupt:
            print("\n  goodbye — the vault remembers.")
            return 0
        if wav_path is None:
            continue
        duration = wav_duration_seconds(wav_path)
        print("  [whisper] transcribing ...")
        transcript, segments = transcribe(wav_path)
        if not transcript:
            print("  [mic] heard nothing intelligible — try again")
            continue
        if not handle_utterance(transcript, segments, duration, wav_path, args):
            return 0


if __name__ == "__main__":
    sys.exit(main())
