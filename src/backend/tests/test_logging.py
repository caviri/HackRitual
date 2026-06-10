"""Tests for the JSON logging formatter."""

from __future__ import annotations

import json
import logging
from io import StringIO


def test_json_formatter_emits_valid_json():
    from app.utils.logging import _JsonFormatter

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_JsonFormatter())

    logger = logging.getLogger("test_json_fmt")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    logger.info("hello world")

    output = stream.getvalue().strip()
    record = json.loads(output)

    assert record["msg"] == "hello world"
    assert record["level"] == "INFO"
    assert record["logger"] == "test_json_fmt"
    assert "ts" in record


def test_json_formatter_includes_extra_fields():
    from app.utils.logging import _JsonFormatter

    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_JsonFormatter())

    logger = logging.getLogger("test_json_extra")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    logger.info("startup", extra={"event_id": "evt-test"})

    record = json.loads(stream.getvalue().strip())
    assert record["event_id"] == "evt-test"


def test_configure_logging_sets_level():
    from app.utils.logging import configure_logging
    configure_logging("DEBUG")
    assert logging.getLogger().level == logging.DEBUG
    # reset
    configure_logging("WARNING")
