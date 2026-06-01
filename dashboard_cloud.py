import streamlit as st
import requests
import pandas as pd

API_BASE = "https://store-intelligence-api-hl9i.onrender.com"
STORE_ID = "STORE_001"


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
            "Pipeline Evidence": f"{total_events} events available",
        },
        {
            "Check": "ENTRY events generated",
            "Status": "PASS" if entry_count > 0 else "WARN",
            "Pipeline Evidence": f"{entry_count} ENTRY events",
        },
        {
            "Check": "EXIT events generated",
            "Status": "PASS" if exit_count > 0 else "WARN",
            "Pipeline Evidence": f"{exit_count} EXIT events",
        },
        {
            "Check": "Visitor tracking",
            "Status": "PASS" if unique_visitors > 0 else "WARN",
            "Pipeline Evidence": f"{unique_visitors} tracked visitor identities",
        },
        {
            "Check": "Zone detection",
            "Status": "PASS" if zone_count > 0 else "WARN",
            "Pipeline Evidence": f"{zone_count} zone-engagement detections",
        },
        {
            "Check": "Billing detection",
            "Status": "PASS" if billing_visitors > 0 else "WARN",
            "Pipeline Evidence": f"{billing_visitors} billing-zone detections",
        },
        {
            "Check": "Heatmap generation",
            "Status": "PASS" if len(heatmap.get("heatmap", [])) > 0 else "WARN",
            "Pipeline Evidence": f"{len(heatmap.get('heatmap', []))} active zones",
        },
        {
            "Check": "Group handling",
            "Status": "SUPPORTED",
            "Pipeline Evidence": "Multiple people can receive separate track IDs",
        },
        {
            "Check": "Partial occlusion handling",
            "Status": "SUPPORTED",
            "Pipeline Evidence": "Detection confidence is retained for review",
        },
        {
            "Check": "Re-entry handling",
            "Status": "LIMITED",
            "Pipeline Evidence": "Planned improvement using DeepSORT/OSNet Re-ID",
        },
        {
            "Check": "Staff exclusion",
            "Status": "PARTIAL",
            "Pipeline Evidence": "Current prototype uses camera/zone-based separation",
        },
    ]

    return pd.DataFrame(checks)


st.set_page_config(
    page_title="Store Intelligence Dashboard",
    page_icon="🏪",
    layout="wide",
)

st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
# Store Intelligence Dashboard

<div class="small-text">
Cloud analytics dashboard connected to the deployed Store Intelligence API.
The local version supports YOLOv8 CCTV video processing and event generation.
</div>
""",
    unsafe_allow_html=True,
)

if st.button("Refresh Dashboard"):
    st.rerun()

try:
    metrics, funnel, heatmap, anomalies, health = load_api_data()
except Exception:
    st.error("API is not reachable. Please check the deployed Render API.")
    st.stop()

st.divider()

col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Visitors", metrics.get("unique_visitors", 0))
col2.metric("Entries", metrics.get("entry_count", 0))
col3.metric("Billing Visitors", metrics.get("billing_visitors", 0))
col4.metric("Conversion Rate", f'{metrics.get("conversion_rate", 0)}%')
col5.metric("Queue Depth", metrics.get("current_queue_depth", 0))

st.divider()

st.subheader("Business Insights")

insight_col1, insight_col2, insight_col3 = st.columns(3)

with insight_col1:
    if metrics.get("conversion_rate", 0) < 20:
        st.warning(
            f"Conversion is low at {metrics.get('conversion_rate', 0)}%. "
            "Visitors are engaging but checkout completion needs attention."
        )
    else:
        st.success(f"Conversion is healthy at {metrics.get('conversion_rate', 0)}%.")

with insight_col2:
    if metrics.get("billing_visitors", 0) > 0:
        st.success(f"{metrics.get('billing_visitors', 0)} visitors reached the billing zone.")
    else:
        st.info("No billing-zone visitors detected yet.")

with insight_col3:
    if metrics.get("current_queue_depth", 0) >= 3:
        st.warning("Billing queue depth is high. Consider opening another counter.")
    else:
        st.success("Billing queue is currently under control.")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Conversion Funnel")

    funnel_data = funnel.get("funnel", {})

    funnel_df = pd.DataFrame(
        [
            {"Stage": "Entry", "Count": funnel_data.get("entry", 0)},
            {"Stage": "Zone Visit", "Count": funnel_data.get("zone_visit", 0)},
            {"Stage": "Billing Queue", "Count": funnel_data.get("billing_queue", 0)},
            {"Stage": "Purchase", "Count": funnel_data.get("purchase", 0)},
        ]
    )

    st.dataframe(funnel_df, use_container_width=True, hide_index=True)
    st.bar_chart(funnel_df.set_index("Stage"))

    dropoff = funnel.get("dropoff_percent", {})

    st.caption(
        f"Entry → Zone Drop-off: {dropoff.get('entry_to_zone', 0)}% | "
        f"Zone → Billing Drop-off: {dropoff.get('zone_to_billing', 0)}%"
    )

with right:
    st.subheader("Zone Heatmap")

    heatmap_df = pd.DataFrame(heatmap.get("heatmap", []))

    if not heatmap_df.empty:
        heatmap_display = heatmap_df[
            [
                "zone_id",
                "visit_frequency",
                "avg_dwell_ms",
                "normalized_score",
                "data_confidence",
            ]
        ].copy()

        heatmap_display["avg_dwell_sec"] = (
            heatmap_display["avg_dwell_ms"] / 1000
        ).round(2)

        heatmap_display = heatmap_display[
            [
                "zone_id",
                "visit_frequency",
                "avg_dwell_sec",
                "normalized_score",
                "data_confidence",
            ]
        ]

        st.dataframe(heatmap_display, use_container_width=True, hide_index=True)
        st.bar_chart(heatmap_display.set_index("zone_id")["normalized_score"])
    else:
        st.info("No heatmap data available yet.")

st.divider()

st.subheader("Store Layout Intelligence")

layout_col1, layout_col2, layout_col3 = st.columns(3)

zone_lookup = {}

if "heatmap_df" in locals() and not heatmap_df.empty:
    for _, row in heatmap_df.iterrows():
        zone_lookup[row["zone_id"]] = row


def zone_card(zone_name, title):
    data = zone_lookup.get(zone_name)

    if data is not None:
        visits = int(data["visit_frequency"])
        dwell = round(data["avg_dwell_ms"] / 1000, 2)
        score = round(data["normalized_score"], 2)

        st.markdown(
            f"""
### {title}

**Zone ID:** `{zone_name}`  
**Visits:** {visits}  
**Avg Dwell:** {dwell} sec  
**Engagement Score:** {score}/100
"""
        )
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
    dwell_df = pd.DataFrame(
        [
            {
                "Zone": zone,
                "Avg Dwell (sec)": round(dwell / 1000, 2),
            }
            for zone, dwell in dwell_data.items()
        ]
    )

    st.dataframe(dwell_df, use_container_width=True, hide_index=True)
    st.bar_chart(dwell_df.set_index("Zone"))
else:
    st.info("No dwell data available.")

st.divider()

st.subheader("Detection Verification")

verification_df = get_detection_verification()

st.dataframe(
    verification_df,
    use_container_width=True,
    hide_index=True,
)

pass_count = len(verification_df[verification_df["Status"] == "PASS"])
supported_count = len(verification_df[verification_df["Status"] == "SUPPORTED"])

v1, v2, v3 = st.columns(3)

v1.metric("Passed Checks", pass_count)
v2.metric("Supported Features", supported_count)
v3.metric("Total Checks", len(verification_df))

st.divider()

col7, col8 = st.columns(2)

with col7:
    st.subheader("Operational Alerts")

    if anomalies.get("active_anomalies", []):
        for anomaly in anomalies["active_anomalies"]:
            title = anomaly["type"].replace("_", " ").title()
            severity = anomaly["severity"]
            action = anomaly["suggested_action"]

            color = "#ef4444" if severity == "CRITICAL" else "#f59e0b"

            st.markdown(
                f"""
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
            """,
                unsafe_allow_html=True,
            )
    else:
        st.success("No active operational alerts.")

with col8:
    st.subheader("System Health")

    if health.get("status") == "ok":
        st.success("System Healthy")
    else:
        st.warning("System Warning")

    st.json(health)

st.divider()

st.caption(
    "Store Intelligence Platform | CCTV Event Analytics | FastAPI | Streamlit | Render"
)