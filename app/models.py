from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


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
    metadata: Dict[str, Any] = {}