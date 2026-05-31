# Engineering Choices and Trade-offs

## Overview

The objective was to build a practical store intelligence system from CCTV footage within the hackathon constraints while keeping the solution explainable, scalable, and easy to evaluate.

---

## Why YOLOv8?

### Choice

YOLOv8 was selected for person detection and tracking.

### Reason

* Fast inference
* Strong person detection performance
* Easy integration
* Widely adopted in production systems

### Trade-off

A larger model could improve accuracy but would significantly increase inference time.

---

## Why Event-Driven Architecture?

### Choice

Video observations are converted into structured events before analytics.

### Reason

Analytics should operate on business events rather than raw frames.

Benefits:

* Easier aggregation
* Better scalability
* Reduced coupling between CV and analytics

### Trade-off

Additional processing step between detection and analytics.

---

## Why Camera-Based Zone Mapping?

### Choice

Store zones are mapped using camera coverage.

### Reason

The challenge dataset did not include a store layout file.

Manual review of CCTV footage identified:

* CAM_3 → Entry
* CAM_1 → Cosmetics A
* CAM_2 → Cosmetics B
* CAM_5 → Billing
* CAM_4 → Warehouse

### Trade-off

Zone mapping is rule-based rather than generated from an official layout.


## Why Enriched Events?

### Choice

Generate:

* ZONE_ENTER
* ZONE_DWELL
* BILLING_QUEUE_JOIN

from low-level observations.

### Reason

Business users care about behavior rather than bounding boxes.

### Trade-off

Some enrichment rules are heuristic-based.

---

## Why In-Memory Storage?

### Choice

Events are stored in memory during hackathon execution.

### Reason

* Faster implementation
* Simpler deployment
* Lower operational complexity

### Production Upgrade

Replace with:

* PostgreSQL
* TimescaleDB
* Redis Streams
* Kafka

---

## Why Separate Detection and API Layers?

### Choice

Computer vision runs locally while the API runs independently.

### Reason

CV workloads require heavy dependencies such as:

* OpenCV
* Torch
* YOLO

Keeping the analytics API lightweight improves deployment speed and reliability.

### Trade-off

Two-step pipeline instead of a single service.

---

## Scalability Strategy

For multi-store deployment:

1. Dedicated detector workers per store.
2. Event streaming through Kafka or Redis Streams.
3. Centralized analytics APIs.
4. Containerized deployment.
5. Horizontal API scaling.

The architecture is designed to support expansion from a single store to dozens of stores with minimal changes.

---

## Future Improvements

* Cross-camera person re-identification.
* Real POS transaction integration.
* Staff identification models.
* Queue length estimation.
* Real-time streaming analytics.
* Predictive conversion forecasting.
* Customer journey reconstruction across cameras.

## Handling Real CCTV Edge Cases

### Group Entry

Multiple customers entering together are handled using person-level YOLO detections instead of treating the group as a single entity. Each detected person receives an individual tracking ID, allowing visitor metrics to count individuals.

### Staff Movement

Staff-only movement is reduced through camera-zone mapping. Warehouse/staff camera feeds are separated from customer-facing zones. In production, this can be improved using staff identification models or registered employee embeddings.

### Re-entry Handling

The current system maintains visitor continuity using tracking IDs during video processing. Long-term re-entry across different time windows can be improved using person re-identification models.

### Partial Occlusion

YOLOv8 provides confidence-based detection for partially visible customers. The pipeline is designed to degrade gracefully instead of failing when detections are uncertain.

### Billing Queue Build-up

Billing counter cameras generate queue-related events. These are converted into operational alerts when abnormal queue patterns are detected.

