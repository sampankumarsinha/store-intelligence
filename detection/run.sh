#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MODE="${DETECTION_MODE:-auto}"
LAYOUT="${LAYOUT_PATH:-data/store_layout.json}"
OUTPUT="${EVENTS_OUTPUT:-data/events.jsonl}"

echo "Running detection pipeline (mode=$MODE)..."
python -m detection.detect --layout "$LAYOUT" --output "$OUTPUT" --mode "$MODE"
echo "Events written to $OUTPUT"

if [ "${INGEST_AFTER_DETECT:-false}" = "true" ]; then
  echo "Ingesting events into API..."
  python scripts/ingest_events.py "$OUTPUT"
fi
