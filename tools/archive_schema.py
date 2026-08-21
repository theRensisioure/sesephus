"""SQLite schemas for T:/Archive/sesefhus dual-append archive."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from ssfs_config import get_archive_root

ARCHIVE_ROOT = get_archive_root()
ARCHIVE_DB = ARCHIVE_ROOT / "db" / "archive.db"
DIMENSIONAL_DB = ARCHIVE_ROOT / "db" / "dimensional.db"

ARCHIVE_DDL = """
CREATE TABLE IF NOT EXISTS archive_records (
    archive_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE,
    source_path TEXT NOT NULL,
    raw_path TEXT,
    normalized_path TEXT,
    vault_index INTEGER,
    transcript_status TEXT NOT NULL DEFAULT 'pending',
    ingest_source TEXT NOT NULL DEFAULT 'historical',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_archive_entry ON archive_records(entry_id);
"""

DIMENSIONAL_DDL = """
CREATE TABLE IF NOT EXISTS dimensional_clips (
    write_seq INTEGER PRIMARY KEY AUTOINCREMENT,
    archive_seq INTEGER NOT NULL,
    clip_index INTEGER NOT NULL,
    window_ms INTEGER NOT NULL,
    transcript_fragment TEXT,
    end_intent_gauge REAL,
    intent_axes_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (archive_seq) REFERENCES archive_records(archive_seq)
);
CREATE INDEX IF NOT EXISTS idx_dim_archive ON dimensional_clips(archive_seq);
"""


def ensure_layout(root: Path | None = None) -> Path:
    root = root or ARCHIVE_ROOT
    for sub in ("raw", "normalized", "manifests", "transcripts", "db", "config"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def init_databases(root: Path | None = None) -> tuple[Path, Path]:
    root = ensure_layout(root)
    archive_path = root / "db" / "archive.db"
    dim_path = root / "db" / "dimensional.db"
    with sqlite3.connect(archive_path) as conn:
        conn.executescript(ARCHIVE_DDL)
    with sqlite3.connect(dim_path) as conn:
        conn.executescript(DIMENSIONAL_DDL)
    return archive_path, dim_path


def sha256_exists(archive_db: Path, digest: str) -> int | None:
    with sqlite3.connect(archive_db) as conn:
        row = conn.execute(
            "SELECT archive_seq FROM archive_records WHERE sha256 = ?", (digest,)
        ).fetchone()
    return row[0] if row else None