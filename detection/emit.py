"""Structured event emission matching the challenge schema."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def emit_event(
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
    sku_zone: Optional[str] = None,
    session_seq: int = 1,
    group_candidate: bool = False,
    track_id: Optional[int] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    ts = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    metadata: Dict[str, Any] = {
        "queue_depth": queue_depth,
        "sku_zone": sku_zone,
        "session_seq": session_seq,
        "group_candidate": group_candidate,
        "source": "detection_pipeline",
    }
    if track_id is not None:
        metadata["track_id"] = track_id
    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "event_id": str(uuid.uuid4()),
        "store_id": store_id,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": ts,
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": is_staff,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "metadata": metadata,
    }
