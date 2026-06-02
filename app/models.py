from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int = 1
    group_candidate: bool = False
    track_id: Optional[int] = None
    source: str = "detection_pipeline"

    model_config = {"extra": "allow"}


class StoreEvent(BaseModel):
    event_id: UUID
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = 0
    is_staff: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    metadata: EventMetadata = Field(default_factory=EventMetadata)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class IngestResponse(BaseModel):
    inserted_count: int
    duplicate_count: int
    failed_count: int
    errors: list[Dict[str, Any]]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    trace_id: Optional[str] = None
