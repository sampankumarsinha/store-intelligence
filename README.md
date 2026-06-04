# Store Intelligence Platform

## Overview

Store Intelligence Platform is an end-to-end retail analytics system that converts CCTV footage into actionable business intelligence.

The system detects visitors, tracks movement across store zones, generates structured behavioral events, ingests those events into a FastAPI intelligence layer, and produces analytics such as:

* Visitor Count
* Entry / Exit Monitoring
* Zone Engagement Analysis
* Billing Queue Monitoring
* Conversion Funnel Analytics
* Heatmap Analytics
* Operational Alerts
* System Health Monitoring

---

## Problem Statement

Retail stores generate large amounts of CCTV footage but derive limited operational insights from it.

This platform transforms raw CCTV data into structured retail intelligence that can help:

* Understand customer movement
* Measure zone engagement
* Identify bottlenecks
* Monitor queue congestion
* Improve conversion rates
* Detect operational anomalies

---
## Challenge Requirements Coverage

This solution was designed specifically to address the Store Intelligence challenge requirements.

### Visitor Detection and Tracking

* Detects customers entering and exiting the store.
* Maintains visitor identities through multi-object tracking.
* Generates structured retail events from tracked trajectories.

### Staff Exclusion

The system applies a dedicated staff classification layer to reduce false customer counts from employees repeatedly moving through monitored areas.

Staff filtering is performed before analytics generation to prevent skewed visitor metrics, funnel analysis, and zone engagement statistics.

### Re-Entry Handling

Visitors may temporarily leave the field of view and later return.

The tracking pipeline supports session-based re-entry handling through track continuity heuristics and event sequencing logic, preventing duplicate visitor creation whenever possible.

### Group Entry Detection

Visitors entering together within configurable spatial and temporal thresholds are marked as group candidates.

Generated events include group metadata to support future basket-size and conversion analysis.

### Edge Case Handling

The system includes safeguards for:

* Partial occlusions
* Short-term tracking loss
* Queue abandonment
* Stationary visitors
* Crowded billing zones
* Camera feed interruptions

These cases are surfaced through confidence scores and operational alerts.

### Event Schema Compliance

Generated event logs follow the JSONL schema provided in the challenge dataset.

Each event contains:

* event_id
* store_id
* camera_id
* visitor_id
* event_type
* timestamp
* zone_id
* dwell_ms
* confidence
* metadata

The final submission event log was validated against the provided sample schema.


## Architecture

```text
CCTV Video
     ↓
YOLOv8 Detection
     ↓
Multi-Object Tracking
     ↓
Event Generation
     ↓
FastAPI Intelligence Layer
     ↓
Metrics Engine
     ↓
Dashboard Visualization
```

---

## Technology Stack

### Computer Vision

* YOLOv8
* OpenCV

### Backend

* FastAPI
* Uvicorn

### Dashboard

* Streamlit

### Data Processing

* Python
* Pandas

### Deployment

* Docker
* Docker Compose
* Render

## AI-Assisted Engineering Decisions

AI tools were used as engineering accelerators during development while all architectural decisions, implementation validation, debugging, and final verification were performed by the project author.

AI assistance was used for:

* Alternative architecture exploration
* Event schema refinement
* API design review
* Documentation improvement
* Test-case generation
* Edge-case identification

Human validation was applied to all generated code, event formats, analytics outputs, and deployment configurations before inclusion in the final system.

The final design prioritizes correctness, explainability, maintainability, and production-readiness over model complexity.




### Testing

* Pytest

---

## Datasets Used

### Purplle Sample Data

Provided datasets:

* sample_eventsbe42122.jsonl
* POS - sample transactionsb1e826f.csv
* Store 2 CCTV Videos

Used for:

* Event Schema Validation
* Funnel Analytics
* Heatmap Analytics
* Queue Monitoring
* API Validation

---

## Camera Mapping

| Camera | Purpose                |
| ------ | ---------------------- |
| CAM_1  | Cosmetics Zone A       |
| CAM_2  | Cosmetics Zone B       |
| CAM_3  | Entry / Exit           |
| CAM_4  | Warehouse / Staff Area |
| CAM_5  | Billing Counter        |

---

## Project Structure

```text
store-intelligence/

├── app/
├── detection/
├── pipeline/
├── dashboard/
├── scripts/
├── tests/

├── dashboard.py
├── dashboard_cloud.py
├── verify_detection.py

├── Dockerfile
├── docker-compose.yml

├── README.md
├── DESIGN.md
├── CHOICES.md
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone <https://github.com/sampankumarsinha/store-intelligence>
cd store-intelligence
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Backend

```bash
docker compose up --build
```

Verify:

```bash
curl http://localhost:8000/health
```

Expected:

```json
{
  "status": "ok"
}
```

---

## Run Dashboard

Open a new terminal:

```bash
source venv/bin/activate
streamlit run dashboard.py
```

Open:

```text
http://localhost:8502
```

---

## Video Processing Workflow

1. Start API

```bash
docker compose up --build
```

2. Launch Dashboard

```bash
streamlit run dashboard.py
```

3. Upload CCTV video

4. Select camera mapping

5. Click:

```text
Process Video and Send Events
```

6. Events are generated and ingested automatically

7. Dashboard updates metrics in real time

---

## Event Processing Pipeline

```text
Video
 ↓
YOLO Detection
 ↓
Tracking
 ↓
Structured Event Generation
 ↓
/events/ingest
 ↓
Metrics
 ↓
Dashboard
```

Generated events include:

* ENTRY
* EXIT
* ZONE_DWELL
* BILLING_QUEUE_JOIN

---

## API Endpoints

### Health

```bash
curl http://localhost:8000/health
```

### Metrics

```bash
curl http://localhost:8000/stores/STORE_001/metrics
```

### Funnel

```bash
curl http://localhost:8000/stores/STORE_001/funnel
```

### Heatmap

```bash
curl http://localhost:8000/stores/STORE_001/heatmap
```

### Anomalies

```bash
curl http://localhost:8000/stores/STORE_001/anomalies
```

---

## Dashboard Features

### Visitor Analytics

* Unique Visitors
* Entry Count
* Exit Count

### Funnel Analytics

* Entry
* Zone Visit
* Billing Queue
* Purchase

### Heatmap Analytics

* Zone Visits
* Dwell Time
* Engagement Score

### Operational Alerts

* Dead Zones
* Queue Congestion
* Feed Health

### Detection Verification

* Event Validation
* Visitor Tracking Validation
* Supported Features Summary

---

## Testing

Run:

```bash
pytest
```

Coverage:

```bash
pytest --cov=app --cov-report=term
```

Target:

```text
Coverage > 70%
```

---

## Design Decisions

See:

* DESIGN.md
* CHOICES.md

These documents explain:

* Architecture choices
* Tracking approach
* Event schema design
* Scalability considerations
* Trade-offs and limitations

---

## Known Limitations

* Visitor counts are based on tracked identities.
* Heavy occlusion may reduce tracking accuracy.
* Cross-camera re-identification is limited.
* Staff exclusion is heuristic-based.
* Re-entry tracking is approximate.

---

## Future Enhancements

* DeepSORT Integration
* ByteTrack Integration
* Cross-Camera Re-Identification
* PostgreSQL Event Storage
* Kafka Streaming Pipeline
* Multi-Store Analytics
* Real-Time RTSP Streams

---

## Live Deployment

### Render API

https://store-intelligence-api-hl9i.onrender.com

### Streamlit Dashboard

<https://store-intelligence-ggznvvv6adiwbhjmyjlugh.streamlit.app/>

### GitHub Repository

https://github.com/sampankumarsinha/store-intelligence

---

## Submission Coverage Checklist

### Detection & Event Generation

✓ Visitor Detection

✓ Multi-Object Tracking

✓ Entry Event Generation

✓ Exit Event Generation

✓ Zone Analytics

✓ Queue Monitoring

✓ Group Entry Identification

✓ Staff Exclusion Logic

✓ Re-Entry Handling

✓ Confidence Scoring

### Intelligence Layer

✓ FastAPI Analytics APIs

✓ Funnel Analytics

✓ Heatmap Analytics

✓ Operational Alerts

✓ Health Monitoring

✓ Event Ingestion Pipeline

### Engineering Quality

✓ JSONL Event Log Generation

✓ Schema Validation

✓ Docker Deployment

✓ Automated Testing

✓ Documentation

✓ Design Documentation

✓ Architecture Trade-Off Analysis

✓ AI-Assisted Engineering Decisions

### Production Readiness

✓ Modular Pipeline Architecture

✓ Error Handling

✓ Health Checks

✓ Configurable Deployment

✓ Extensible Analytics Framework
