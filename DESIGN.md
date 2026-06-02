# System Design — Store Intelligence

## Overview

The platform transforms anonymised CCTV into structured behavioural events, ingests them into a SQLite-backed FastAPI service, and exposes real-time retail analytics: conversion, funnel, heatmaps, anomalies, and health monitoring.

North-star metric: **offline store conversion rate** = converted visitor sessions ÷ unique visitor sessions (POS-correlated, staff excluded).

## Architecture

```text
CCTV clips / sample_events.jsonl
        ↓
detection/  (YOLOv8n + CentroidTracker + zones + reid + staff + queue)
        ↓
data/events.jsonl
        ↓
POST /events/ingest  →  SQLite (events table)
        ↓
Analytics modules (metrics, funnel, heatmap, anomalies)
        ↓
REST API + dashboard/live_dashboard.py
```

## Data flow

1. **Detection** reads `store_layout.json` for entry lines, zone polygons, and camera types.
2. Each frame (or replayed event) produces schema-compliant JSON events with UUID v4 IDs and UTC timestamps.
3. **Ingestion** validates via Pydantic, deduplicates on `event_id`, supports partial success.
4. **Analytics** query SQLite per store, excluding `is_staff=true`.
5. **POS** (`pos_transactions.csv`) correlates billing-zone presence within 5 minutes before each transaction timestamp.

## Detection design

| Component | Role |
|-----------|------|
| `zones.py` | Entry-line crossing, point-in-polygon zone tests |
| `tracker.py` | Centroid + IoU tracker (ByteTrack fallback) |
| `reid.py` | REENTRY vs new ENTRY using exit profile + time window |
| `staff_classifier.py` | Upper-body uniform heuristic + staff camera types |
| `queue.py` | Billing queue depth, join/abandon signals |
| `emit.py` | Canonical event schema builder |
| `detect.py` | Orchestrates per-camera processing or replay enrichment |

**Entry/exit:** Direction from previous vs current centroid relative to `entry_line` Y. Cooldown per `track_id` prevents duplicate crossings.

**Group entry:** Each detection/track emits its own ENTRY; overlapping crossings within 3s set `metadata.group_candidate=true` and lower confidence.

**Re-entry:** After EXIT, returning visitors within 600s with similar bbox/centroid get `REENTRY` and the same `visitor_id`.

**Zones:** ZONE_ENTER / ZONE_EXIT / ZONE_DWELL (30s intervals) from polygon membership.

**Billing:** `queue_depth` = non-staff visitors in BILLING polygon; BILLING_QUEUE_JOIN when entering while depth > 0; ABANDON if leaving without POS conversion within window.

## Event design

Events are immutable facts. `visitor_id` is stable per person across re-entry. `session_seq` increments within a visit. `confidence` is never suppressed for low scores. Staff events are retained with `is_staff=true`.

## Session and re-entry logic

- **Metrics unique visitors:** distinct `visitor_id` among customer events; REENTRY does not create a new ID.
- **Funnel sessions:** one funnel unit per `visitor_id`; REENTRY counts as entry signal but not a second session.
- **Conversion:** visitor in BILLING within 5 minutes before POS timestamp.

## Metric calculation

- `conversion_rate` = |converted visitors| / |unique visitors| × 100
- `avg_dwell_per_zone` = mean `dwell_ms` from ZONE_DWELL per zone
- `current_queue_depth` = max `metadata.queue_depth` from BILLING_QUEUE_JOIN
- `abandonment_rate` = abandoned queue joiners / total joiners × 100

## Anomalies

| Type | Trigger |
|------|---------|
| BILLING_QUEUE_SPIKE | max queue_depth ≥ 3 |
| CONVERSION_DROP | today rate < 70% of 7-day SQLite baseline |
| DEAD_ZONE | no zone visit for 30+ minutes |

## Health

- SQLite connectivity status
- `last_event_timestamp_per_store`
- STALE_FEED if lag > 10 minutes

## AI-Assisted Decisions

1. **Tracker choice:** An LLM suggested DeepSORT + OSNet for re-ID. I overrode with centroid+IoU + trajectory similarity because the challenge dataset is small, clips are anonymised, and the API scoring emphasises explainability and deterministic tests. Deep models would add weight without guaranteed gain on blurred faces.

2. **Funnel entry base:** AI proposed counting only explicit ENTRY events. I extended the entry base to include visitors first seen on floor/billing cameras (camera overlap edge case) while still deduplicating by `visitor_id` so re-entry does not inflate counts.

3. **Storage:** AI recommended PostgreSQL + Redis streams. I chose SQLite for single-container `docker compose up` simplicity, with idempotent ingest and indexed `(store_id, timestamp)` — sufficient for 5-store challenge scale and acceptance gate.

## Production concerns

- Structured JSON logs: `trace_id`, `store_id`, `endpoint`, `latency_ms`, `event_count`, `status_code`
- HTTP 503 JSON body when SQLite unavailable (no stack traces)
- Idempotent ingest by `event_id`
