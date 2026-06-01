import streamlit as st
import tempfile
import cv2
import uuid
import requests
from datetime import datetime, timezone, timedelta
from ultralytics import YOLO

API_BASE = "http://localhost:8000"
STORE_ID = "STORE_001"

st.set_page_config(page_title="Video Upload Analytics", layout="wide")

st.title("Video Upload Analytics")
st.caption("Upload a CCTV clip, process it with YOLOv8, generate visitor events, and send them to the Store Intelligence API.")

uploaded_file = st.file_uploader(
    "Upload CCTV video",
    type=["mp4", "avi", "mov"]
)

camera_id = st.selectbox(
    "Select camera mapping",
    ["CAM_3 - Entry / Exit", "CAM_1 - Cosmetics Zone A", "CAM_2 - Cosmetics Zone B", "CAM_5 - Billing Counter"]
)

CAMERA_MAP = {
    "CAM_3 - Entry / Exit": "CAM_3",
    "CAM_1 - Cosmetics Zone A": "CAM_1",
    "CAM_2 - Cosmetics Zone B": "CAM_2",
    "CAM_5 - Billing Counter": "CAM_5"
}

ZONE_MAP = {
    "CAM_1": "COSMETICS_A",
    "CAM_2": "COSMETICS_B",
    "CAM_5": "BILLING"
}

ENTRY_LINE_Y = 500
PROCESS_EVERY_N_FRAMES = 10


def generate_event(camera_id, visitor_id, event_type, timestamp, confidence, track_id, zone_id=None, dwell_ms=0):
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": STORE_ID,
        "camera_id": camera_id,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": timestamp.isoformat(),
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": False,
        "confidence": float(confidence),
        "metadata": {
            "track_id": int(track_id),
            "line_y": ENTRY_LINE_Y if camera_id == "CAM_3" else None,
            "queue_depth": 1 if event_type == "BILLING_QUEUE_JOIN" else None,
            "session_seq": 1
        }
    }


def process_uploaded_video(video_path, camera_id):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_no = 0
    previous_positions = {}
    completed_tracks = set()
    events = []

    base_time = datetime.now(timezone.utc)

    progress = st.progress(0)
    status = st.empty()

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_no += 1

        if frame_no % PROCESS_EVERY_N_FRAMES != 0:
            continue

        progress.progress(min(frame_no / max(total_frames, 1), 1.0))
        status.write(f"Processing frame {frame_no}/{total_frames}")

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

            visitor_id = f"UPLOAD_{camera_id}_{track_id:03d}"
            event_type = None
            zone_id = None
            dwell_ms = 0

            if camera_id == "CAM_3":
                if track_id in previous_positions:
                    prev_y = previous_positions[track_id]

                    if prev_y < ENTRY_LINE_Y and center_y >= ENTRY_LINE_Y:
                        event_type = "ENTRY"
                    elif prev_y > ENTRY_LINE_Y and center_y <= ENTRY_LINE_Y:
                        event_type = "EXIT"

            elif camera_id in ["CAM_1", "CAM_2"]:
                if track_id not in completed_tracks:
                    zone_id = ZONE_MAP[camera_id]
                    event_type = "ZONE_DWELL"
                    dwell_ms = 30000

            elif camera_id == "CAM_5":
                if track_id not in completed_tracks:
                    zone_id = "BILLING"
                    event_type = "BILLING_QUEUE_JOIN"
                    dwell_ms = 0

            if event_type and track_id not in completed_tracks:
                events.append(
                    generate_event(
                        camera_id=camera_id,
                        visitor_id=visitor_id,
                        event_type=event_type,
                        timestamp=timestamp,
                        confidence=conf,
                        track_id=track_id,
                        zone_id=zone_id,
                        dwell_ms=dwell_ms
                    )
                )

                if event_type in ["ENTRY", "ZONE_DWELL", "BILLING_QUEUE_JOIN"]:
                    completed_tracks.add(track_id)

            previous_positions[track_id] = center_y

    cap.release()
    progress.progress(1.0)
    status.write("Processing complete")

    return events


if uploaded_file is not None:
    st.video(uploaded_file)

    selected_camera_id = CAMERA_MAP[camera_id]

    if st.button("Process Video and Send Events"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            temp_file.write(uploaded_file.read())
            temp_video_path = temp_file.name

        with st.spinner("Running YOLOv8 detection..."):
            generated_events = process_uploaded_video(temp_video_path, selected_camera_id)

        st.success(f"Generated {len(generated_events)} events")

        if generated_events:
            response = requests.post(
                f"{API_BASE}/events/ingest",
                json=generated_events
            )

            st.write("API Response:")
            st.json(response.json())

            metrics = requests.get(f"{API_BASE}/stores/{STORE_ID}/metrics").json()
            st.subheader("Updated Metrics")
            st.json(metrics)
        else:
            st.warning("No events were generated from this clip.")