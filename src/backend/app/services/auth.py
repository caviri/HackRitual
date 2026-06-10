"""
Authentication service — the forge of identity.

Responsibilities:
- Access-password login (lookup on the unique `users.access_password` column)
- In-memory per-IP throttling of failed login attempts
- JWT creation and decoding
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from jose import jwt
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Rate limiter — in-memory, keyed by (bucket, identifier)
# Structure: {key: [(timestamp, ...), ...]}
# ------------------------------------------------------------------ #

_rate_buckets: dict[str, list[float]] = defaultdict(list)

_LOGIN_WINDOW = 15 * 60   # 15 minutes
_LOGIN_MAX_FAILURES = 10  # failed attempts per IP per window


def _count_recent(key: str, window: int) -> int:
    now = time.monotonic()
    cutoff = now - window
    _rate_buckets[key] = [t for t in _rate_buckets[key] if t > cutoff]
    return len(_rate_buckets[key])


def _record_attempt(key: str) -> None:
    _rate_buckets[key].append(time.monotonic())


def check_rate_limit_login(ip: str | None) -> bool:
    """Return True if this IP is still allowed to attempt a login.

    The password is the sole credential, so this throttle is load-bearing:
    it is what makes the password's entropy sufficient. Only failures count
    (successful logins never lock anyone out).
    """
    if not ip:
        return True
    return _count_recent(f"login:ip:{ip}", _LOGIN_WINDOW) < _LOGIN_MAX_FAILURES


def record_login_failure(ip: str | None) -> None:
    if ip:
        _record_attempt(f"login:ip:{ip}")


def clear_login_failures(ip: str | None) -> None:
    if ip:
        _rate_buckets.pop(f"login:ip:{ip}", None)


# ------------------------------------------------------------------ #
# Password login
# ------------------------------------------------------------------ #

def get_user_by_password(db: Session, raw: str) -> User | None:
    """Resolve an active user from a submitted access password.

    Returns None for unknown, empty, or inactive credentials. NULL-password
    users (e.g. pre-migration accounts) can never match.
    """
    from app.models.user import User

    password = (raw or "").strip().lower()
    if not password:
        return None
    return (
        db.query(User)
        .filter(User.access_password == password, User.status == "active")
        .first()
    )


# ------------------------------------------------------------------ #
# JWT
# ------------------------------------------------------------------ #

def create_jwt(user: User) -> str:
    from app.config import settings

    now = datetime.now(UTC)
    payload = {
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_jwt(token: str) -> dict:
    """Decode and validate a JWT. Raises JWTError on failure."""
    from app.config import settings

    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def is_near_expiry(payload: dict, threshold_minutes: int = 60) -> bool:
    """Return True if the token expires within threshold_minutes."""
    exp = payload.get("exp", 0)
    return (exp - time.time()) < threshold_minutes * 60
