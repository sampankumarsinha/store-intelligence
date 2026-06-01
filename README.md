# Store Intelligence Platform

An end-to-end retail analytics platform that transforms raw CCTV footage into actionable business intelligence using computer vision, event-driven analytics, and real-time dashboards.

---

## Overview

The Store Intelligence Platform processes CCTV footage from multiple retail store cameras to generate visitor analytics, conversion funnels, zone engagement insights, billing activity monitoring, heatmaps, operational alerts, and system health metrics.

The system combines YOLOv8-based people detection, event generation pipelines, FastAPI analytics services, and Streamlit dashboards to simulate a production-grade retail intelligence solution.

---

## Key Features

* Visitor Detection and Tracking
* Entry / Exit Monitoring
* Zone Engagement Analytics
* Billing Queue Monitoring
* Conversion Funnel Analytics
* Zone Heatmap Generation
* Dwell Time Analysis
* Operational Alerts
* System Health Monitoring
* Detection Verification Dashboard
* Dockerized Deployment

---

## Camera Mapping

After manual review of the provided CCTV footage:

| Camera | Purpose                |
| ------ | ---------------------- |
| CAM_1  | Cosmetics Zone A       |
| CAM_2  | Cosmetics Zone B       |
| CAM_3  | Entry / Exit           |
| CAM_4  | Warehouse / Staff Area |
| CAM_5  | Billing Counter        |

---

## System Architecture

```text
Raw CCTV Videos
        ↓
YOLOv8 Person Detection
        ↓
Multi-Object Tracking
        ↓
Structured Event Generation
        ↓
Event Enrichment Pipeline
        ↓
FastAPI Intelligence Layer
        ↓
Metrics / Funnel / Heatmap / Alerts
        ↓
Streamlit Dashboard
```

---

## Technology Stack

### Computer Vision

* YOLOv8
* OpenCV

### Backend

* FastAPI
* Uvicorn

### Analytics

* Pandas
* NumPy

### Dashboard

* Streamlit

### Deployment

* Docker
* Docker Compose
* Render

### Testing

* Pytest

---

## Project Structure

```text
store-intelligence/

├── app/
├── pipeline/
├── tests/
├── docs/
│
├── dashboard.py
├── dashboard_cloud.py
├── verify_detection.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── requirements-api.txt
└── README.md
```

---

## Quick Start

### Start Backend API

```bash
docker compose up --build
```

API:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```

---

### Load CCTV Events

```bash
python3 pipeline/send_detected_events.py
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

### Run Local Dashboard

```bash
streamlit run dashboard.py
```

Dashboard:

```text
http://localhost:8501
```

---

## Detection Pipeline

Process all CCTV clips:

```bash
python3 pipeline/detect_all.py
```

Merge events:

```bash
python3 pipeline/merge_events.py
```

Enrich zone activity:

```bash
python3 pipeline/enrich_zone_events.py
```

Send events:

```bash
python3 pipeline/send_detected_events.py
```

---

## Local Dashboard

File:

```text
dashboard.py
```

Capabilities:

* CCTV Video Upload
* YOLOv8 Inference
* Event Generation
* API Ingestion
* Analytics Dashboard
* Detection Verification

Run:

```bash
streamlit run dashboard.py
```

---

## Cloud Dashboard

File:

```text
dashboard_cloud.py
```

Capabilities:

* Analytics Visualization
* Funnel Analytics
* Heatmap Analytics
* Operational Alerts
* System Health Monitoring

The cloud dashboard does not execute YOLOv8 inference.

Video processing is available in the local dashboard.

---

## Available APIs

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

Tracks:

* Unique Visitors
* Entry Count
* Exit Count

### Conversion Funnel

Stages:

* Entry
* Zone Visit
* Billing Queue
* Purchase

### Heatmap Analytics

Measures:

* Visit Frequency
* Average Dwell Time
* Zone Engagement Score

### Operational Alerts

Detects:

* Dead Zones
* Queue Congestion
* Feed Health Issues

### Detection Verification

Validates:

* Event Ingestion
* Entry Detection
* Exit Detection
* Visitor Tracking
* Billing Detection
* Heatmap Generation

---

## Detection Verification Notes

Supported:

* Group Visitor Handling
* Partial Occlusion Handling
* Multi-Zone Tracking

Known Limitations:

* Cross-Camera Re-identification
* Heavy Crowd Identity Switching
* Staff/Customer Visual Similarity

Future versions can integrate:

* DeepSORT
* ByteTrack
* OSNet Re-Identification

---

## Scalability Considerations

Current Prototype:

* In-Memory Storage
* JSONL Event Streams

Production Upgrade Path:

* PostgreSQL / TimescaleDB
* Kafka Event Streaming
* Redis Streams
* Horizontal FastAPI Scaling
* Distributed Detection Workers
* Multi-Store Analytics

---

## Testing

Run Tests:

```bash
pytest
```

Coverage:

```bash
pytest --cov=app --cov-report=term
```

Current Coverage:

```text
82%
```

---

## Live Deployment

### Render API

https://store-intelligence-api-hl9i.onrender.com

### Streamlit Dashboard

<https://store-intelligence-ggznvvv6adiwbhjmyjlugh.streamlit.app/>

### GitHub Repository

https://github.com/sampankumarsinha/store-intelligence

---

## Submission Coverage

✓ CCTV Detection Pipeline

✓ Structured Event Generation

✓ FastAPI Intelligence Layer

✓ Conversion Funnel Analytics

✓ Heatmap Analytics

✓ Billing Analytics

✓ Operational Alerts

✓ System Health Monitoring

✓ Docker Deployment

✓ Automated Testing

✓ Streamlit Dashboard

✓ Production Scalability Considerations

---

## Future Enhancements

* DeepSORT Integration
* ByteTrack Integration
* Real-Time RTSP Streams
* Cross-Camera Re-Identification
* Multi-Store Deployment
* PostgreSQL Persistence
* Kafka-Based Event Processing
* Advanced Customer Journey Analytics
