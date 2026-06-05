"""
Structured JSON logging setup for HackRitual.
Call configure_logging() once at application startup.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class _JsonFormatter(logging.Formatter):
    """
    Logging formatter that serialises each log record to a single-line JSON string.

    Standard fields emitted for every record:

    - ``ts``     — UTC ISO 8601 timestamp
    - ``level``  — log level name (e.g. ``"INFO"``)
    - ``logger`` — logger name (e.g. ``"app.routers.health"``)
    - ``msg``    — formatted log message

    Optional fields:

    - ``exc``    — formatted exception traceback (if ``exc_info`` is set)
    - ``stack``  — stack info string (if ``stack_info`` is set)
    - Any extra key/value pairs passed via ``extra={}`` in the log call.

    Internal ``logging.LogRecord`` bookkeeping attributes are excluded from output.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialise a log record to a JSON string.

        Args:
            record: The log record produced by a ``logging.Logger`` call.

        Returns:
            A single-line JSON string suitable for stdout/stderr streaming.
        """
        payload: dict[str, object] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        # Any extra fields attached to the record
        for key, value in record.__dict__.items():
            if key not in {
                "args", "asctime", "created", "exc_info", "exc_text",
                "filename", "funcName", "id", "levelname", "levelno",
                "lineno", "module", "msecs", "message", "msg", "name",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "thread", "threadName", "taskName",
            }:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    """
    Replace root logger handlers with a single JSON-to-stdout handler.
    Should be called once, before any other imports that create loggers.
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(numeric_level)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = True
