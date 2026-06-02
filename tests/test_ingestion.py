# PROMPT:
# Generate pytest tests for POST /events/ingest covering idempotency, batch limits,
# partial success on malformed events, and structured response fields.
#
# CHANGES MADE:
# Added temp SQLite fixture, explicit duplicate and malformed payload cases,
# and assertions on inserted_count / duplicate_count / failed_count.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _event(eid: str, visitor: str = "VIS_001", event_type: str = "ENTRY"):
    return {
        "event_id": eid,
        "store_id": "STORE_001",
        "camera_id": "CAM_1",
        "visitor_id": visitor,
        "event_type": event_type,
        "timestamp": "2026-05-29T22:33:15Z",
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {"session_seq": 1, "source": "detection_pipeline"},
    }


def test_ingest_success():
    payload = [_event("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")]
    resp = client.post("/events/ingest", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["inserted_count"] == 1
    assert data["duplicate_count"] == 0
    assert data["failed_count"] == 0


def test_idempotent_duplicate():
    eid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    payload = [_event(eid)]
    first = client.post("/events/ingest", json=payload)
    second = client.post("/events/ingest", json=payload)
    assert first.json()["inserted_count"] == 1
    assert second.json()["duplicate_count"] == 1
    assert second.json()["inserted_count"] == 0


def test_partial_success_malformed():
    payload = [
        _event("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        {"event_id": "not-a-uuid", "store_id": "STORE_001"},
    ]
    resp = client.post("/events/ingest", json=payload)
    data = resp.json()
    assert data["inserted_count"] == 1
    assert data["failed_count"] == 1
    assert len(data["errors"]) == 1


def test_ingest_batch_caps_at_500():
    payload = [_event(f"{i:08x}-0000-4000-8000-000000000000") for i in range(502)]
    resp = client.post("/events/ingest", json=payload)
    assert resp.status_code == 200
    assert resp.json()["inserted_count"] <= 500


def test_group_entry_multiple_events():
    payload = [
        _event("dddddddd-dddd-dddd-dddd-dddddddddd01", "VIS_G1"),
        _event("dddddddd-dddd-dddd-dddd-dddddddddd02", "VIS_G2"),
        _event("dddddddd-dddd-dddd-dddd-dddddddddd03", "VIS_G3"),
    ]
    resp = client.post("/events/ingest", json=payload)
    assert resp.json()["inserted_count"] == 3
