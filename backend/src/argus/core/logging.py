from __future__ import annotations

import contextvars
import logging
import uuid
from typing import Any, cast

import structlog
from opentelemetry import trace
from structlog.typing import EventDict, WrappedLogger

from argus.core.config import Settings

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)


def configure_logging(settings: Settings) -> None:
    log_level = logging.INFO if settings.environment == "development" else logging.WARNING
    logging.basicConfig(level=log_level, format="%(message)s")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            cast(Any, add_request_and_trace_context),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def add_request_and_trace_context(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    request_id = request_id_var.get()
    if request_id is not None:
        event_dict["request_id"] = request_id

    span = trace.get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")

    return event_dict


def bind_request_context() -> str:
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    structlog.contextvars.bind_contextvars(request_id=request_id)
    return request_id


def clear_request_context() -> None:
    request_id_var.set(None)
    structlog.contextvars.clear_contextvars()
