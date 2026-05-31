import json
import uuid
from datetime import datetime, timedelta

INPUT_FILE = "data/all_detected_events.jsonl"
OUTPUT_FILE = "data/enriched_events.jsonl"

CAMERA_ZONE_MAP = {
    "CAM_1": "COSMETICS_A",
    "CAM_2": "COSMETICS_B",
    "CAM_3": None,
    "CAM_4": "WAREHOUSE",
    "CAM_5": "BILLING"
    
}

enriched_events = []

with open(INPUT_FILE, "r") as f:
    for line in f:
        if not line.strip():
            continue

        event = json.loads(line)
        enriched_events.append(event)

        camera_id = event["camera_id"]
        zone_id = CAMERA_ZONE_MAP.get(camera_id)

        if zone_id is None:
            continue

        if zone_id == "WAREHOUSE":
            event["is_staff"] = True
            continue

        visitor_id = event["visitor_id"]
        timestamp = datetime.fromisoformat(event["timestamp"])

        # ZONE_ENTER
        zone_enter = event.copy()
        zone_enter["event_id"] = str(uuid.uuid4())
        zone_enter["event_type"] = "ZONE_ENTER"
        zone_enter["zone_id"] = zone_id
        zone_enter["dwell_ms"] = 0
        zone_enter["metadata"] = {
            **zone_enter.get("metadata", {}),
            "derived_from": event["event_id"],
            "zone_source": camera_id,
            "session_seq": 2
        }
        enriched_events.append(zone_enter)

        # ZONE_DWELL after 30 seconds
        zone_dwell = event.copy()
        zone_dwell["event_id"] = str(uuid.uuid4())
        zone_dwell["event_type"] = "ZONE_DWELL"
        zone_dwell["timestamp"] = (timestamp + timedelta(seconds=30)).isoformat()
        zone_dwell["zone_id"] = zone_id
        zone_dwell["dwell_ms"] = 30000
        zone_dwell["metadata"] = {
            **zone_dwell.get("metadata", {}),
            "derived_from": event["event_id"],
            "zone_source": camera_id,
            "session_seq": 3
        }
        enriched_events.append(zone_dwell)

        # Billing queue event
        if zone_id == "BILLING":
            billing_event = event.copy()
            billing_event["event_id"] = str(uuid.uuid4())
            billing_event["event_type"] = "BILLING_QUEUE_JOIN"
            billing_event["zone_id"] = "BILLING"
            billing_event["dwell_ms"] = 0
            billing_event["metadata"] = {
                **billing_event.get("metadata", {}),
                "derived_from": event["event_id"],
                "queue_depth": 1,
                "session_seq": 4
            }
            enriched_events.append(billing_event)

with open(OUTPUT_FILE, "w") as f:
    for event in enriched_events:
        f.write(json.dumps(event) + "\n")

print(f"Input events: {sum(1 for _ in open(INPUT_FILE))}")
print(f"Enriched events: {len(enriched_events)}")
print(f"Saved to {OUTPUT_FILE}")