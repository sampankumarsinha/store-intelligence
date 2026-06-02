from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "structured"):
            payload.update(record.structured)  # type: ignore[attr-defined]
        return json.dumps(payload, default=str)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("store-intelligence")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def log_structured(logger: logging.Logger, message: str, **fields: Any) -> None:
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "(structured)",
        0,
        message,
        (),
        None,
    )
    record.structured = fields  # type: ignore[attr-defined]
    logger.handle(record)
