# PROMPT:
# Create tests for GET /stores/{id}/anomalies covering queue spike, conversion drop,
# and dead zone detection with severity and suggested_action fields.
#
# CHANGES MADE:
# Seeded queue join events with depth>=3 and verified BILLING_QUEUE_SPIKE anomaly type.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_queue_spike_anomaly():
    events = []
    for i in range(4):
        events.append(
            {
                "event_id": f"33333333-3333-3333-3333-33333333330{i}",
                "store_id": "STORE_001",
                "camera_id": "CAM_3",
                "visitor_id": f"VIS_Q{i}",
                "event_type": "BILLING_QUEUE_JOIN",
                "timestamp": f"2026-05-29T23:00:{10+i}Z",
                "zone_id": "BILLING",
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {"queue_depth": 3, "session_seq": 1},
            }
        )
    client.post("/events/ingest", json=events)
    resp = client.get("/stores/STORE_001/anomalies")
    types = [a["type"] for a in resp.json()["active_anomalies"]]
    assert "BILLING_QUEUE_SPIKE" in types
    assert all("suggested_action" in a for a in resp.json()["active_anomalies"])
