"""
Email metrics — aggregate counters only.

Per spec §12.4 / §14.7 we keep counts, never content: how many emails were
attempted, how many succeeded or failed, and when the last one went out. No
addresses, no bodies, no SMTP responses. In-process and reset-able (tests); a
durable store is a later concern.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

_lock = threading.Lock()
_sent = 0
_succeeded = 0
_failed = 0
_last_sent_at: Optional[str] = None


def record(success: bool) -> None:
    """Tally one delivery attempt."""
    global _sent, _succeeded, _failed, _last_sent_at
    with _lock:
        _sent += 1
        if success:
            _succeeded += 1
        else:
            _failed += 1
        _last_sent_at = datetime.now(timezone.utc).isoformat()


def snapshot() -> dict:
    with _lock:
        return {
            "sent": _sent,
            "succeeded": _succeeded,
            "failed": _failed,
            "last_sent_at": _last_sent_at,
        }


def reset() -> None:
    """Zero the counters (test support)."""
    global _sent, _succeeded, _failed, _last_sent_at
    with _lock:
        _sent = _succeeded = _failed = 0
        _last_sent_at = None
