


# Store Intelligence API

This project builds an end-to-end store analytics system from raw CCTV footage. It detects people from CCTV clips, converts movement into structured behavioral events, ingests those events into a FastAPI intelligence layer, and exposes live retail metrics such as visitors, funnel, heatmap, billing activity, and anomalies.

## Camera Mapping

After manual review of the provided CCTV clips:

- CAM_3: Entry / Exit camera
- CAM_1: Cosmetics Zone A
- CAM_2: Cosmetics Zone B
- CAM_5: Billing Counter
- CAM_4: Warehouse / staff-only area

## Tech Stack

- Python
- FastAPI
- YOLOv8
- OpenCV
- Docker
- JSONL event stream

## Run API with Docker

```bash
docker compose up --build

## Architecture

```text
Raw CCTV Videos
        ↓
YOLOv8 Detection
        ↓
Visitor Tracking
        ↓
Event Generation
        ↓
Event Enrichment
        ↓
FastAPI Ingestion
        ↓
Metrics / Funnel / Heatmap / Anomalies
        ↓
Streamlit Dashboard
```

## Running the Detection Pipeline

Process all CCTV videos:

```bash
python3 pipeline/detect_all.py
```

Merge generated events:

```bash
python3 pipeline/merge_events.py
```

Enrich events with zone and billing intelligence:

```bash
python3 pipeline/enrich_zone_events.py
```

Send events to the API:

```bash
python3 pipeline/send_detected_events.py
```

## API Endpoints

### Metrics

```bash
curl http://127.0.0.1:8000/stores/STORE_001/metrics
```

### Funnel

```bash
curl http://127.0.0.1:8000/stores/STORE_001/funnel
```

### Heatmap

```bash
curl http://127.0.0.1:8000/stores/STORE_001/heatmap
```

### Anomalies

```bash
curl http://127.0.0.1:8000/stores/STORE_001/anomalies
```

### Health

```bash
curl http://127.0.0.1:8000/health
```

## Dashboard

Run:

```bash
streamlit run dashboard.py
```

Open:

```text
http://localhost:8501
```

The dashboard provides:

* Visitor metrics
* Conversion funnel
* Zone engagement analytics
* Dwell time analysis
* Operational alerts
* System health monitoring

## Testing

Run:

```bash
pytest
```

Run coverage:

```bash
pytest --cov=app --cov-report=term
```

Current coverage:

```text
82%
## Running the Dashboard

First start the API:

```bash
docker compose up --build
```

## Scalability

The prototype uses in-memory storage and JSONL event streams for simplicity.

For production deployment:

* PostgreSQL / TimescaleDB for event storage
* Kafka or Redis Streams for event ingestion
* Distributed detector workers per store
* Horizontal FastAPI scaling
* Centralized monitoring and observability

## Submission Notes

This implementation satisfies:

* Detection pipeline
* Structured event generation
* Intelligence API
* Funnel analytics
* Heatmap analytics
* Anomaly detection
* Health monitoring
* Docker deployment
* Automated tests
* Streamlit dashboard
* Production-readiness considerations


## The deployed Streamlit Cloud dashboard is used for analytics visualization and API monitoring.

* The full CCTV video processing workflow runs locally through dashboard.py because it uses YOLOv8 and OpenCV for video inference.

* To run the complete local demo:

* docker compose up --build
streamlit run dashboard.py


## Quick Start

### 1. Start the API

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

### 2. Load Sample Events

Open a new terminal and run:

```bash
python3 pipeline/send_detected_events.py
```

This loads the generated CCTV events into the Store Intelligence API.

Verify:

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{
  "status": "ok",
  "total_events": 328
}
```

---

### 3. Launch Dashboard

Open another terminal and run:

```bash
streamlit run dashboard.py
```

Dashboard URL:

```text
http://localhost:8501
```

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

## Testing

Run tests:

```bash
pytest
```

Run coverage:

```bash
pytest --cov=app --cov-report=term
```

Current coverage:

```text
82%
```

---

## Dashboard Features

The dashboard provides:

- Visitor Analytics
- Conversion Funnel
- Zone Engagement Analysis
- Dwell Time Insights
- Billing Activity Monitoring
- Operational Alerts
- System Health Monitoring

---

## Deployment URLs

| Service | URL |
|----------|------|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Dashboard | http://localhost:8501 |
