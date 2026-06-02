from __future__ import annotations

import json
import time
import uuid
from typing import Any, List

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.anomalies import compute_anomalies
from app.database import DatabaseUnavailable, fetch_store_events, get_connection, init_db
from app.funnel import compute_funnel
from app.health import compute_health
from app.heatmap import compute_heatmap
from app.ingestion import ingest_events
from app.logging_config import log_structured, setup_logging
from app.metrics import compute_metrics
from app.models import ErrorResponse, IngestResponse

logger = setup_logging()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        init_db()
    except DatabaseUnavailable:
        logger.warning("Database init skipped")
    yield


app = FastAPI(title="Store Intelligence API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    start = time.time()
    store_id = request.path_params.get("store_id")
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)
    log_structured(
        logger,
        "request_complete",
        trace_id=trace_id,
        store_id=store_id,
        endpoint=request.url.path,
        latency_ms=latency_ms,
        status_code=response.status_code,
    )
    response.headers["X-Trace-Id"] = trace_id
    return response


def db_error_response(trace_id: str) -> JSONResponse:
    body = ErrorResponse(
        error="service_unavailable",
        detail="Database is unavailable",
        trace_id=trace_id,
    ).model_dump()
    return JSONResponse(status_code=503, content=body)


def get_store_events(store_id: str) -> List[dict]:
    with get_connection() as conn:
        return fetch_store_events(conn, store_id)


@app.post("/events/ingest", response_model=IngestResponse)
def ingest_endpoint(request: Request, payload: List[Any]):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    try:
        inserted, duplicates, failed, errors = ingest_events(payload)
        log_structured(
            logger,
            "ingest_complete",
            trace_id=trace_id,
            endpoint="/events/ingest",
            event_count=len(payload),
            inserted_count=inserted,
            status_code=200,
        )
        return IngestResponse(
            inserted_count=inserted,
            duplicate_count=duplicates,
            failed_count=failed,
            errors=errors,
        )
    except DatabaseUnavailable:
        return db_error_response(trace_id)


@app.get("/stores/{store_id}/metrics")
def metrics_endpoint(request: Request, store_id: str):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    try:
        events = get_store_events(store_id)
        return compute_metrics(store_id, events)
    except DatabaseUnavailable:
        return db_error_response(trace_id)


@app.get("/stores/{store_id}/funnel")
def funnel_endpoint(request: Request, store_id: str):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    try:
        events = get_store_events(store_id)
        return compute_funnel(store_id, events)
    except DatabaseUnavailable:
        return db_error_response(trace_id)


@app.get("/stores/{store_id}/heatmap")
def heatmap_endpoint(request: Request, store_id: str):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    try:
        events = get_store_events(store_id)
        return compute_heatmap(store_id, events)
    except DatabaseUnavailable:
        return db_error_response(trace_id)


@app.get("/stores/{store_id}/anomalies")
def anomalies_endpoint(request: Request, store_id: str):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    try:
        events = get_store_events(store_id)
        return compute_anomalies(store_id, events)
    except DatabaseUnavailable:
        return db_error_response(trace_id)


@app.get("/health")
def health_endpoint():
    return compute_health()
