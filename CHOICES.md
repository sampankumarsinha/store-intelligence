# Engineering Choices

## 1. Detection Model Choice

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| YOLOv8n + Ultralytics tracking | Fast, simple, widely used, good person detection | Can lose IDs in occlusion |
| RT-DETR | Higher detection accuracy | Heavier and slower on CPU |
| MediaPipe | Lightweight | Weaker in crowded retail CCTV scenes |
| VLM-based zone/staff labeling | Flexible semantic understanding | Costly, slower, non-deterministic |
| DeepSORT / ByteTrack | Better tracking and re-identification | More dependencies and setup complexity |

### What AI Suggested

AI suggested using YOLOv8 with ByteTrack and optionally a vision-language model for staff recognition and zone classification.

### What I Chose

I chose **YOLOv8n with tracking and rule-based camera/zone mapping**.

Reasons:

- YOLOv8n is lightweight and works well on CPU for challenge-scale CCTV clips.
- The model provides reliable person detection without needing a large GPU setup.
- Camera-to-zone mapping is deterministic and easier to validate.
- The challenge focuses on structured event generation and analytics, not just model complexity.
- The system remains reproducible with fewer dependencies.

### Trade-off

This approach is fast and simple, but it may lose identity continuity during heavy occlusion, re-entry, or crowded group movement. A production version would use ByteTrack, DeepSORT, or OSNet-based re-identification.

---

## 2. Event Schema Design Rationale

The event schema was designed as a flat JSON structure so that every stage of the pipeline can consume and validate events easily.

Each event contains:

- `event_id`
- `store_id`
- `camera_id`
- `visitor_id`
- `event_type`
- `timestamp`
- `zone_id`
- `dwell_ms`
- `is_staff`
- `confidence`
- `metadata`

### Why This Schema Works

| Requirement | Schema Field |
|------------|--------------|
| Unique visitor analytics | `visitor_id` |
| Entry/exit tracking | `event_type` |
| Zone analytics | `zone_id`, `dwell_ms` |
| Billing queue monitoring | `BILLING_QUEUE_JOIN`, `metadata.queue_depth` |
| Staff exclusion | `is_staff` |
| Idempotent ingestion | `event_id` |
| Confidence calibration | `confidence` |
| Debugging and traceability | `metadata` |

### Why I Kept Confidence Values

Low-confidence detections are not silently removed. They are retained with their confidence value so that downstream analytics can decide how to handle uncertain detections.

This makes the system more transparent and auditable.

---

## 3. API Architecture Choice

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| In-memory FastAPI | Simple and fast | No persistence |
| FastAPI + SQLite | Lightweight persistence | Limited write scalability |
| FastAPI + PostgreSQL | Production-ready | More setup complexity |
| FastAPI + Kafka | Scalable streaming | Too heavy for challenge scope |

### What AI Suggested

AI suggested PostgreSQL for persistent event storage, Redis for caching metrics, and a separate worker service for aggregation.

### What I Chose

I chose **FastAPI with lightweight event ingestion and analytics computation**.

Reasons:

- FastAPI provides clear REST API design.
- Docker Compose can start the API with minimal setup.
- The project remains easy to run and evaluate.
- Analytics can be computed directly from stored/ingested events.
- It satisfies the challenge acceptance gate without adding unnecessary infrastructure.

### Trade-off

For production scale, a database and streaming layer would be required. PostgreSQL or TimescaleDB would be used for event storage, and Kafka or Redis Streams would handle high-volume event ingestion.

---

## 4. Dashboard Architecture

The project uses two dashboard modes:

### Local Dashboard

File:

```text
dashboard.py