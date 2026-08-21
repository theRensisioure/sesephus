"""SQLite storage for ETDI (Emotional Time Density Index) scores.

Lives alongside the archive/vault databases; keyed by entry_id so a score
row always maps back to the memo manifest that produced it.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from ssfs_config import get_archive_root

ETDI_DDL = """
CREATE TABLE IF NOT EXISTS etdi_scores (
    entry_id TEXT PRIMARY KEY,
    recorded_at_utc TEXT,
    duration_seconds REAL,
    words_per_second REAL,
    pause_count INTEGER,
    pause_total_seconds REAL,
    valence REAL NOT NULL,
    arousal REAL NOT NULL,
    salience REAL NOT NULL,
    primary_emotion TEXT,
    time_distortion_likelihood REAL,
    rationale TEXT,
    confidence REAL,
    etdi REAL NOT NULL,
    backend TEXT,
    model TEXT,
    raw_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_etdi_recorded ON etdi_scores(recorded_at_utc);
"""


def default_db_path() -> Path:
    env = os.environ.get("SESEFUS_ETDI_DB")
    if env:
        return Path(env)
    try:
        from sesefus_config import load_config
        configured = load_config().get("etdi_db")
        if configured:
            path = Path(configured)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
    except ImportError:
        pass
    if os.name == "nt":
        # The main rig's archive drive via drive-mapping.json; only meaningful
        # on Windows — on POSIX the drive-letter path would just create a junk
        # directory in cwd.
        archive_db_dir = get_archive_root() / "db"
        try:
            archive_db_dir.mkdir(parents=True, exist_ok=True)
            return archive_db_dir / "etdi.db"
        except OSError:
            pass  # no T: drive — fall through to the repo-local default
    local = Path(__file__).resolve().parent.parent / "aurgio" / "etdi.db"
    local.parent.mkdir(parents=True, exist_ok=True)
    return local


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or default_db_path()
    conn = sqlite3.connect(path)
    conn.executescript(ETDI_DDL)
    return conn


def upsert_score(conn: sqlite3.Connection, record: dict) -> None:
    conn.execute(
        """
        INSERT INTO etdi_scores
        (entry_id, recorded_at_utc, duration_seconds, words_per_second,
         pause_count, pause_total_seconds, valence, arousal, salience,
         primary_emotion, time_distortion_likelihood, rationale, confidence,
         etdi, backend, model, raw_json)
        VALUES (:entry_id, :recorded_at_utc, :duration_seconds, :words_per_second,
                :pause_count, :pause_total_seconds, :valence, :arousal, :salience,
                :primary_emotion, :time_distortion_likelihood, :rationale, :confidence,
                :etdi, :backend, :model, :raw_json)
        ON CONFLICT(entry_id) DO UPDATE SET
            recorded_at_utc=excluded.recorded_at_utc,
            duration_seconds=excluded.duration_seconds,
            words_per_second=excluded.words_per_second,
            pause_count=excluded.pause_count,
            pause_total_seconds=excluded.pause_total_seconds,
            valence=excluded.valence,
            arousal=excluded.arousal,
            salience=excluded.salience,
            primary_emotion=excluded.primary_emotion,
            time_distortion_likelihood=excluded.time_distortion_likelihood,
            rationale=excluded.rationale,
            confidence=excluded.confidence,
            etdi=excluded.etdi,
            backend=excluded.backend,
            model=excluded.model,
            raw_json=excluded.raw_json
        """,
        record,
    )
    conn.commit()


def daily_trend(conn: sqlite3.Connection, days: int = 30) -> list[dict]:
    rows = conn.execute(
        """
        SELECT substr(coalesce(recorded_at_utc, created_at), 1, 10) AS day,
               avg(etdi) AS avg_etdi, max(etdi) AS max_etdi, count(*) AS n
        FROM etdi_scores
        GROUP BY day
        ORDER BY day DESC
        LIMIT ?
        """,
        (days,),
    ).fetchall()
    return [
        {"day": d, "avg_etdi": round(a, 4), "max_etdi": round(m, 4), "count": n}
        for d, a, m, n in reversed(rows)
    ]


def high_density_flags(conn: sqlite3.Connection, threshold: float = 0.30, limit: int = 20) -> list[dict]:
    rows = conn.execute(
        """
        SELECT entry_id, recorded_at_utc, etdi, primary_emotion,
               time_distortion_likelihood, rationale, confidence
        FROM etdi_scores
        WHERE etdi >= ?
        ORDER BY etdi DESC
        LIMIT ?
        """,
        (threshold, limit),
    ).fetchall()
    keys = ("entry_id", "recorded_at_utc", "etdi", "primary_emotion",
            "time_distortion_likelihood", "rationale", "confidence")
    return [dict(zip(keys, r)) for r in rows]


def recent_entries(conn: sqlite3.Connection, limit: int = 50) -> list[dict]:
    rows = conn.execute(
        """
        SELECT entry_id, recorded_at_utc, duration_seconds, valence, arousal,
               salience, primary_emotion, etdi, confidence
        FROM etdi_scores
        ORDER BY coalesce(recorded_at_utc, created_at) DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    keys = ("entry_id", "recorded_at_utc", "duration_seconds", "valence",
            "arousal", "salience", "primary_emotion", "etdi", "confidence")
    return [dict(zip(keys, r)) for r in rows]


if __name__ == "__main__":
    conn = connect()
    print(json.dumps({"trend": daily_trend(conn), "flags": high_density_flags(conn)}, indent=2))
