# SQLite via stdlib sqlite3, no ORM

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent.parent / "data" / "echomap.db"

_connection: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Get or create database connection."""
    global _connection
    if _connection is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _connection.row_factory = sqlite3.Row
        init_db()
    return _connection


def init_db() -> None:
    """Initialize database schema."""
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            call_id_csv TEXT UNIQUE,
            file TEXT,
            start_sec REAL,
            end_sec REAL,
            call_type TEXT,
            caller_id TEXT,
            date TEXT,
            location TEXT,
            lat REAL,
            lon REAL,
            notes TEXT,
            hpss_path TEXT,
            gated_path TEXT,
            clean_path TEXT,
            spec_hpss TEXT,
            spec_gated TEXT,
            spec_clean TEXT,
            classification TEXT,
            confidence REAL,
            fundamental_hz REAL,
            num_callers INTEGER,
            harmonics_json TEXT,
            gemini_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_calls_call_id ON calls(call_id_csv);
        CREATE INDEX IF NOT EXISTS idx_calls_type ON calls(call_type);
    """)
    conn.commit()


def upsert_call(record: dict[str, Any]) -> int:
    """Insert or update a call record."""
    import json
    conn = get_db()

    existing = conn.execute(
        "SELECT id FROM calls WHERE call_id_csv = ?",
        (record["call_id_csv"],)
    ).fetchone()

    harmonics = json.dumps(record.get("harmonics", []))

    if existing:
        conn.execute("""
            UPDATE calls SET
                file = ?, start_sec = ?, end_sec = ?, call_type = ?,
                hpss_path = ?, gated_path = ?, clean_path = ?,
                spec_hpss = ?, spec_gated = ?, spec_clean = ?,
                classification = ?, confidence = ?, fundamental_hz = ?,
                num_callers = ?, harmonics_json = ?, gemini_notes = ?, notes = ?
            WHERE call_id_csv = ?
        """, (
            record.get("file"),
            record.get("start_sec"),
            record.get("end_sec"),
            record.get("call_type"),
            record.get("hpss_path"),
            record.get("gated_path"),
            record.get("clean_path"),
            record.get("spec_hpss"),
            record.get("spec_gated"),
            record.get("spec_clean"),
            record.get("classification"),
            record.get("confidence"),
            record.get("fundamental_hz"),
            record.get("num_callers"),
            harmonics,
            record.get("gemini_notes"),
            record.get("notes"),
            record["call_id_csv"]
        ))
        conn.commit()
        return existing[0]
    else:
        cursor = conn.execute("""
            INSERT INTO calls (
                call_id_csv, file, start_sec, end_sec, call_type,
                hpss_path, gated_path, clean_path,
                spec_hpss, spec_gated, spec_clean,
                classification, confidence, fundamental_hz,
                num_callers, harmonics_json, gemini_notes, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["call_id_csv"],
            record.get("file"),
            record.get("start_sec"),
            record.get("end_sec"),
            record.get("call_type"),
            record.get("hpss_path"),
            record.get("gated_path"),
            record.get("clean_path"),
            record.get("spec_hpss"),
            record.get("spec_gated"),
            record.get("spec_clean"),
            record.get("classification"),
            record.get("confidence"),
            record.get("fundamental_hz"),
            record.get("num_callers"),
            harmonics,
            record.get("gemini_notes"),
            record.get("notes")
        ))
        conn.commit()
        return cursor.lastrowid


def list_calls() -> list[dict[str, Any]]:
    """Get all calls."""
    import json
    conn = get_db()
    rows = conn.execute("SELECT * FROM calls ORDER BY id").fetchall()

    result = []
    for row in rows:
        item = dict(row)
        try:
            item["harmonics"] = json.loads(item.get("harmonics_json") or "[]")
        except:
            item["harmonics"] = []
        result.append(item)

    return result


def get_call(call_id: int) -> dict[str, Any] | None:
    """Get a single call by ID."""
    import json
    conn = get_db()
    row = conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()

    if not row:
        return None

    item = dict(row)
    try:
        item["harmonics"] = json.loads(item.get("harmonics_json") or "[]")
    except:
        item["harmonics"] = []

    return item


def get_stats() -> dict[str, Any]:
    """Get database statistics."""
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    avg_conf = conn.execute(
        "SELECT AVG(confidence) FROM calls WHERE confidence IS NOT NULL"
    ).fetchone()[0]
    by_type = conn.execute(
        "SELECT call_type, COUNT(*) FROM calls WHERE call_type IS NOT NULL GROUP BY call_type"
    ).fetchall()

    return {
        "total_calls": total,
        "avg_confidence": avg_conf or 0,
        "by_call_type": {t: c for t, c in by_type if t}
    }


def close_db() -> None:
    """Close database connection."""
    global _connection
    if _connection:
        _connection.close()
        _connection = None
