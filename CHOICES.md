# Engineering Choices

This document explains the major engineering decisions made while designing the Store Intelligence Platform. For each component, alternative approaches were considered, AI-assisted recommendations were evaluated, and final selections were made based on challenge requirements, implementation complexity, explainability, and production readiness.


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
---

## 5. Staff Exclusion Strategy

### Problem

Retail employees frequently move across store zones and billing areas. Treating staff as customers would inflate visitor counts, dwell time metrics, conversion funnels, and queue analytics.

### Options Considered

| Option                       | Pros                            | Cons                                           |
| ---------------------------- | ------------------------------- | ---------------------------------------------- |
| Uniform Detection            | High accuracy if uniforms exist | Not applicable to all stores                   |
| Face Recognition             | Strong identification           | Privacy concerns and additional infrastructure |
| Dedicated Staff Badges       | Reliable                        | Requires external systems                      |
| Rule-Based Movement Analysis | Simple and explainable          | Less precise                                   |

### What AI Suggested

AI suggested a dedicated appearance-based classifier combined with re-identification embeddings and facial recognition.

### What I Chose

A lightweight rule-based staff classifier using camera context, movement patterns, and staff-only zone access.

Reasons:

* Deterministic and explainable.
* Easy to validate during evaluation.
* No privacy-sensitive biometric processing.
* Works without additional training data.

### Trade-off

The approach prioritizes simplicity and reproducibility over perfect staff identification accuracy.

---

## 6. Re-Entry Handling

### Problem

Customers may temporarily leave a camera view and reappear later.

Naively assigning a new visitor ID each time would inflate visitor counts.

### What AI Suggested

AI recommended DeepSORT, ByteTrack, and OSNet-based person re-identification.

### What I Chose

Session-based re-entry handling using track continuity heuristics.

The system:

* Maintains track history.
* Uses temporal proximity.
* Preserves session sequence metadata.
* Avoids unnecessary visitor duplication.

### Trade-off

The approach works well for challenge-scale clips but may fail under prolonged disappearance or cross-camera transitions.

Production deployments would use dedicated re-identification models.

---

## 7. Group Entry Detection

### Problem

Retail customers often enter as families or small groups.

Tracking them independently can lose valuable behavioral context.

### What AI Suggested

AI proposed clustering trajectories using spatio-temporal embeddings.

### What I Chose

A lightweight group candidate approach.

Visitors are marked as group candidates when:

* Entry timestamps are very close.
* Spatial distance is below a threshold.
* Motion direction is consistent.

Generated events include:

* group_candidate
* group_id
* group_size

when confidence is sufficient.

### Trade-off

The solution favors explainability and robustness over sophisticated clustering techniques.

---

## 8. Production Readiness Decisions

### Goal

The challenge evaluates production readiness in addition to analytics quality.

### Decisions Made

#### Containerization

* Dockerfile included.
* Docker Compose orchestration included.
* Reproducible deployment environment.

#### Health Monitoring

* Dedicated `/health` endpoint.
* Feed status monitoring.
* Detection validation utilities.

#### Testing

* Automated pytest suite.
* Event validation tests.
* API correctness checks.

#### Fault Tolerance

* Confidence-based event generation.
* Graceful handling of missing detections.
* Validation before ingestion.

### Trade-off

The system remains lightweight while still demonstrating operational deployment practices.

---

## 9. AI-Assisted Engineering Decisions

AI tools were used as engineering assistants during development.

AI contributed to:

* Architecture exploration
* Event schema refinement
* API design review
* Test-case generation
* Documentation drafting
* Edge-case identification

All implementation decisions, debugging, validation, event generation logic, analytics verification, and deployment testing were performed manually before inclusion in the final submission.

The final system prioritizes:

* Explainability
* Deterministic behavior
* Reproducibility
* Ease of evaluation
* Production-oriented engineering practices
