from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Set

from app.sessions import converted_sessions, customer_events, load_pos_transactions, session_units

POS_PATH = Path(os.getenv("POS_PATH", "data/pos_transactions.csv"))


def compute_funnel(store_id: str, events: List[dict]) -> Dict[str, Any]:
    store_events = [e for e in events if e["store_id"] == store_id]
    customers = customer_events(store_events)
    sessions = set(session_units(customers))

    entered: Set[str] = set()
    zone_visit: Set[str] = set()
    billing_queue: Set[str] = set()

    for e in customers:
        vid = e["visitor_id"]
        if vid not in sessions:
            continue
        if e["event_type"] in ("ENTRY", "REENTRY"):
            entered.add(vid)
        if e["event_type"] in ("ZONE_ENTER", "ZONE_DWELL") and e.get("zone_id"):
            zone_visit.add(vid)
        if e.get("zone_id") == "BILLING" or e["event_type"] in (
            "BILLING_QUEUE_JOIN",
            "ZONE_ENTER",
        ):
            if e.get("zone_id") == "BILLING" or e["event_type"] == "BILLING_QUEUE_JOIN":
                billing_queue.add(vid)

    # Include visitors first seen on floor/billing cameras (overlap handling)
    entry_base = entered | zone_visit | billing_queue
    zone_visit &= entry_base
    billing_queue &= entry_base

    pos_rows = load_pos_transactions(str(POS_PATH))
    purchased = converted_sessions(customers, pos_rows, store_id) & entry_base

    entry_count = len(entry_base)
    zone_count = len(zone_visit)
    billing_count = len(billing_queue)
    purchase_count = len(purchased)

    def dropoff(from_count: int, to_count: int) -> float:
        if from_count == 0:
            return 0.0
        return round((1 - to_count / from_count) * 100, 2)

    return {
        "store_id": store_id,
        "funnel": {
            "entry": entry_count,
            "zone_visit": zone_count,
            "billing_queue": billing_count,
            "purchase": purchase_count,
        },
        "dropoff_percent": {
            "entry_to_zone": dropoff(entry_count, zone_count),
            "zone_to_billing": dropoff(zone_count, billing_count),
            "billing_to_purchase": dropoff(billing_count, purchase_count),
        },
    }
