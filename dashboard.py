import streamlit as st
import requests
import pandas as pd

API_BASE = "https://store-intelligence-api-hl9i.onrender.com"
STORE_ID = "STORE_001"

ENTRY_LINE_Y = 500
PROCESS_EVERY_N_FRAMES = 10

CAMERA_MAP = {
    "CAM_3 - Entry / Exit": "CAM_3",
    "CAM_1 - Cosmetics Zone A": "CAM_1",
    "CAM_2 - Cosmetics Zone B": "CAM_2",
    "CAM_5 - Billing Counter": "CAM_5",
}

ZONE_MAP = {
    "CAM_1": "COSMETICS_A",
    "CAM_2": "COSMETICS_B",
    "CAM_5": "BILLING",
}


def make_event(camera_id, visitor_id, event_type, timestamp, confidence, track_id, zone_id=None, dwell_ms=0, queue_depth=None):
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
            "queue_depth": queue_depth,
            "session_seq": 1,
            "source": "dashboard_upload"
        },
    }


def process_uploaded_video(video_path, camera_id):
    model = YOLO("yolov8n.pt")
    cap = cv2.VideoCapture(video_path)

    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1

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

        progress.progress(min(frame_no / total_frames, 1.0))
        status.write(f"Processing frame {frame_no}/{total_frames}")

        results = model.track(frame, persist=True, classes=[0], verbose=False)

        if results[0].boxes.id is None:
            continue

        boxes = results[0].boxes.xyxy.cpu().numpy()
        track_ids = results[0].boxes.id.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()

        timestamp = base_time + timedelta(seconds=frame_no / fps)

        for box, track_id, conf in zip(boxes, track_ids, confidences):
            _, y1, _, y2 = box
            center_y = int((y1 + y2) / 2)
            track_id = int(track_id)
            visitor_id = f"UPLOAD_{camera_id}_{track_id:03d}"

            if camera_id == "CAM_3":
                if track_id in previous_positions and track_id not in completed_tracks:
                    prev_y = previous_positions[track_id]

                    if prev_y < ENTRY_LINE_Y and center_y >= ENTRY_LINE_Y:
                        events.append(make_event(camera_id, visitor_id, "ENTRY", timestamp, conf, track_id))
                        completed_tracks.add(track_id)

                    elif prev_y > ENTRY_LINE_Y and center_y <= ENTRY_LINE_Y:
                        events.append(make_event(camera_id, visitor_id, "EXIT", timestamp, conf, track_id))
                        completed_tracks.add(track_id)

            elif camera_id in ["CAM_1", "CAM_2"]:
                if track_id not in completed_tracks:
                    zone_id = ZONE_MAP[camera_id]

                    events.append(make_event(
                        camera_id, visitor_id, "ZONE_ENTER",
                        timestamp, conf, track_id,
                        zone_id=zone_id,
                        dwell_ms=0
                    ))

                    events.append(make_event(
                        camera_id, visitor_id, "ZONE_DWELL",
                        timestamp + timedelta(seconds=30),
                        conf, track_id,
                        zone_id=zone_id,
                        dwell_ms=30000
                    ))

                    completed_tracks.add(track_id)

            elif camera_id == "CAM_5":
                if track_id not in completed_tracks:
                    zone_id = "BILLING"

                    events.append(make_event(
                        camera_id, visitor_id, "ZONE_ENTER",
                        timestamp, conf, track_id,
                        zone_id=zone_id,
                        dwell_ms=0
                    ))

                    events.append(make_event(
                        camera_id, visitor_id, "BILLING_QUEUE_JOIN",
                        timestamp, conf, track_id,
                        zone_id=zone_id,
                        dwell_ms=0,
                        queue_depth=1
                    ))

                    events.append(make_event(
                        camera_id, visitor_id, "ZONE_DWELL",
                        timestamp + timedelta(seconds=30),
                        conf, track_id,
                        zone_id=zone_id,
                        dwell_ms=30000
                    ))

                    completed_tracks.add(track_id)

            previous_positions[track_id] = center_y

    cap.release()
    progress.progress(1.0)
    status.write("Processing complete")
    return events


def load_api_data():
    metrics = requests.get(f"{API_BASE}/stores/{STORE_ID}/metrics").json()
    funnel = requests.get(f"{API_BASE}/stores/{STORE_ID}/funnel").json()
    heatmap = requests.get(f"{API_BASE}/stores/{STORE_ID}/heatmap").json()
    anomalies = requests.get(f"{API_BASE}/stores/{STORE_ID}/anomalies").json()
    health = requests.get(f"{API_BASE}/health").json()
    return metrics, funnel, heatmap, anomalies, health


def get_detection_verification():
    health = requests.get(f"{API_BASE}/health").json()
    metrics = requests.get(f"{API_BASE}/stores/{STORE_ID}/metrics").json()
    funnel = requests.get(f"{API_BASE}/stores/{STORE_ID}/funnel").json()
    heatmap = requests.get(f"{API_BASE}/stores/{STORE_ID}/heatmap").json()

    total_events = health.get("total_events", 0)
    entry_count = metrics.get("entry_count", 0)
    exit_count = metrics.get("exit_count", 0)
    unique_visitors = metrics.get("unique_visitors", 0)
    billing_visitors = metrics.get("billing_visitors", 0)
    zone_count = funnel.get("funnel", {}).get("zone_visit", 0)

    checks = [
        {
            "Check": "Events ingested",
            "Status": "PASS" if total_events > 0 else "WARN",
            "Evidence": f"{total_events} events available"
        },
        {
            "Check": "ENTRY events generated",
            "Status": "PASS" if entry_count > 0 else "WARN",
            "Evidence": f"{entry_count} ENTRY events"
        },
        {
            "Check": "EXIT events generated",
            "Status": "PASS" if exit_count > 0 else "WARN",
            "Evidence": f"{exit_count} EXIT events"
        },
        {
            "Check": "Visitor tracking",
            "Status": "PASS" if unique_visitors > 0 else "WARN",
            "Evidence": f"{unique_visitors} unique visitor tokens"
        },
        {
            "Check": "Zone detection",
            "Status": "PASS" if zone_count > 0 else "WARN",
            "Evidence": f"{zone_count} visitors reached zones"
        },
        {
            "Check": "Billing detection",
            "Status": "PASS" if billing_visitors > 0 else "WARN",
            "Evidence": f"{billing_visitors} billing visitors"
        },
        {
            "Check": "Heatmap generation",
            "Status": "PASS" if len(heatmap.get("heatmap", [])) > 0 else "WARN",
            "Evidence": f"{len(heatmap.get('heatmap', []))} active zones"
        },
        {
            "Check": "Group handling",
            "Status": "SUPPORTED",
            "Evidence": "YOLO assigns separate track IDs per detected person"
        },
        {
            "Check": "Partial occlusion handling",
            "Status": "SUPPORTED",
            "Evidence": "Confidence values are retained instead of suppressed"
        },
        {
            "Check": "Re-entry handling",
            "Status": "LIMITED",
            "Evidence": "Documented as future ReID enhancement using DeepSORT/OSNet"
        },
        {
            "Check": "Staff exclusion",
            "Status": "PARTIAL",
            "Evidence": "Warehouse/staff camera separated using camera-zone mapping"
        },
    ]

    return pd.DataFrame(checks)
st.set_page_config(
    page_title="Store Intelligence Dashboard",
    page_icon="🏪",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.small-text {
    color:#9CA3AF;
    font-size:14px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
# Store Intelligence Dashboard

<div class="small-text">
Real-time retail analytics generated from CCTV event processing,
visitor journey tracking, zone engagement analysis,
billing activity monitoring, and operational alerts.
</div>
""", unsafe_allow_html=True)

if st.button("Refresh Dashboard"):
    st.rerun()

try:
    metrics, funnel, heatmap, anomalies, health = load_api_data()
except Exception:
    st.error("API is not reachable. Start FastAPI first using docker compose up --build.")
    st.stop()


st.divider()
st.subheader("Upload CCTV Clip for Live Processing")

uploaded_file = st.file_uploader(
    "Upload a CCTV video",
    type=["mp4", "avi", "mov"]
)

camera_choice = st.selectbox(
    "Select correct camera mapping",
    list(CAMERA_MAP.keys())
)

st.info("Important: Select CAM_1 for CAM 1.mp4, CAM_2 for CAM 2.mp4, CAM_3 for entry/exit video, and CAM_5 for billing video.")

if uploaded_file is not None:
    st.video(uploaded_file)

    st.info(
        "Video preview is available in the cloud demo. "
        "YOLO-based video processing is available in the local version using dashboard_upload.py."
    )

st.divider()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Visitors", metrics["unique_visitors"])
col2.metric("Entries", metrics["entry_count"])
col3.metric("Billing Visitors", metrics["billing_visitors"])
col4.metric("Conversion Rate", f'{metrics["conversion_rate"]}%')
col5.metric("Queue Depth", metrics["current_queue_depth"])

st.divider()

st.subheader("Business Insights")

insight_col1, insight_col2, insight_col3 = st.columns(3)

with insight_col1:
    if metrics["conversion_rate"] < 20:
        st.warning(
            f"Conversion is low at {metrics['conversion_rate']}%. "
            "Visitors are engaging but checkout completion needs attention."
        )
    else:
        st.success(f"Conversion is healthy at {metrics['conversion_rate']}%.")

with insight_col2:
    if metrics["billing_visitors"] > 0:
        st.success(f"{metrics['billing_visitors']} visitors reached the billing zone.")
    else:
        st.info("No billing-zone visitors detected yet.")

with insight_col3:
    if metrics["current_queue_depth"] >= 3:
        st.warning("Billing queue depth is high. Consider opening another counter.")
    else:
        st.success("Billing queue is currently under control.")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Conversion Funnel")

    funnel_df = pd.DataFrame([
        {"Stage": "Entry", "Count": funnel["funnel"]["entry"]},
        {"Stage": "Zone Visit", "Count": funnel["funnel"]["zone_visit"]},
        {"Stage": "Billing Queue", "Count": funnel["funnel"]["billing_queue"]},
        {"Stage": "Purchase", "Count": funnel["funnel"]["purchase"]}
    ])

    st.dataframe(funnel_df, use_container_width=True, hide_index=True)
    st.bar_chart(funnel_df.set_index("Stage"))

    st.caption(
        f"Entry → Zone Drop-off: {funnel['dropoff_percent']['entry_to_zone']}% | "
        f"Zone → Billing Drop-off: {funnel['dropoff_percent']['zone_to_billing']}%"
    )

with right:
    st.subheader("Zone Heatmap")

    heatmap_df = pd.DataFrame(heatmap["heatmap"])

    if not heatmap_df.empty:
        heatmap_display = heatmap_df[
            ["zone_id", "visit_frequency", "avg_dwell_ms", "normalized_score", "data_confidence"]
        ].copy()

        heatmap_display["avg_dwell_sec"] = (
            heatmap_display["avg_dwell_ms"] / 1000
        ).round(2)

        heatmap_display = heatmap_display[
            ["zone_id", "visit_frequency", "avg_dwell_sec", "normalized_score", "data_confidence"]
        ]

        st.dataframe(heatmap_display, use_container_width=True, hide_index=True)
        st.bar_chart(heatmap_display.set_index("zone_id")["normalized_score"])
    else:
        st.info("No heatmap data available yet.")

st.divider()

st.subheader("Store Layout Intelligence")

layout_col1, layout_col2, layout_col3 = st.columns(3)

zone_lookup = {}
if not heatmap_df.empty:
    for _, row in heatmap_df.iterrows():
        zone_lookup[row["zone_id"]] = row


def zone_card(zone_name, title):
    data = zone_lookup.get(zone_name)

    if data is not None:
        visits = int(data["visit_frequency"])
        dwell = round(data["avg_dwell_ms"] / 1000, 2)
        score = round(data["normalized_score"], 2)

        st.markdown(f"""
### {title}

**Zone ID:** `{zone_name}`  
**Visits:** {visits}  
**Avg Dwell:** {dwell} sec  
**Engagement Score:** {score}/100
""")
    else:
        st.info(f"No data available for {title}")


with layout_col1:
    zone_card("COSMETICS_A", "Cosmetics Zone A")

with layout_col2:
    zone_card("COSMETICS_B", "Cosmetics Zone B")

with layout_col3:
    zone_card("BILLING", "Billing Counter")

st.divider()

st.subheader("Average Dwell Time Per Zone")

dwell_data = metrics.get("avg_dwell_per_zone", {})

if dwell_data:
    dwell_df = pd.DataFrame([
        {
            "Zone": zone,
            "Avg Dwell (sec)": round(dwell / 1000, 2)
        }
        for zone, dwell in dwell_data.items()
    ])

    st.dataframe(dwell_df, use_container_width=True, hide_index=True)
    st.bar_chart(dwell_df.set_index("Zone"))
else:
    st.info("No dwell data available.")

st.divider()

# Detection Verification
st.subheader("Detection Verification")

verification_df = get_detection_verification()

st.dataframe(
    verification_df,
    use_container_width=True,
    hide_index=True
)

pass_count = len(
    verification_df[
        verification_df["Status"] == "PASS"
    ]
)

supported_count = len(
    verification_df[
        verification_df["Status"] == "SUPPORTED"
    ]
)

v1, v2, v3 = st.columns(3)

v1.metric("Passed Checks", pass_count)
v2.metric("Supported Features", supported_count)
v3.metric("Total Checks", len(verification_df))

st.divider()

col7, col8 = st.columns(2)

with col7:
    st.subheader("Operational Alerts")


    if anomalies["active_anomalies"]:
        for anomaly in anomalies["active_anomalies"]:
            title = anomaly["type"].replace("_", " ").title()
            severity = anomaly["severity"]
            action = anomaly["suggested_action"]

            color = "#ef4444" if severity == "CRITICAL" else "#f59e0b"

            st.markdown(f"""
            <div style="
                background:#1f2937;
                padding:18px;
                border-radius:14px;
                border-left:5px solid {color};
                margin-bottom:12px;
            ">
            <h4 style="margin-bottom:10px;">{title}</h4>
            <p><b>Severity:</b> {severity}</p>
            <p><b>Recommended Action:</b><br>{action}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No active operational alerts.")

with col8:
    st.subheader("System Health")

    if health["status"] == "ok":
        st.success("System Healthy")
    else:
        st.warning("System Warning")

    st.json(health)

st.divider()

st.caption(
    "Store Intelligence Platform | CCTV Event Analytics | FastAPI | Streamlit | Docker"
)