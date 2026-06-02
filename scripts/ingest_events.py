#!/usr/bin/env python3
"""Ingest events.jsonl into the running API."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
BATCH = 500


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/events.jsonl")
    events = []
    with path.open() as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))

    for i in range(0, len(events), BATCH):
        batch = events[i : i + BATCH]
        resp = httpx.post(f"{API_URL}/events/ingest", json=batch, timeout=60)
        resp.raise_for_status()
        print(resp.json())

    print(f"Ingested {len(events)} events from {path}")


if __name__ == "__main__":
    main()
