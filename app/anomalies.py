from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from app.database import avg_conversion_7d, get_connection
from app.metrics import compute_metrics
from app.sessions import customer_events, parse_ts


def compute_anomalies(store_id: str, events: List[dict]) -> Dict[str, Any]:
    store_events = [e for e in events if e["store_id"] == store_id]
    customers = customer_events(store_events)
    active: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)

    queue_depths = [
        e.get("metadata", {}).get("queue_depth", 0) or 0
        for e in customers
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    ]
    if queue_depths and max(queue_depths) >= 3:
        active.append(
            {
                "type": "BILLING_QUEUE_SPIKE",
                "severity": "WARN",
                "suggested_action": "Open another billing counter or reassign staff to queue management.",
            }
        )

    metrics = compute_metrics(store_id, events)
    day = now.strftime("%Y-%m-%d")
    try:
        with get_connection() as conn:
            baseline = avg_conversion_7d(conn, store_id, day)
    except Exception:
        baseline = None

    if baseline is not None and metrics["unique_visitors"] >= 5:
        if metrics["conversion_rate"] < baseline * 0.7:
            active.append(
                {
                    "type": "CONVERSION_DROP",
                    "severity": "CRITICAL",
                    "suggested_action": (
                        f"Conversion {metrics['conversion_rate']}% is below 7-day avg "
                        f"{round(baseline, 2)}%. Review queue and staffing."
                    ),
                }
            )

    # Dead zone: no visits in 30 minutes
    zone_last_seen: Dict[str, datetime] = {}
    for e in customers:
        zone = e.get("zone_id")
        if zone and e["event_type"] in ("ZONE_ENTER", "ZONE_DWELL"):
            zone_last_seen[zone] = max(
                zone_last_seen.get(zone, parse_ts(e["timestamp"])),
                parse_ts(e["timestamp"]),
            )

    for zone, last_ts in zone_last_seen.items():
        if now - last_ts > timedelta(minutes=30):
            active.append(
                {
                    "type": "DEAD_ZONE",
                    "zone_id": zone,
                    "severity": "INFO",
                    "suggested_action": f"No visits in {zone} for 30+ minutes. Check placement or camera coverage.",
                }
            )

    return {"store_id": store_id, "active_anomalies": active}
