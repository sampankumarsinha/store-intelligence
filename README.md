# Store Intelligence Platform

End-to-end retail analytics for Apex Retail: raw anonymised CCTV → structured behavioural events → FastAPI intelligence layer → live dashboard.

## Quick start (5 commands)

```bash
git clone <your-repo-url> store-intelligence && cd store-intelligence
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
docker compose up --build -d
curl http://localhost:8000/health
```

## Purplle-provided datasets

Official sample files (place in `detection/` or use as shipped):

- `detection/sample_eventsbe42122.jsonl` — Purplle CCTV events (entry/exit, zones, queue)
- `detection/POS - sample transactionsb1e826f.csv` — Purplle POS line items
- **Store 2 videos** (iCloud): `~/Library/Mobile Documents/com~apple~CloudDocs/Store 2/`  
  (`entry 1.mp4`, `entry 2.mp4`, `zone.mp4`, `billing_area.mp4`, layout PNG)

Convert to the challenge API schema and import:

```bash
source venv/bin/activate
python scripts/import_purplle_data.py --also-sample --link-store2-videos
python scripts/ingest_events.py data/purplle_events.jsonl
curl http://localhost:8000/stores/ST1076/metrics
```

| Dataset | Store ID | Date (sample) |
|---------|----------|----------------|
| CCTV events | `ST1076` | 2026-03-08 |
| POS CSV | `ST1008` | 2026-04-10 (→ `data/pos_transactions_purplle.csv`) |

POS and CCTV samples use **different stores/dates** in the Purplle pack. The API loads both `data/pos_transactions.csv` (challenge demo) and `data/pos_transactions_purplle.csv` when present.

## Run detection pipeline

**Replay mode** (no GPU/video required — uses `data/purplle_events.jsonl` or `data/sample_events.jsonl`):

```bash
source venv/bin/activate
bash detection/run.sh
# or: python -m detection.detect --mode replay
```

**Video mode** (place clips in `data/videos/` matching `store_layout.json`):

```bash
export DETECTION_MODE=video
bash detection/run.sh
```

Output: `data/events.jsonl`

## Ingest events into API

```bash
# API must be running (docker compose up)
python scripts/ingest_events.py data/events.jsonl
```

Or via curl:

```bash
curl -X POST http://localhost:8000/events/ingest \
  -H "Content-Type: application/json" \
  --data-binary @data/events.jsonl
```

## API examples

```bash
# Health
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/stores/STORE_001/metrics

# Funnel
curl http://localhost:8000/stores/STORE_001/funnel

# Heatmap
curl http://localhost:8000/stores/STORE_001/heatmap

# Anomalies
curl http://localhost:8000/stores/STORE_001/anomalies
```

## Live dashboard

**Docker (browser UI — recommended):**

```bash
docker compose up -d api dashboard
# Open http://localhost:8501
```

**Terminal (local venv):**

```bash
source venv/bin/activate
export API_URL=http://localhost:8000
export STORE_ID=STORE_001
python dashboard/live_dashboard.py
```

The Docker dashboard is Streamlit (`dashboard_cloud.py`). The terminal dashboard uses Rich and polls the same API metrics.

## Run tests

```bash
pytest tests/ --cov=app --cov-report=term-missing
```

## Acceptance checks

```bash
python assertions.py --api-url http://localhost:8000
```

Validates health, ingest, metrics, funnel, heatmap, and anomalies endpoints.

## Project structure

```text
store-intelligence/
├── detection/          # YOLOv8 pipeline + replay fallback
├── app/                # FastAPI + SQLite analytics
├── dashboard/          # Live terminal dashboard
├── tests/              # Pytest suite (>70% coverage)
├── data/               # layout, POS, sample events, events.jsonl, store.db
├── scripts/            # ingest helper
├── README.md
├── DESIGN.md
└── CHOICES.md
```

## Docker

The API image uses `requirements-api.txt` only (FastAPI + SQLite) — **not** YOLO/Torch. Detection stays on the host (`bash detection/run.sh`). Builds typically finish in under a minute.

```bash
docker compose up --build -d
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

## Known limitations

- Re-ID uses trajectory/bbox similarity (no deep embedding model) — may miss re-entries after long gaps or wardrobe changes.
- Staff detection is a uniform-color heuristic — false positives/negatives possible.
- 7-day conversion baseline requires prior daily snapshots in SQLite (built up as metrics are queried).
- Video mode requires `ultralytics`, OpenCV, and clips under `data/videos/`.
- Cross-camera deduplication relies on consistent `visitor_id` assignment at entry camera.

## Licence

Challenge dataset — not for redistribution or model training.
