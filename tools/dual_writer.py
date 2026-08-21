#!/usr/bin/env python3
"""Archive-first dual append: archive.db -> dimensional.db clip rows."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from archive_schema import ARCHIVE_ROOT, DIMENSIONAL_DB, ensure_layout, init_databases, sha256_exists

CLIP_WINDOWS_MS = (300, 700, 900)
AUDIO_EXT = {".wav", ".m4a", ".mp3", ".ogg", ".flac", ".aac"}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def entry_id_from_path(path: Path) -> str:
    stem = re.sub(r"[^a-zA-Z0-9]+", "-", path.stem.lower()).strip("-")
    return f"aje-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{stem[:12] or uuid.uuid4().hex[:12]}"


def normalize_wav(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-i", str(src),
        "-ac", "1", "-ar", "16000", "-vn", str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def mock_transcript(path: Path) -> str:
    return f"[mock transcript for {path.name}]"


def gauge_intent(text: str) -> tuple[float, dict]:
    text_l = text.lower()
    task = 1.0 if any(w in text_l for w in ("todo", "need to", "must", "schedule")) else 0.1
    mood = 0.5 if any(w in text_l for w in ("feel", "anxious", "happy", "tired")) else 0.2
    score = min(1.0, max(0.0, (task + mood) / 2))
    axes = {
        "topic": 0.5,
        "mood": mood,
        "task": task,
        "narrative_phase": 0.4,
        "prosody": 0.3,
    }
    return score, axes


def write_manifest(entry_id: str, src: Path, digest: str, raw_path: Path, norm_path: Path, transcript: str) -> Path:
    manifest = {
        "schemaVersion": "heydhd.audio-journal-entry.v0",
        "entryId": entry_id,
        "source": {
            "sourcePath": str(src),
            "sha256": digest,
        },
        "audio": {
            "copiedRawPath": str(raw_path),
            "normalizedPath": str(norm_path),
        },
        "transcript": {
            "status": "complete" if transcript else "pending",
            "text": transcript,
        },
        "ingestion": {
            "ingestedAtUtc": datetime.now(timezone.utc).isoformat(),
            "pipelineVersion": "dual-writer-0.1",
        },
    }
    out = ARCHIVE_ROOT / "manifests" / f"{entry_id}.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out


class DualWriter:
    def __init__(self, root: Path | None = None, dry_run: bool = False):
        self.root = ensure_layout(root)
        self.archive_db, self.dim_db = init_databases(self.root)
        self.dry_run = dry_run

    def ingest_file(self, src: Path, limit_check: bool = True) -> int | None:
        if not src.is_file() or src.suffix.lower() not in AUDIO_EXT:
            return None
        digest = file_sha256(src)
        existing = sha256_exists(self.archive_db, digest)
        if existing is not None:
            return existing

        entry_id = entry_id_from_path(src)
        raw_dest = self.root / "raw" / f"{entry_id}{src.suffix.lower()}"
        norm_dest = self.root / "normalized" / f"{entry_id}.wav"

        if self.dry_run:
            print(f"[dry-run] would ingest {src} -> {entry_id}")
            return None

        shutil.copy2(src, raw_dest)
        try:
            normalize_wav(src, norm_dest)
        except (subprocess.CalledProcessError, FileNotFoundError):
            if src.suffix.lower() == ".wav":
                shutil.copy2(src, norm_dest)
            else:
                raise

        transcript = mock_transcript(norm_dest)
        transcript_path = self.root / "transcripts" / f"{entry_id}.json"
        transcript_path.write_text(json.dumps({"text": transcript, "entryId": entry_id}, indent=2), encoding="utf-8")

        with sqlite3.connect(self.archive_db) as conn:
            cur = conn.execute(
                """
                INSERT INTO archive_records
                (entry_id, sha256, source_path, raw_path, normalized_path, transcript_status, ingest_source)
                VALUES (?, ?, ?, ?, ?, 'complete', 'historical')
                """,
                (entry_id, digest, str(src), str(raw_dest), str(norm_dest)),
            )
            archive_seq = cur.lastrowid

        with sqlite3.connect(self.dim_db) as conn:
            for clip_index, window_ms in enumerate(CLIP_WINDOWS_MS):
                fragment = transcript[: max(16, window_ms // 50)]
                score, axes = gauge_intent(fragment)
                conn.execute(
                    """
                    INSERT INTO dimensional_clips
                    (archive_seq, clip_index, window_ms, transcript_fragment, end_intent_gauge, intent_axes_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (archive_seq, clip_index, window_ms, fragment, score, json.dumps(axes)),
                )

        write_manifest(entry_id, src, digest, raw_dest, norm_dest, transcript)
        print(f"[ingest] archive_seq={archive_seq} entry={entry_id} src={src.name}")
        return archive_seq