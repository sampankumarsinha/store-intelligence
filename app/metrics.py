from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from app.database import get_connection, upsert_daily_conversion
from app.sessions import (
    converted_sessions,
    customer_events,
    events_on_latest_day,
    load_pos_transactions,
    unique_visitor_sessions,
)

POS_PATH = Path(os.getenv("POS_PATH", "data/pos_transactions.csv"))


def compute_metrics(store_id: str, events: List[dict]) -> Dict[str, Any]:
    store_events = [e for e in events if e["store_id"] == store_id]
    customers = customer_events(store_events)
    customers_today = events_on_latest_day(customers)
    visitors = unique_visitor_sessions(customers_today)
    pos_rows = load_pos_transactions(str(POS_PATH))
    converted = converted_sessions(customers_today, pos_rows, store_id)

    unique_count = len(visitors)
    converted_count = len(converted & visitors)
    conversion_rate = round(
        (converted_count / unique_count * 100) if unique_count else 0.0,
        2,
    )

    # avg dwell per zone
    dwell_by_zone: Dict[str, List[int]] = {}
    for e in customers_today:
        if e["event_type"] == "ZONE_DWELL" and e.get("zone_id"):
            dwell_by_zone.setdefault(e["zone_id"], []).append(e.get("dwell_ms", 0))
    avg_dwell_per_zone = {
        z: round(sum(vals) / len(vals), 2) for z, vals in dwell_by_zone.items()
    }

    queue_depths = [
        e.get("metadata", {}).get("queue_depth", 0) or 0
        for e in customers_today
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    ]
    current_queue_depth = max(queue_depths) if queue_depths else 0

    joined = {
        e["visitor_id"]
        for e in customers_today
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    }
    abandoned = {
        e["visitor_id"]
        for e in customers_today
        if e["event_type"] == "BILLING_QUEUE_ABANDON"
    }
    abandonment_rate = round(
        (len(abandoned) / len(joined) * 100) if joined else 0.0,
        2,
    )

    # Persist daily conversion snapshot for anomaly baseline
    if unique_count:
        day = customers_today[-1]["timestamp"][:10] if customers_today else "1970-01-01"
        try:
            with get_connection() as conn:
                upsert_daily_conversion(conn, store_id, day, conversion_rate)
                conn.commit()
        except Exception:
            pass

    return {
        "store_id": store_id,
        "unique_visitors": unique_count,
        "conversion_rate": conversion_rate,
        "converted_visitors": converted_count,
        "avg_dwell_per_zone": avg_dwell_per_zone,
        "current_queue_depth": current_queue_depth,
        "abandonment_rate": abandonment_rate,
    }
