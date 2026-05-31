import cv2
import json
import uuid
import os
from datetime import datetime, timezone, timedelta
from ultralytics import YOLO

VIDEO_FILE = os.getenv("VIDEO_FILE", "CAM 1.mp4")
VIDEO_PATH = f"data/videos/{VIDEO_FILE}"
OUTPUT_PATH = f"data/{VIDEO_FILE.replace('.mp4', '')}_events.jsonl"

STORE_ID = "STORE_001"
CAMERA_ID = VIDEO_FILE.replace(".mp4", "").replace(" ", "_")

ENTRY_LINE_Y = 500
COOLDOWN_SECONDS = 5

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(VIDEO_PATH)

fps = cap.get(cv2.CAP_PROP_FPS)
frame_no = 0
base_time = datetime.now(timezone.utc)

previous_positions = {}
visitor_map = {}
last_event_for_track = {}
completed_tracks = set()
events = []

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_no += 1

    if frame_no % 5 != 0:
        continue

    results = model.track(
        frame,
        persist=True,
        classes=[0],
        verbose=False
    )

    if results[0].boxes.id is None:
        continue

    boxes = results[0].boxes.xyxy.cpu().numpy()
    track_ids = results[0].boxes.id.cpu().numpy()
    confidences = results[0].boxes.conf.cpu().numpy()

    timestamp = base_time + timedelta(seconds=frame_no / fps)

    for box, track_id, conf in zip(boxes, track_ids, confidences):
        x1, y1, x2, y2 = box
        center_y = int((y1 + y2) / 2)
        track_id = int(track_id)

        if track_id not in visitor_map:
            visitor_map[track_id] = f"VIS_{CAMERA_ID}_{track_id:03d}"

        visitor_id = visitor_map[track_id]
        event_type = None

        if track_id in previous_positions:
            prev_y = previous_positions[track_id]

            if CAMERA_ID == "CAM_3":
                if prev_y < ENTRY_LINE_Y and center_y >= ENTRY_LINE_Y:
                    event_type = "ENTRY"
                elif prev_y > ENTRY_LINE_Y and center_y <= ENTRY_LINE_Y:
                    event_type = "EXIT"

            elif CAMERA_ID in ["CAM_1", "CAM_2", "CAM_5"]:
                event_type = "ZONE_OBSERVED"

            elif CAMERA_ID == "CAM_4":
                event_type = None

            if event_type:
                if event_type in ["ENTRY", "ZONE_OBSERVED"] and track_id in completed_tracks:
                    previous_positions[track_id] = center_y
                    continue

                last_time = last_event_for_track.get(track_id)

                if last_time is not None:
                    gap = (timestamp - last_time).total_seconds()
                    if gap < COOLDOWN_SECONDS:
                        previous_positions[track_id] = center_y
                        continue

                last_event_for_track[track_id] = timestamp

                events.append({
                    "event_id": str(uuid.uuid4()),
                    "store_id": STORE_ID,
                    "camera_id": CAMERA_ID,
                    "visitor_id": visitor_id,
                    "event_type": event_type,
                    "timestamp": timestamp.isoformat(),
                    "zone_id": None,
                    "dwell_ms": 0,
                    "is_staff": CAMERA_ID == "CAM_4",
                    "confidence": float(conf),
                    "metadata": {
                        "track_id": track_id,
                        "line_y": ENTRY_LINE_Y if CAMERA_ID == "CAM_3" else None,
                        "session_seq": 1
                    }
                })

                if event_type in ["ENTRY", "ZONE_OBSERVED"]:
                    completed_tracks.add(track_id)

        previous_positions[track_id] = center_y

cap.release()

with open(OUTPUT_PATH, "w") as f:
    for event in events:
        f.write(json.dumps(event) + "\n")

print(f"Generated {len(events)} events")
print(f"Saved to {OUTPUT_PATH}")