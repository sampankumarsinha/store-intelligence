# System Design

## Overview

The system converts raw CCTV footage into actionable retail intelligence. It follows an event-driven architecture where computer vision detections are transformed into structured events and then aggregated into business metrics.

---

## Architecture

text
CCTV Videos
     |
     v
YOLOv8 Detection + Tracking
     |
     v
Event Generation
(ENTRY, EXIT, ZONE_OBSERVED)
     |
     v
Event Enrichment
(ZONE_ENTER, ZONE_DWELL, BILLING_QUEUE_JOIN)
     |
     v
FastAPI Event Ingestion Layer
     |
     v
Analytics Engine
     |
     +--> Metrics API
     +--> Funnel API
     +--> Heatmap API
     +--> Anomaly API
```

---

## Camera Mapping

Based on manual review of the CCTV feeds:

| Camera | Purpose                |
| ------ | ---------------------- |
| CAM_3  | Entry / Exit           |
| CAM_1  | Cosmetics Zone A       |
| CAM_2  | Cosmetics Zone B       |
| CAM_5  | Billing Counter        |
| CAM_4  | Warehouse (Staff Area) |

---

## Event Pipeline

### Detection Layer

YOLOv8 detects people in CCTV footage.

Tracking IDs are assigned to maintain visitor continuity within each camera feed.

### Event Generation

Generated events include:

* ENTRY
* EXIT
* ZONE_OBSERVED

### Event Enrichment

Observed events are transformed into higher-level business events:

* ZONE_ENTER
* ZONE_DWELL
* BILLING_QUEUE_JOIN

---

## Analytics Layer

### Metrics

Calculates:

* Unique visitors
* Entry count
* Exit count
* Billing visitors
* Conversion rate
* Average dwell time

### Funnel

Measures customer progression:

Entry → Zone Visit → Billing

### Heatmap

Measures:

* Visit frequency
* Average dwell time
* Zone popularity

### Anomaly Detection

Flags unusual visitor patterns and abnormal store behavior.

---

## Scalability

Current implementation uses in-memory storage for simplicity.

For production deployment:

* PostgreSQL / TimescaleDB for event storage
* Redis Streams or Kafka for ingestion
* Distributed detector workers per store
* Horizontal API scaling using containers
* Centralized analytics service

The architecture supports expansion from a single store to multi-store deployments with minimal modifications.


## AI-Assisted Decisions

AI tools were used throughout the project to accelerate implementation, evaluate architectural alternatives, and validate design assumptions. However, all final design decisions were manually reviewed and adapted based on the characteristics of the provided CCTV footage and the challenge requirements.

### Detection Model Selection

Several alternatives were evaluated, including YOLOv8, YOLOv9, RT-DETR, and MediaPipe-based approaches. AI-assisted comparisons highlighted the trade-off between accuracy and implementation complexity. YOLOv8 was selected because it provided a mature ecosystem, strong person-detection performance, straightforward tracking integration, and fast experimentation within the challenge timeline.

### Camera-to-Zone Mapping

Initial AI-generated assumptions treated the cameras as generic entry, floor, and billing feeds. After reviewing the actual CCTV clips, those assumptions were overridden. Manual inspection revealed that CAM_3 represented the entry/exit threshold, CAM_1 and CAM_2 covered cosmetics zones, CAM_5 covered the billing counter, and CAM_4 primarily covered warehouse activity. This manual validation significantly improved the quality of generated events and downstream analytics.

### Containerization Strategy

AI initially suggested packaging the complete computer-vision pipeline inside Docker. After evaluating build times, image size, and deployment complexity, the decision was made to containerize only the FastAPI analytics layer. The detection pipeline remains a preprocessing stage. This resulted in significantly faster builds, simpler deployment, and easier testing while preserving a clear upgrade path toward a fully containerized production deployment.

## Edge Case Handling

The challenge dataset contains several real-world edge cases.

* Group entries are handled by person-level detection and tracking rather than group counting.
* Warehouse activity is excluded from customer analytics through camera-level zone mapping.
* Empty-store periods naturally produce zero-valued metrics without generating errors.
* Low-confidence detections are retained and exposed through the confidence field instead of being silently discarded.
* Duplicate event ingestion is prevented through event_id-based idempotency.

## Production Scaling Strategy

Although the current implementation uses in-memory storage for simplicity, the architecture was intentionally designed to support large-scale deployments.

For a production rollout across 40 stores:

* Event ingestion would be backed by Kafka or Redis Streams.
* Event storage would move to PostgreSQL or TimescaleDB.
* Detection workers would run independently per camera or per store.
* FastAPI instances would scale horizontally behind a load balancer.
* Centralized monitoring and structured logging would support operational visibility.

This separation between detection, event processing, analytics, and visualization allows the platform to scale without major architectural changes.

