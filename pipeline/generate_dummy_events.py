import json
import uuid
from datetime import datetime, timezone, timedelta

events = []

base_time = datetime.now(timezone.utc)

for i in range(10):
    visitor_id = f"VIS_{i+1:03d}"

    events.append({
        "event_id": str(uuid.uuid4()),
        "store_id": "STORE_001",
        "camera_id": "CAM_1",
        "visitor_id": visitor_id,
        "event_type": "ENTRY",
        "timestamp": (base_time + timedelta(seconds=i * 10)).isoformat(),
        "zone_id": None,
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.90,
        "metadata": {
            "session_seq": 1
        }
    })

    events.append({
        "event_id": str(uuid.uuid4()),
        "store_id": "STORE_001",
        "camera_id": "CAM_2",
        "visitor_id": visitor_id,
        "event_type": "ZONE_DWELL",
        "timestamp": (base_time + timedelta(seconds=i * 10 + 40)).isoformat(),
        "zone_id": "MAIN_FLOOR",
        "dwell_ms": 30000,
        "is_staff": False,
        "confidence": 0.88,
        "metadata": {
            "session_seq": 2
        }
    })

with open("data/sample_events.jsonl", "w") as f:
    for event in events:
        f.write(json.dumps(event) + "\n")

print("Generated data/sample_events.jsonl")