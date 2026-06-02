#!/usr/bin/env python3
"""
Challenge acceptance checks for Store Intelligence API.
Run: python assertions.py [--api-url http://localhost:8000]
"""
from __future__ import annotations

import argparse
import sys
import uuid

import httpx

STORE_ID = "STORE_001"


def check(name: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    args = parser.parse_args()
    base = args.api_url.rstrip("/")
    passed = 0
    total = 0

    try:
        with httpx.Client(timeout=15) as client:
            health = client.get(f"{base}/health").json()
            total += 1
            if check("GET /health", health.get("database") == "ok", str(health.get("status"))):
                passed += 1

            eid = str(uuid.uuid4())
            event = {
                "event_id": eid,
                "store_id": STORE_ID,
                "camera_id": "CAM_3",
                "visitor_id": "VIS_ASSERT",
                "event_type": "ENTRY",
                "timestamp": "2026-05-29T23:08:00Z",
                "zone_id": None,
                "dwell_ms": 0,
                "is_staff": False,
                "confidence": 0.9,
                "metadata": {
                    "queue_depth": None,
                    "sku_zone": None,
                    "session_seq": 1,
                    "group_candidate": False,
                    "source": "detection_pipeline",
                },
            }
            ing = client.post(f"{base}/events/ingest", json=[event]).json()
            total += 1
            if check(
                "POST /events/ingest",
                ing.get("inserted_count", 0) >= 1 or ing.get("duplicate_count", 0) >= 1,
                str(ing),
            ):
                passed += 1

            metrics = client.get(f"{base}/stores/{STORE_ID}/metrics").json()
            total += 1
            if check(
                "GET /metrics",
                "unique_visitors" in metrics and "conversion_rate" in metrics,
                f"visitors={metrics.get('unique_visitors')}",
            ):
                passed += 1

            funnel = client.get(f"{base}/stores/{STORE_ID}/funnel").json()
            total += 1
            if check("GET /funnel", "funnel" in funnel and "dropoff_percent" in funnel):
                passed += 1

            heatmap = client.get(f"{base}/stores/{STORE_ID}/heatmap").json()
            total += 1
            if check(
                "GET /heatmap",
                "heatmap" in heatmap and "data_confidence" in heatmap,
            ):
                passed += 1

            anomalies = client.get(f"{base}/stores/{STORE_ID}/anomalies").json()
            total += 1
            if check("GET /anomalies", "active_anomalies" in anomalies):
                passed += 1

    except httpx.HTTPError as exc:
        print(f"[FAIL] API unreachable: {exc}")
        return 1

    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
