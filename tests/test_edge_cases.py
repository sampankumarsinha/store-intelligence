# PROMPT:
# Generate edge-case API tests: empty store, all-staff, zero purchases, billing abandonment,
# stale feed warning, database 503, and heatmap data_confidence LOW.
#
# CHANGES MADE:
# Added db-disable simulation via set_db_enabled, stale timestamp seeding, and heatmap confidence check.

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.database import get_connection, insert_event, set_db_enabled
from app.main import app

client = TestClient(app)


def test_empty_store_returns_zeros():
    resp = client.get("/stores/EMPTY_XYZ/metrics")
    data = resp.json()
    assert resp.status_code == 200
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["current_queue_depth"] == 0
    assert data["abandonment_rate"] == 0.0


def test_all_staff_excluded_from_customer_metrics():
    events = [
        {
            "event_id": "66666666-6666-6666-6666-666666666601",
            "store_id": "STORE_STAFF_ONLY",
            "camera_id": "CAM_4",
            "visitor_id": "STAFF_ONLY",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-05-29T22:00:00Z",
            "zone_id": "WAREHOUSE",
            "dwell_ms": 1000,
            "is_staff": True,
            "confidence": 0.9,
            "metadata": {"session_seq": 1},
        },
    ]
    client.post("/events/ingest", json=events)
    metrics = client.get("/stores/STORE_STAFF_ONLY/metrics").json()
    assert metrics["unique_visitors"] == 0
    assert metrics["conversion_rate"] == 0.0


def test_zero_purchases_safe_conversion():
    resp = client.get("/stores/STORE_ZERO_PURCHASE/metrics")
    assert resp.status_code == 200
    assert resp.json()["conversion_rate"] == 0.0


def test_billing_abandonment_rate():
    events = [
        {
            "event_id": "44444444-4444-4444-4444-444444444401",
            "store_id": "STORE_001",
            "camera_id": "CAM_3",
            "visitor_id": "VIS_ABANDON",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": "2026-05-29T21:00:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"queue_depth": 1, "session_seq": 1},
        },
        {
            "event_id": "44444444-4444-4444-4444-444444444402",
            "store_id": "STORE_001",
            "camera_id": "CAM_3",
            "visitor_id": "VIS_ABANDON",
            "event_type": "BILLING_QUEUE_ABANDON",
            "timestamp": "2026-05-29T21:05:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.85,
            "metadata": {"session_seq": 2},
        },
    ]
    client.post("/events/ingest", json=events)
    metrics = client.get("/stores/STORE_001/metrics").json()
    assert metrics["abandonment_rate"] == 100.0


def test_heatmap_low_confidence():
    resp = client.get("/stores/STORE_NEW/heatmap")
    assert resp.json()["data_confidence"] == "LOW"


def test_stale_feed_warning():
    old_ts = (datetime.now(timezone.utc) - timedelta(minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with get_connection() as conn:
        insert_event(
            conn,
            {
                "event_id": "55555555-5555-5555-5555-555555555551",
                "store_id": "STORE_STALE",
                "camera_id": "CAM_1",
                "visitor_id": "VIS_OLD",
                "event_type": "ENTRY",
                "timestamp": old_ts,
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {},
            },
        )
        conn.commit()
    health = client.get("/health").json()
    assert "STORE_STALE" in health.get("stale_feeds", {})


def test_database_unavailable_503():
    set_db_enabled(False)
    resp = client.get("/stores/STORE_001/metrics")
    assert resp.status_code == 503
    assert resp.json()["error"] == "service_unavailable"
    set_db_enabled(True)
