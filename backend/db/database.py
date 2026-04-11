import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.config import DB_PATH



def get_connection() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn



def init_db() -> None:
    schema_path = Path(__file__).with_name("schema.sql")
    with get_connection() as conn:
        conn.executescript(schema_path.read_text())



def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["harmonics_json"] = item.get("harmonics_json") or "[]"
    try:
        item["harmonics"] = json.loads(item["harmonics_json"])
    except json.JSONDecodeError:
        item["harmonics"] = []
    return item



def list_calls() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM calls ORDER BY id DESC").fetchall()
    return [row_to_dict(r) for r in rows]



def get_call(call_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
    return row_to_dict(row) if row else None



def upsert_call(record: dict[str, Any]) -> int:
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM calls WHERE call_id_csv = ?",
            (record["call_id_csv"],),
        ).fetchone()

        values = (
            record["call_id_csv"],
            record["start_sec"],
            record["end_sec"],
            record["hpss_path"],
            record["gated_path"],
            record["clean_path"],
            record["spec_hpss"],
            record["spec_gated"],
            record["spec_clean"],
            record["call_type"],
            record["fundamental_hz"],
            record["num_callers"],
            json.dumps(record.get("harmonics_visible", [])),
            record["confidence"],
            record["notes"],
        )

        if existing:
            conn.execute(
                """
                UPDATE calls
                SET start_sec = ?, end_sec = ?, hpss_path = ?, gated_path = ?, clean_path = ?,
                    spec_hpss = ?, spec_gated = ?, spec_clean = ?, call_type = ?,
                    fundamental_hz = ?, num_callers = ?, harmonics_json = ?, confidence = ?, gemini_notes = ?
                WHERE call_id_csv = ?
                """,
                values[1:] + (record["call_id_csv"],),
            )
            return int(existing["id"])

        cursor = conn.execute(
            """
            INSERT INTO calls(
              call_id_csv, start_sec, end_sec, hpss_path, gated_path, clean_path,
              spec_hpss, spec_gated, spec_clean, call_type, fundamental_hz, num_callers,
              harmonics_json, confidence, gemini_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return int(cursor.lastrowid)



def get_stats() -> dict[str, Any]:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) AS count FROM calls").fetchone()["count"]
        by_type_rows = conn.execute(
            "SELECT call_type, COUNT(*) AS count FROM calls GROUP BY call_type"
        ).fetchall()
        confidence = conn.execute(
            "SELECT AVG(confidence) AS avg_conf FROM calls WHERE confidence IS NOT NULL"
        ).fetchone()["avg_conf"]

    return {
        "total_calls": total,
        "avg_confidence": confidence or 0.0,
        "by_call_type": {r["call_type"] or "unknown": r["count"] for r in by_type_rows},
    }
