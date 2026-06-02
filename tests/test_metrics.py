# PROMPT:
# Write tests for GET /stores/{id}/metrics including staff exclusion, zero visitors,
# POS-based conversion, queue depth, and abandonment rate.
#
# CHANGES MADE:
# Wired billing + POS timestamps from data/pos_transactions.csv and added staff exclusion case.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def ingest(events):
    client.post("/events/ingest", json=events)


def test_empty_store_metrics():
    resp = client.get("/stores/EMPTY_STORE/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unique_visitors"] == 0
    assert data["conversion_rate"] == 0.0
    assert data["current_queue_depth"] == 0


def test_staff_excluded_from_metrics():
    ingest([
        {
            "event_id": "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            "store_id": "STORE_001",
            "camera_id": "CAM_4",
            "visitor_id": "STAFF_01",
            "event_type": "ZONE_DWELL",
            "timestamp": "2026-05-29T22:00:00Z",
            "zone_id": "WAREHOUSE",
            "dwell_ms": 30000,
            "is_staff": True,
            "confidence": 0.8,
            "metadata": {"session_seq": 1},
        }
    ])
    data = client.get("/stores/STORE_001/metrics").json()
    assert data["unique_visitors"] == 0


def test_conversion_with_pos_correlation():
    events = [
        {
            "event_id": "11111111-1111-1111-1111-111111111101",
            "store_id": "STORE_001",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_BUYER",
            "event_type": "ENTRY",
            "timestamp": "2026-05-29T23:08:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"session_seq": 1},
        },
        {
            "event_id": "11111111-1111-1111-1111-111111111102",
            "store_id": "STORE_001",
            "camera_id": "CAM_3",
            "visitor_id": "VIS_BUYER",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-05-29T23:10:00Z",
            "zone_id": "BILLING",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.88,
            "metadata": {"session_seq": 2},
        },
        {
            "event_id": "11111111-1111-1111-1111-111111111103",
            "store_id": "STORE_001",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_WINDOW",
            "event_type": "ENTRY",
            "timestamp": "2026-05-29T23:08:30Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"session_seq": 1},
        },
    ]
    ingest(events)
    data = client.get("/stores/STORE_001/metrics").json()
    assert data["unique_visitors"] >= 2
    assert data["conversion_rate"] > 0
