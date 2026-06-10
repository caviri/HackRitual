"""
Abuse metrics — aggregate, in-memory, content-free.

Per spec §14.5 we count rate-limit triggers per day and nothing else: no IPs, no
users, no per-key tallies. Cleared on restart, like the limiter itself.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone

_lock = threading.Lock()
_by_day: dict[str, int] = {}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def record_trigger() -> None:
    with _lock:
        day = _today()
        _by_day[day] = _by_day.get(day, 0) + 1


def snapshot() -> dict:
    with _lock:
        return {
            "today": _by_day.get(_today(), 0),
            "total": sum(_by_day.values()),
            "by_day": dict(_by_day),
        }


def reset() -> None:
    with _lock:
        _by_day.clear()
