# PROMPT:
# Generate funnel endpoint tests verifying session-based counts and that REENTRY
# does not double-count visitors in the funnel.
#
# CHANGES MADE:
# Added explicit REENTRY + ENTRY pair for same visitor_id and asserted entry count stays 1.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_reentry_does_not_double_count():
    events = [
        {
            "event_id": "22222222-2222-2222-2222-222222222201",
            "store_id": "STORE_001",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_RETURN",
            "event_type": "ENTRY",
            "timestamp": "2026-05-29T20:00:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"session_seq": 1},
        },
        {
            "event_id": "22222222-2222-2222-2222-222222222202",
            "store_id": "STORE_001",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_RETURN",
            "event_type": "EXIT",
            "timestamp": "2026-05-29T20:10:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.9,
            "metadata": {"session_seq": 2},
        },
        {
            "event_id": "22222222-2222-2222-2222-222222222203",
            "store_id": "STORE_001",
            "camera_id": "CAM_1",
            "visitor_id": "VIS_RETURN",
            "event_type": "REENTRY",
            "timestamp": "2026-05-29T20:20:00Z",
            "zone_id": None,
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.85,
            "metadata": {"session_seq": 3},
        },
        {
            "event_id": "22222222-2222-2222-2222-222222222204",
            "store_id": "STORE_001",
            "camera_id": "CAM_2",
            "visitor_id": "VIS_RETURN",
            "event_type": "ZONE_ENTER",
            "timestamp": "2026-05-29T20:25:00Z",
            "zone_id": "MAIN_FLOOR",
            "dwell_ms": 0,
            "is_staff": False,
            "confidence": 0.88,
            "metadata": {"session_seq": 4},
        },
    ]
    client.post("/events/ingest", json=events)
    funnel = client.get("/stores/STORE_001/funnel").json()
    assert funnel["funnel"]["entry"] == 1
    assert funnel["funnel"]["zone_visit"] == 1
