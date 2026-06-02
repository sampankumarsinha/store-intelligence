# Engineering Choices

## 1. Detection model choice

### Options considered

| Option | Pros | Cons |
|--------|------|------|
| YOLOv8n + Ultralytics track | Fast, easy, good person class | Needs GPU/CPU time per frame |
| RT-DETR | Accuracy | Heavier, slower on CPU |
| MediaPipe | Lightweight | Weaker in crowded retail scenes |
| VLM zone/staff labelling | Flexible semantics | Cost, latency, non-deterministic |

### What AI suggested

Use YOLOv8 with ByteTrack and optionally a VLM to label staff uniforms and zone semantics from frames.

### What I chose and why

**YOLOv8n + Centroid/IoU tracker** with rule-based zones from `store_layout.json`.

- Matches typical CCTV deployment (15fps, 1080p) with acceptable latency.
- `yolov8n.pt` is small and runs on CPU for challenge clips.
- Zone polygons and entry lines are already in layout JSON — a VLM adds little over deterministic geometry.
- **Override:** I did not use ByteTrack as a separate dependency; Ultralytics built-in track IDs plus our CentroidTracker fallback keeps dependencies simpler while still separating group members by distinct boxes/track IDs.

Staff uses a **uniform color heuristic** (dark, low-saturation upper body) rather than a VLM — documented as a known limitation in README.

---

## 2. Event schema rationale

### Design

Flat JSON events with typed `event_type`, optional `zone_id`, `dwell_ms`, and rich `metadata` (queue_depth, sku_zone, session_seq, group_candidate, track_id, source).

### Why this supports all API queries

| API need | Schema support |
|----------|----------------|
| Unique visitors / funnel | `visitor_id`, ENTRY/REENTRY/EXIT |
| Zone dwell / heatmap | ZONE_* + `dwell_ms` + `zone_id` |
| Queue metrics | BILLING_QUEUE_* + `metadata.queue_depth` |
| Staff exclusion | `is_staff` flag (events retained) |
| POS conversion | BILLING zone events + timestamps |
| Idempotent ingest | UUID `event_id` |
| Quality audit | `confidence` always present; low conf kept |

### Confidence and metadata

- **Confidence** is model/detection certainty — never dropped silently; group crossings may scale down confidence.
- **group_candidate** marks uncertain group separations for downstream review.
- **session_seq** orders events within a visit for debugging and future session analytics.

---

## 3. API architecture choice

### Options considered

| Option | Pros | Cons |
|--------|------|------|
| Monolith in-memory dict | Trivial | No persistence, no 503 semantics |
| FastAPI + SQLite | Single container, SQL queries | Not horizontally scaled |
| FastAPI + PostgreSQL + Redis | Production scale | Ops overhead for take-home |

### What AI suggested

PostgreSQL for events, Redis for live metrics, separate worker for aggregation.

### What I chose and why

**FastAPI + SQLite** with modular packages (`ingestion`, `metrics`, `funnel`, `heatmap`, `anomalies`, `health`).

- Satisfies `docker compose up` acceptance gate with zero external services.
- Idempotent ingest via PRIMARY KEY on `event_id`.
- Daily conversion snapshots table supports 7-day anomaly baseline.
- **Trade-off:** At 40 live stores with high event rates, SQLite write contention and single-process uvicorn would be the first bottleneck — production would move to PostgreSQL + partitioned tables + materialized metrics.

### Where AI was overridden

AI suggested caching `/metrics` in Redis with TTL. I compute metrics from stored events on each request for **correctness and simpler tests**; caching would risk stale conversion during live ingest for marginal latency gain at challenge scale.

---

## Summary

| Decision | Choice |
|----------|--------|
| Detection | YOLOv8n + geometric zones + trajectory re-entry |
| Events | Flat schema, staff flag, rich metadata |
| API | FastAPI + SQLite, modular analytics |
