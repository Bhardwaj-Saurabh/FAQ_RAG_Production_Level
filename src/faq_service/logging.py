"""Structured logging: every log line is one JSON object in prod, readable text in dev.

Why structured: in production, logs go to a collector (Docker, Fly, CloudWatch)
where you search and filter them. `{"event": "query_answered", "model":
"gpt-4o-mini", "latency_ms": 812}` can be filtered by `model`; the sentence
"answered with gpt-4o-mini in 812 ms" cannot.

Usage:
    log = get_logger(__name__)
    log.info("query_answered", model="gpt-4o-mini", latency_ms=812)

Context bound with `bind_context(request_id=...)` is added to every line
logged afterwards in the same request (it uses contextvars, so concurrent
async requests never mix). The request middleware in P0.4 uses this.

Library logs that use the standard `logging` module (uvicorn, httpx, openai)
go through the same formatter, so the whole process emits one format.
"""

import logging
import sys
from typing import Any, TextIO

import structlog
from structlog.types import EventDict, Processor, WrappedLogger

# Keys whose values must never reach a log line, whatever the caller passes.
_SECRET_KEYS = {"api_key", "authorization", "password", "secret", "x-api-key"}
_REDACTED = "***"


def _redact_secrets(_logger: WrappedLogger, _method: str, event_dict: EventDict) -> EventDict:
    for key in event_dict:
        if key.lower() in _SECRET_KEYS:
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(
    level: str = "INFO", *, json: bool = True, stream: TextIO | None = None
) -> None:
    """Route structlog and stdlib logging to one stream in one format. Call once at startup.

    `stream` defaults to stdout; tests pass an in-memory buffer.
    """
    shared: list[Processor] = [
        structlog.contextvars.merge_contextvars,  # request-scoped fields
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _redact_secrets,
    ]

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer: Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,  # applied to stdlib records (uvicorn, httpx, ...)
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,  # tracebacks as a string field
            renderer,
        ],
    )

    # stdout, not stderr: containers and log collectors read stdout.
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn installs its own handlers; drop them so its logs use ours.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def get_logger(name: str | None = None) -> Any:
    """A structlog logger; pass `__name__` so lines show which module logged them."""
    return structlog.stdlib.get_logger(name)


def bind_context(**fields: Any) -> None:
    """Attach fields to every log line for the rest of the current request/task."""
    structlog.contextvars.bind_contextvars(**fields)


def clear_context() -> None:
    structlog.contextvars.clear_contextvars()
