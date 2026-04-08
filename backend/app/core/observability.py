from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from datetime import datetime, timezone
import json
import logging
from typing import Any
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-ID"

_request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": getattr(record, "event_name", record.getMessage()),
            "message": record.getMessage(),
        }

        request_id = get_request_id()
        if request_id is not None:
            payload["request_id"] = request_id

        event_fields = getattr(record, "event_fields", None)
        if isinstance(event_fields, dict):
            payload.update(event_fields)

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if getattr(root_logger, "_enterprise_copilot_observability_configured", False):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())

    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
    root_logger._enterprise_copilot_observability_configured = True  # type: ignore[attr-defined]


def generate_request_id() -> str:
    return uuid4().hex


def get_request_id() -> str | None:
    return _request_id_context.get()


def bind_request_id(request_id: str | None) -> Token[str | None]:
    return _request_id_context.set(request_id)


def reset_request_id(token: Token[str | None]) -> None:
    _request_id_context.reset(token)


@contextmanager
def request_id_context(request_id: str | None):
    token = bind_request_id(request_id)
    try:
        yield
    finally:
        reset_request_id(token)


def log_event(
    logger: logging.Logger,
    level: int,
    event_name: str,
    **event_fields: Any,
) -> None:
    logger.log(
        level,
        event_name,
        extra={
            "event_name": event_name,
            "event_fields": event_fields,
        },
    )
