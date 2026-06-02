from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pydantic import ValidationError

from app.database import get_connection, insert_event
from app.models import StoreEvent


def ingest_events(events: List[Dict[str, Any]]) -> Tuple[int, int, int, List[Dict[str, Any]]]:
    """
    Validate and ingest up to 500 events.
    Returns (inserted, duplicates, failed, errors).
    """
    if len(events) > 500:
        events = events[:500]

    inserted = 0
    duplicates = 0
    failed = 0
    errors: List[Dict[str, Any]] = []

    with get_connection() as conn:
        for raw in events:
            try:
                model = StoreEvent.model_validate(raw)
                payload = model.model_dump(mode="json")
                payload["event_id"] = str(payload["event_id"])
                payload["timestamp"] = model.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
                payload["metadata"] = model.metadata.model_dump()
                if insert_event(conn, payload):
                    inserted += 1
                else:
                    duplicates += 1
            except ValidationError as exc:
                failed += 1
                errors.append({"event": raw, "error": exc.errors()})
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append({"event": raw, "error": str(exc)})
        conn.commit()

    return inserted, duplicates, failed, errors
