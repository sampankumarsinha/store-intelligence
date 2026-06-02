"""
Convert Purplle-provided CCTV/POS exports into the Store Intelligence challenge event schema.
"""
from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _parse_purplle_ts(raw: str) -> datetime:
    s = raw.strip().replace("Z", "")
    if "+" not in s and s.count("-") <= 2:
        dt = datetime.fromisoformat(s)
    else:
        dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _fmt_ts(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _normalize_store_id(raw: Optional[str]) -> str:
    if not raw:
        return "STORE_UNKNOWN"
    s = raw.strip().upper().replace("STORE_", "ST").replace("STORE", "ST")
    if s.startswith("ST") and s[2:].isdigit():
        return s if s.startswith("ST") else f"ST{s}"
    if s.lower().startswith("store_"):
        num = s.split("_", 1)[-1]
        return f"ST{num}"
    return s.upper()


def _normalize_camera(raw: Optional[str]) -> str:
    if not raw:
        return "CAM_UNKNOWN"
    c = raw.strip().upper()
    if c.startswith("PURPLLE_"):
        return c.split("_")[-1] if "CAM" in c else c
    if c.lower().startswith("cam"):
        digits = "".join(ch for ch in c if ch.isdigit())
        return f"CAM_{digits or c[3:]}"
    return c


def _visitor_from_row(row: Dict[str, Any]) -> str:
    if row.get("id_token"):
        return str(row["id_token"])
    if row.get("track_id") is not None:
        return f"TRACK_{row['track_id']}"
    return f"VIS_{uuid.uuid4().hex[:8]}"


def _emit(
    *,
    store_id: str,
    camera_id: str,
    visitor_id: str,
    event_type: str,
    timestamp: datetime,
    zone_id: Optional[str] = None,
    dwell_ms: int = 0,
    is_staff: bool = False,
    confidence: float = 0.9,
    queue_depth: Optional[int] = None,
    group_candidate: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "queue_depth": queue_depth,
        "sku_zone": zone_id,
        "session_seq": 1,
        "group_candidate": group_candidate,
        "source": "purplle_adapter",
    }
    if extra:
        meta["purplle"] = extra
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": _fmt_ts(timestamp),
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": bool(is_staff),
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "metadata": meta,
    }


def convert_purplle_event(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Map one Purplle JSONL record to zero or more challenge-schema events."""
    et = (row.get("event_type") or "").lower()
    out: List[Dict[str, Any]] = []

    if et in ("entry", "exit"):
        ts = _parse_purplle_ts(row["event_timestamp"])
        store_id = _normalize_store_id(row.get("store_code"))
        camera_id = _normalize_camera(row.get("camera_id"))
        visitor_id = _visitor_from_row(row)
        group = bool(row.get("group_id"))
        mapped = "ENTRY" if et == "entry" else "EXIT"
        out.append(
            _emit(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=visitor_id,
                event_type=mapped,
                timestamp=ts,
                is_staff=bool(row.get("is_staff")),
                confidence=0.85 if group else 0.92,
                group_candidate=group,
                extra={
                    "group_id": row.get("group_id"),
                    "group_size": row.get("group_size"),
                    "gender_pred": row.get("gender_pred"),
                    "age_bucket": row.get("age_bucket"),
                },
            )
        )
        return out

    if et in ("zone_entered", "zone_exited"):
        ts = _parse_purplle_ts(row["event_time"])
        store_id = _normalize_store_id(row.get("store_id"))
        camera_id = _normalize_camera(row.get("camera_id"))
        visitor_id = _visitor_from_row(row)
        zone_id = row.get("zone_id") or row.get("zone_name")
        mapped = "ZONE_ENTER" if et == "zone_entered" else "ZONE_EXIT"
        billing = (row.get("zone_type") or "").upper() == "BILLING"
        out.append(
            _emit(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=visitor_id,
                event_type=mapped,
                timestamp=ts,
                zone_id=zone_id,
                is_staff=False,
                confidence=0.88,
                extra={"zone_name": row.get("zone_name"), "zone_type": row.get("zone_type")},
            )
        )
        if billing and et == "zone_entered":
            pos = row.get("queue_position_at_join")
            depth = int(pos) if pos is not None else 1
            if depth > 1:
                out.append(
                    _emit(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="BILLING_QUEUE_JOIN",
                        timestamp=ts,
                        zone_id=zone_id or "BILLING",
                        queue_depth=depth,
                        confidence=0.9,
                    )
                )
        return out

    if et in ("queue_completed", "queue_abandoned"):
        store_id = _normalize_store_id(row.get("store_id"))
        camera_id = _normalize_camera(row.get("camera_id"))
        visitor_id = _visitor_from_row(row)
        zone_id = row.get("zone_id") or "BILLING"
        join_ts = _parse_purplle_ts(row["queue_join_ts"])
        exit_ts = _parse_purplle_ts(row["queue_exit_ts"])
        pos = row.get("queue_position_at_join")
        depth = int(pos) if pos is not None else 1

        out.append(
            _emit(
                store_id=store_id,
                camera_id=camera_id,
                visitor_id=visitor_id,
                event_type="ZONE_ENTER",
                timestamp=join_ts,
                zone_id=zone_id,
                confidence=0.88,
                extra={"purplle_queue_event_id": row.get("queue_event_id")},
            )
        )
        if depth > 1:
            out.append(
                _emit(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_JOIN",
                    timestamp=join_ts,
                    zone_id=zone_id,
                    queue_depth=depth,
                    confidence=0.9,
                )
            )
        if row.get("abandoned") or et == "queue_abandoned":
            out.append(
                _emit(
                    store_id=store_id,
                    camera_id=camera_id,
                    visitor_id=visitor_id,
                    event_type="BILLING_QUEUE_ABANDON",
                    timestamp=exit_ts,
                    zone_id=zone_id,
                    confidence=0.85,
                )
            )
        else:
            served = row.get("queue_served_ts")
            if served:
                out.append(
                    _emit(
                        store_id=store_id,
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type="ZONE_DWELL",
                        timestamp=_parse_purplle_ts(served),
                        zone_id=zone_id,
                        dwell_ms=int((exit_ts - join_ts).total_seconds() * 1000),
                        confidence=0.86,
                    )
                )
        return out

    return out


def convert_purplle_jsonl(input_path: Path, output_path: Path) -> int:
    events: List[Dict[str, Any]] = []
    with input_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            events.extend(convert_purplle_event(row))
    events.sort(key=lambda e: e["timestamp"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as out:
        for e in events:
            out.write(json.dumps(e) + "\n")
    return len(events)


def _parse_purplle_order_date(date_str: str) -> str:
    """DD-MM-YYYY → YYYY-MM-DD."""
    day, month, year = date_str.strip().split("-")
    return f"{year}-{month}-{day}"


def convert_purplle_pos_csv(input_path: Path, output_path: Path) -> int:
    import csv

    orders: Dict[tuple, Dict[str, Any]] = defaultdict(lambda: {"total": 0.0, "lines": 0})
    with input_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            store_id = row["store_id"].strip().upper()
            order_id = row["order_id"].strip()
            iso_date = _parse_purplle_order_date(row["order_date"])
            ts = f"{iso_date}T{row['order_time'].strip()}Z"
            key = (store_id, order_id)
            orders[key]["store_id"] = store_id
            orders[key]["timestamp"] = ts
            orders[key]["transaction_id"] = f"ORD_{order_id}"
            orders[key]["total"] += float(row.get("total_amount") or 0)
            orders[key]["lines"] += 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["store_id", "transaction_id", "timestamp", "basket_value_inr"],
        )
        writer.writeheader()
        for (_, _), data in sorted(orders.items(), key=lambda x: x[1]["timestamp"]):
            writer.writerow(
                {
                    "store_id": data["store_id"],
                    "transaction_id": data["transaction_id"],
                    "timestamp": data["timestamp"],
                    "basket_value_inr": round(data["total"], 2),
                }
            )
    return len(orders)
