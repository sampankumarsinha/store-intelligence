import time
import uuid
import logging
from typing import List
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from app.models import StoreEvent

app = FastAPI(title="Store Intelligence API")

EVENTS = {}
LAST_EVENT_TIME = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("store-intelligence")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    trace_id = str(uuid.uuid4())
    start_time = time.time()

    response = await call_next(request)

    latency_ms = round((time.time() - start_time) * 1000, 2)

    logger.info({
        "trace_id": trace_id,
        "method": request.method,
        "endpoint": request.url.path,
        "latency_ms": latency_ms,
        "status_code": response.status_code
    })

    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health")
def health():
    now = datetime.now(timezone.utc)
    stale_feeds = {}

    for store_id, ts in LAST_EVENT_TIME.items():
        last_time = datetime.fromisoformat(ts)
        lag_minutes = (now - last_time).total_seconds() / 60

        if lag_minutes > 100000:
            stale_feeds[store_id] = {
                "status": "STALE_FEED",
                "lag_minutes": round(lag_minutes, 2),
                "suggested_action": "Check CCTV feed or detection pipeline."
            }

    return {
        "status": "ok" if not stale_feeds else "warning",
        "total_events": len(EVENTS),
        "last_event_timestamp_per_store": LAST_EVENT_TIME,
        "stale_feeds": stale_feeds
    }


@app.post("/events/ingest")
def ingest_events(events: List[StoreEvent]):
    inserted = 0
    duplicates = 0
    errors = []

    for event in events:
        try:
            event_id = str(event.event_id)

            if event_id in EVENTS:
                duplicates += 1
                continue

            EVENTS[event_id] = event.model_dump()
            LAST_EVENT_TIME[event.store_id] = event.timestamp.isoformat()
            inserted += 1

        except Exception as e:
            errors.append({
                "event": str(event),
                "error": str(e)
            })

    return {
        "status": "success",
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors
    }


@app.get("/stores/{store_id}/metrics")
def get_metrics(store_id: str):
    store_events = [
        e for e in EVENTS.values()
        if e["store_id"] == store_id and e["is_staff"] is False
    ]

    visitor_ids = set(e["visitor_id"] for e in store_events)

    entries = [
        e for e in store_events
        if e["event_type"] == "ENTRY"
    ]

    exits = [
        e for e in store_events
        if e["event_type"] == "EXIT"
    ]

    billing_events = [
        e for e in store_events
        if e.get("zone_id") == "BILLING"
    ]

    billing_visitors = set(e["visitor_id"] for e in billing_events)

    queue_depths = [
        e.get("metadata", {}).get("queue_depth", 0)
        for e in store_events
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    ]

    current_queue_depth = max(queue_depths) if queue_depths else 0

    avg_dwell = {}
    zone_events = [
        e for e in store_events
        if e["event_type"] == "ZONE_DWELL"
    ]

    for e in zone_events:
        zone = e["zone_id"]
        avg_dwell.setdefault(zone, []).append(e["dwell_ms"])

    avg_dwell = {
        zone: round(sum(values) / len(values), 2)
        for zone, values in avg_dwell.items()
    }

    abandonment_rate = 0.0
    queue_join_visitors = set(
        e["visitor_id"]
        for e in store_events
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    )

    abandoned_visitors = set(
        e["visitor_id"]
        for e in store_events
        if e["event_type"] == "BILLING_QUEUE_ABANDON"
    )

    if queue_join_visitors:
        abandonment_rate = round(
            len(abandoned_visitors) / len(queue_join_visitors) * 100,
            2
        )

    conversion_rate = round(
        len(billing_visitors) / max(len(visitor_ids), 1) * 100,
        2
    )

    return {
        "store_id": store_id,
        "unique_visitors": len(visitor_ids),
        "entry_count": len(entries),
        "exit_count": len(exits),
        "billing_visitors": len(billing_visitors),
        "conversion_rate": conversion_rate,
        "avg_dwell_per_zone": avg_dwell,
        "current_queue_depth": current_queue_depth,
        "abandonment_rate": abandonment_rate
    }



    
@app.get("/stores/{store_id}/funnel")
def funnel(store_id: str):
    store_events = [
        e for e in EVENTS.values()
        if e["store_id"] == store_id and e["is_staff"] is False
    ]

    entered = set()
    zone_visit = set()
    billing = set()

    for e in store_events:
        visitor_id = e["visitor_id"]

        if e["event_type"] == "ENTRY":
            entered.add(visitor_id)

        if e["event_type"] in ["ZONE_ENTER", "ZONE_DWELL"]:
            zone_visit.add(visitor_id)

        if e.get("zone_id") == "BILLING":
            billing.add(visitor_id)

    # Funnel should represent the reconstructed customer journey.
    # Some visitors are first detected in product/billing cameras,
    # so we include them in entry base to avoid missing camera-overlap journeys.
    entry_base = entered | zone_visit | billing

    zone_visit = zone_visit & entry_base
    billing = billing & entry_base

    entry_count = len(entry_base)
    zone_count = len(zone_visit)
    billing_count = len(billing)
    purchase_count = billing_count

    return {
        "store_id": store_id,
        "funnel": {
            "entry": entry_count,
            "zone_visit": zone_count,
            "billing_queue": billing_count,
            "purchase": purchase_count
        },
        "dropoff_percent": {
            "entry_to_zone": round(
                (1 - zone_count / max(entry_count, 1)) * 100,
                2
            ),
            "zone_to_billing": round(
                (1 - billing_count / max(zone_count, 1)) * 100,
                2
            ),
            "billing_to_purchase": round(
                (1 - purchase_count / max(billing_count, 1)) * 100,
                2
            )
        }
    }
@app.get("/stores/{store_id}/heatmap")
def heatmap(store_id: str):
    store_events = [
        e for e in EVENTS.values()
        if e["store_id"] == store_id and e["is_staff"] is False
    ]

    zones = {}

    for e in store_events:
        zone = e.get("zone_id")

        if zone:
            zones.setdefault(zone, {
                "visits": 0,
                "total_dwell_ms": 0
            })

            zones[zone]["visits"] += 1
            zones[zone]["total_dwell_ms"] += e.get("dwell_ms", 0)

    result = []

    max_visits = max([z["visits"] for z in zones.values()], default=1)

    for zone, data in zones.items():
        normalized_score = round((data["visits"] / max_visits) * 100, 2)

        result.append({
            "zone_id": zone,
            "visit_frequency": data["visits"],
            "avg_dwell_ms": round(
                data["total_dwell_ms"] / max(data["visits"], 1),
                2
            ),
            "normalized_score": normalized_score,
            "data_confidence": "LOW" if data["visits"] < 20 else "HIGH"
        })

    return {
        "store_id": store_id,
        "heatmap": result
    }


@app.get("/stores/{store_id}/anomalies")
def anomalies(store_id: str):
    store_events = [
        e for e in EVENTS.values()
        if e["store_id"] == store_id and e["is_staff"] is False
    ]

    active = []

    billing_events = [
        e for e in store_events
        if e.get("zone_id") == "BILLING"
    ]

    queue_depths = [
        e.get("metadata", {}).get("queue_depth", 0)
        for e in store_events
        if e["event_type"] == "BILLING_QUEUE_JOIN"
    ]

    max_queue_depth = max(queue_depths) if queue_depths else 0

    if max_queue_depth >= 3:
        active.append({
            "type": "BILLING_QUEUE_SPIKE",
            "severity": "WARN",
            "suggested_action": "Open another billing counter or assign staff to manage queue."
        })

    zone_visits = {}

    for e in store_events:
        zone = e.get("zone_id")
        if zone and zone != "BILLING":
            zone_visits[zone] = zone_visits.get(zone, 0) + 1

    expected_zones = ["COSMETICS_A", "COSMETICS_B"]

    for zone in expected_zones:
        if zone_visits.get(zone, 0) == 0:
            active.append({
                "type": "DEAD_ZONE",
                "zone_id": zone,
                "severity": "INFO",
                "suggested_action": f"Review product placement or camera coverage for {zone}."
            })

    metrics_data = get_metrics(store_id)
    conversion_rate = metrics_data["conversion_rate"]

    if metrics_data["unique_visitors"] > 5 and conversion_rate < 20:
        active.append({
            "type": "CONVERSION_DROP",
            "severity": "CRITICAL",
            "suggested_action": "Investigate billing queue, staff availability, and product-zone engagement."
        })

    return {
        "store_id": store_id,
        "active_anomalies": active
    }
@app.post("/reset")
def reset_events():
    EVENTS.clear()
    LAST_EVENT_TIME.clear()
    return {"status": "cleared"}