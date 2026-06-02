from __future__ import annotations

from typing import Any, Dict, List

from app.sessions import customer_events, session_units


def compute_heatmap(store_id: str, events: List[dict]) -> Dict[str, Any]:
    store_events = [e for e in events if e["store_id"] == store_id]
    customers = customer_events(store_events)
    sessions = session_units(customers)
    data_confidence = "LOW" if len(sessions) < 20 else "HIGH"

    zones: Dict[str, Dict[str, float]] = {}
    for e in customers:
        zone = e.get("zone_id")
        if not zone:
            continue
        zones.setdefault(zone, {"visits": 0, "total_dwell_ms": 0.0})
        if e["event_type"] in ("ZONE_ENTER", "ZONE_DWELL", "ZONE_EXIT"):
            zones[zone]["visits"] += 1
            zones[zone]["total_dwell_ms"] += e.get("dwell_ms", 0)

    max_visits = max((z["visits"] for z in zones.values()), default=1)
    heatmap = []
    for zone_id, data in zones.items():
        visits = int(data["visits"])
        avg_dwell = round(data["total_dwell_ms"] / max(visits, 1), 2)
        normalized = round((visits / max_visits) * 100, 2) if max_visits else 0.0
        heatmap.append(
            {
                "zone_id": zone_id,
                "visit_frequency": visits,
                "avg_dwell_ms": avg_dwell,
                "normalized_score": normalized,
                "data_confidence": data_confidence,
            }
        )

    return {
        "store_id": store_id,
        "data_confidence": data_confidence,
        "sessions_in_window": len(sessions),
        "heatmap": heatmap,
    }
