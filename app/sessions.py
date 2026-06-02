"""Visitor session reconstruction for metrics and funnel."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Set


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def customer_events(events: List[dict]) -> List[dict]:
    return [e for e in events if not e.get("is_staff")]


def events_on_latest_day(events: List[dict]) -> List[dict]:
    """Filter to the latest UTC calendar day present (store operational day)."""
    if not events:
        return []
    latest_day = max(parse_ts(e["timestamp"]).date() for e in events)
    return [e for e in events if parse_ts(e["timestamp"]).date() == latest_day]


def unique_visitor_sessions(events: List[dict]) -> Set[str]:
    """
    Unique visitors for metrics — REENTRY does not create a new visitor_id.
    Count distinct visitor_id that have ENTRY or REENTRY.
    """
    visitors: Set[str] = set()
    for e in customer_events(events):
        if e["event_type"] in ("ENTRY", "REENTRY"):
            visitors.add(e["visitor_id"])
    # Visitors only seen in zones still count if they have any event
    for e in customer_events(events):
        visitors.add(e["visitor_id"])
    return visitors


def session_units(events: List[dict]) -> List[str]:
    """
    Funnel session units: one per visitor_id (re-entry does not double-count).
    """
    return sorted(unique_visitor_sessions(events))


def visitors_in_billing_window(
    events: List[dict],
    txn_time: datetime,
    window_minutes: int = 5,
) -> Set[str]:
    window = timedelta(minutes=window_minutes)
    converted: Set[str] = set()
    for e in customer_events(events):
        if e.get("zone_id") != "BILLING":
            continue
        if e["event_type"] not in (
            "ZONE_ENTER",
            "ZONE_DWELL",
            "BILLING_QUEUE_JOIN",
        ):
            continue
        ts = parse_ts(e["timestamp"])
        if txn_time - window <= ts <= txn_time:
            converted.add(e["visitor_id"])
    return converted


def load_pos_transactions(path: str) -> List[dict]:
    import csv
    from pathlib import Path

    rows: List[dict] = []
    base = Path(path)
    paths = [base]
    purplle = base.parent / "pos_transactions_purplle.csv"
    if purplle.exists() and purplle.resolve() != base.resolve():
        paths.append(purplle)
    for p in paths:
        if not p.exists():
            continue
        with p.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(_normalize_pos_row(row))
    return rows


def _normalize_pos_row(row: dict) -> dict:
    if "timestamp" in row and row.get("timestamp"):
        return row
    if "order_date" in row and "order_time" in row:
        day, month, year = row["order_date"].strip().split("-")
        ts = f"{year}-{month}-{day}T{row['order_time'].strip()}Z"
        return {
            "store_id": row["store_id"].strip().upper(),
            "transaction_id": f"ORD_{row.get('order_id', '').strip()}",
            "timestamp": ts,
            "basket_value_inr": row.get("total_amount", "0"),
        }
    return row


def converted_sessions(
    events: List[dict],
    pos_rows: List[dict],
    store_id: str,
) -> Set[str]:
    converted: Set[str] = set()
    store_events = [e for e in customer_events(events) if e["store_id"] == store_id]
    for txn in pos_rows:
        if txn.get("store_id") != store_id:
            continue
        txn_time = parse_ts(txn["timestamp"])
        converted |= visitors_in_billing_window(store_events, txn_time)
    return converted
