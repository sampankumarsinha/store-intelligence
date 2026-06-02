from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

DB_PATH = Path(os.getenv("DATABASE_PATH", "data/store.db"))


class DatabaseUnavailable(Exception):
    """Raised when SQLite cannot be accessed."""


_db_enabled = True


def set_db_enabled(enabled: bool) -> None:
    global _db_enabled
    _db_enabled = enabled


def is_db_enabled() -> bool:
    return _db_enabled


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                store_id TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                visitor_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                zone_id TEXT,
                dwell_ms INTEGER NOT NULL DEFAULT 0,
                is_staff INTEGER NOT NULL DEFAULT 0,
                confidence REAL NOT NULL,
                metadata TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_store_ts ON events(store_id, timestamp)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_conversion (
                store_id TEXT NOT NULL,
                day TEXT NOT NULL,
                conversion_rate REAL NOT NULL,
                PRIMARY KEY (store_id, day)
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    if not _db_enabled:
        raise DatabaseUnavailable("Database is disabled")
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as exc:
        raise DatabaseUnavailable(str(exc)) from exc
    finally:
        if conn is not None:
            conn.close()


def insert_event(conn: sqlite3.Connection, event: Dict[str, Any]) -> bool:
    """Returns True if inserted, False if duplicate."""
    cur = conn.execute("SELECT 1 FROM events WHERE event_id = ?", (event["event_id"],))
    if cur.fetchone():
        return False
    conn.execute(
        """
        INSERT INTO events (
            event_id, store_id, camera_id, visitor_id, event_type,
            timestamp, zone_id, dwell_ms, is_staff, confidence, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            event["store_id"],
            event["camera_id"],
            event["visitor_id"],
            event["event_type"],
            event["timestamp"],
            event.get("zone_id"),
            event.get("dwell_ms", 0),
            1 if event.get("is_staff") else 0,
            event.get("confidence", 0.0),
            json.dumps(event.get("metadata", {})),
        ),
    )
    return True


def fetch_store_events(conn: sqlite3.Connection, store_id: str) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM events WHERE store_id = ? ORDER BY timestamp",
        (store_id,),
    ).fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "event_id": row["event_id"],
                "store_id": row["store_id"],
                "camera_id": row["camera_id"],
                "visitor_id": row["visitor_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "zone_id": row["zone_id"],
                "dwell_ms": row["dwell_ms"],
                "is_staff": bool(row["is_staff"]),
                "confidence": row["confidence"],
                "metadata": json.loads(row["metadata"]),
            }
        )
    return result


def last_event_per_store(conn: sqlite3.Connection) -> Dict[str, str]:
    rows = conn.execute(
        """
        SELECT store_id, MAX(timestamp) AS last_ts
        FROM events
        GROUP BY store_id
        """
    ).fetchall()
    return {row["store_id"]: row["last_ts"] for row in rows}


def upsert_daily_conversion(conn: sqlite3.Connection, store_id: str, day: str, rate: float):
    conn.execute(
        """
        INSERT INTO daily_conversion (store_id, day, conversion_rate)
        VALUES (?, ?, ?)
        ON CONFLICT(store_id, day) DO UPDATE SET conversion_rate = excluded.conversion_rate
        """,
        (store_id, day, rate),
    )


def avg_conversion_7d(conn: sqlite3.Connection, store_id: str, day: str) -> Optional[float]:
    rows = conn.execute(
        """
        SELECT conversion_rate FROM daily_conversion
        WHERE store_id = ? AND day < ?
        ORDER BY day DESC LIMIT 7
        """,
        (store_id, day),
    ).fetchall()
    if not rows:
        return None
    return sum(r["conversion_rate"] for r in rows) / len(rows)
