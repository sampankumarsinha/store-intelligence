# PROMPT:
# Generate FastAPI tests for a Store Intelligence API covering health,
# event ingestion, idempotency, metrics, funnel, heatmap, and anomalies.
#
# CHANGES MADE:
# I simplified the generated tests to match the final in-memory prototype.
# I added edge cases for duplicate ingestion, empty store metrics,
# staff exclusion, and zero-event stores.

from fastapi.testclient import TestClient
from app.main import app, EVENTS, LAST_EVENT_TIME

client = TestClient(app)


def reset_state():
    EVENTS.clear()
    LAST_EVENT_TIME.clear()


def test_health_empty():
    reset_state()

    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["total_events"] == 0


def test_empty_store_metrics():
    reset_state()

    response = client.get("/stores/EMPTY_STORE/metrics")

    assert response.status_code == 200
    data = response.json()

    assert data["unique_visitors"] == 0
    assert data["entry_count"] == 0
    assert data["conversion_rate"] == 0.0


def test_ingest_event_success():
    reset_state()

    event = [{
        "event_id": "11111111-1111-1111-1111-111111111111",
        "store_id": "STORE_TEST",
        "camera_id": "CAM_3",
        "visitor_id": "VIS_001",
        "event_type": "ENTRY",
        "timestamp": "2026-05-29T20:00:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.95,
        "metadata": {"session_seq": 1}
    }]

    response = client.post("/events/ingest", json=event)

    assert response.status_code == 200
    assert response.json()["inserted"] == 1


def test_idempotent_ingest_duplicate():
    reset_state()

    event = [{
        "event_id": "22222222-2222-2222-2222-222222222222",
        "store_id": "STORE_TEST",
        "camera_id": "CAM_3",
        "visitor_id": "VIS_002",
        "event_type": "ENTRY",
        "timestamp": "2026-05-29T20:01:00Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.90,
        "metadata": {"session_seq": 1}
    }]

    first = client.post("/events/ingest", json=event)
    second = client.post("/events/ingest", json=event)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["inserted"] == 1
    assert second.json()["duplicates"] == 1


def test_metrics_with_zone_and_billing():
    reset_state()

    events = [
        {
            "event_id": "33333333-3333-3333-3333-333333333333",
            "store_id": "STORE_TEST",
            "camera_id": "CAM_3",
            "visitor_id": "VIS_001",
            "event_type": "ENTRY",
            "timestamp": "2026-05-29T20:00:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"session_seq": 1}
        },
        {
            "event_id": "44444444-4444-4444-4444-444444444444",
            "store_id": "STORE_TEST",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_001",
            "event_type": "ZONE_DWELL",
            "timestamp": "2026-05-29T20:02:00Z",
            "zone_id": "COSMETICS_A",
            "dwell_ms": 30000,
            "is_staff": False,
            "confidence": 0.88,
            "metadata": {"session_seq": 2}
        },
        {
            "event_id": "55555555-5555-5555-5555-555555555555",
            "store_id": "STORE_TEST",
            "camera_id": "CAM_5",
            "visitor_id": "VIS_001",
            "event_type": "BILLING_QUEUE_JOIN",
            "timestamp": "2026-05-29T20:04:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.91,
            "metadata": {"queue_depth": 2, "session_seq": 3}
        }
    ]

    client.post("/events/ingest", json=events)

    response = client.get("/stores/STORE_TEST/metrics")
    data = response.json()

    assert response.status_code == 200
    assert data["unique_visitors"] == 1
    assert data["entry_count"] == 1
    assert data["billing_visitors"] == 1
    assert data["conversion_rate"] == 100.0
    assert data["current_queue_depth"] == 2
    assert data["avg_dwell_per_zone"]["COSMETICS_A"] == 30000.0


def test_staff_exclusion():
    reset_state()

    events = [
        {
            "event_id": "66666666-6666-6666-6666-666666666666",
            "store_id": "STORE_TEST",
            "camera_id": "CAM_4",
            "visitor_id": "STAFF_001",
            "event_type": "ZONE_DWELL",
            "timestamp": "2026-05-29T20:05:00Z",
            "zone_id": "WAREHOUSE",
            "dwell_ms": 30000,
            "is_staff": True,
            "confidence": 0.85,
            "metadata": {"session_seq": 1}
        }
    ]

    client.post("/events/ingest", json=events)

    response = client.get("/stores/STORE_TEST/metrics")
    data = response.json()

    assert data["unique_visitors"] == 0


def test_funnel_endpoint():
    reset_state()

    response = client.get("/stores/STORE_TEST/funnel")

    assert response.status_code == 200
    assert "funnel" in response.json()


def test_heatmap_endpoint():
    reset_state()

    response = client.get("/stores/STORE_TEST/heatmap")

    assert response.status_code == 200
    assert "heatmap" in response.json()


def test_anomalies_endpoint():
    reset_state()

    response = client.get("/stores/STORE_TEST/anomalies")

    assert response.status_code == 200
    assert "active_anomalies" in response.json()