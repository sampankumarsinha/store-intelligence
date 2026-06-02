from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.database import DatabaseUnavailable, get_connection, is_db_enabled, last_event_per_store
from app.sessions import parse_ts

STALE_MINUTES = 10


def compute_health() -> Dict[str, Any]:
    db_status = "ok"
    last_per_store: Dict[str, str] = {}
    stale_feeds: Dict[str, Any] = {}

    total_events = 0
    try:
        if not is_db_enabled():
            raise DatabaseUnavailable("disabled")
        with get_connection() as conn:
            last_per_store = last_event_per_store(conn)
            row = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
            total_events = int(row["c"]) if row else 0
    except DatabaseUnavailable:
        db_status = "unavailable"

    now = datetime.now(timezone.utc)
    for store_id, ts in last_per_store.items():
        last_time = parse_ts(ts)
        lag_minutes = (now - last_time).total_seconds() / 60
        if lag_minutes > STALE_MINUTES:
            stale_feeds[store_id] = {
                "status": "STALE_FEED",
                "lag_minutes": round(lag_minutes, 2),
                "suggested_action": "Check CCTV feed or restart detection pipeline.",
            }

    status = "ok"
    if db_status != "ok":
        status = "degraded"
    elif stale_feeds:
        status = "warning"

    return {
        "status": status,
        "database": db_status,
        "total_events": total_events,
        "last_event_timestamp_per_store": last_per_store,
        "stale_feeds": stale_feeds,
    }
