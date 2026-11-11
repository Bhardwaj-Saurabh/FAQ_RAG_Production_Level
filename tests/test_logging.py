"""Log lines are JSON with standard fields, carry bound context, and never leak secrets."""

import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest

from faq_service.logging import bind_context, clear_context, configure_logging, get_logger


@pytest.fixture
def out() -> Iterator[io.StringIO]:
    """JSON logging configured to write into an in-memory buffer."""
    buffer = io.StringIO()
    configure_logging("INFO", json=True, stream=buffer)
    yield buffer
    clear_context()


def _lines(out: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_line_is_json_with_standard_fields(out: io.StringIO) -> None:
    get_logger("faq_service.test").info("query_answered", model="gpt-4o-mini", latency_ms=812)

    [line] = _lines(out)
    assert line["event"] == "query_answered"
    assert line["level"] == "info"
    assert line["logger"] == "faq_service.test"
    assert line["model"] == "gpt-4o-mini"
    assert line["latency_ms"] == 812
    assert line["timestamp"].endswith("Z")  # ISO 8601, UTC


def test_bound_context_is_added_to_every_line(out: io.StringIO) -> None:
    bind_context(request_id="req-123")
    log = get_logger("faq_service.test")
    log.info("first")
    log.info("second")

    assert [line["request_id"] for line in _lines(out)] == ["req-123", "req-123"]


def test_secret_fields_are_redacted(out: io.StringIO) -> None:
    get_logger().info("client_created", api_key="sk-very-secret", prompt_tokens=42)

    [line] = _lines(out)
    assert line["api_key"] == "***"
    assert line["prompt_tokens"] == 42  # similar-looking keys are untouched
    assert "sk-very-secret" not in json.dumps(line)


def test_stdlib_library_logs_use_the_same_json_format(
    out: io.StringIO,
) -> None:
    logging.getLogger("uvicorn.error").info("Started server process")

    [line] = _lines(out)
    assert line["event"] == "Started server process"
    assert line["logger"] == "uvicorn.error"
    assert line["level"] == "info"


def test_level_filters_lower_messages(out: io.StringIO) -> None:
    configure_logging("WARNING", json=True, stream=out)
    log = get_logger("faq_service.test")
    log.info("hidden")
    log.warning("shown")

    assert [line["event"] for line in _lines(out)] == ["shown"]


def test_exceptions_are_logged_as_a_string_field(out: io.StringIO) -> None:
    try:
        1 / 0  # noqa: B018
    except ZeroDivisionError:
        get_logger().exception("boom")

    [line] = _lines(out)
    assert "ZeroDivisionError" in line["exception"]
