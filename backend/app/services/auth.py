"""
Authentication service — the forge of identity.

Responsibilities:
- 6-digit magic code generation and SHA-256 hashing
- LoginCode persistence and verification
- JWT creation and decoding
- In-memory rate limiting (MVP-1; replaced by DB-backed in Step 15)
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from jose import JWTError, jwt
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.user import User

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Rate limiter — in-memory, keyed by (bucket, identifier)
# Structure: {key: [(timestamp, ...), ...]}
# ------------------------------------------------------------------ #

_rate_buckets: dict[str, list[float]] = defaultdict(list)

_CODE_REQUEST_WINDOW = 15 * 60   # 15 minutes
_CODE_REQUEST_MAX_EMAIL = 3
_CODE_REQUEST_MAX_IP = 10
_CODE_VERIFY_MAX_ATTEMPTS = 5


def _count_recent(key: str, window: int) -> int:
    now = time.monotonic()
    cutoff = now - window
    _rate_buckets[key] = [t for t in _rate_buckets[key] if t > cutoff]
    return len(_rate_buckets[key])


def _record_attempt(key: str) -> None:
    _rate_buckets[key].append(time.monotonic())


def check_rate_limit_request_code(email: str, ip: str | None) -> bool:
    """Return True if the request is within rate limits."""
    email_key = f"req_code:email:{email.lower()}"
    if _count_recent(email_key, _CODE_REQUEST_WINDOW) >= _CODE_REQUEST_MAX_EMAIL:
        return False
    if ip:
        ip_key = f"req_code:ip:{ip}"
        if _count_recent(ip_key, _CODE_REQUEST_WINDOW) >= _CODE_REQUEST_MAX_IP:
            return False
    return True


def record_code_request(email: str, ip: str | None) -> None:
    _record_attempt(f"req_code:email:{email.lower()}")
    if ip:
        _record_attempt(f"req_code:ip:{ip}")


def check_rate_limit_verify(email: str) -> bool:
    """Return True if verification attempts are within limits."""
    key = f"verify:email:{email.lower()}"
    return _count_recent(key, _CODE_REQUEST_WINDOW) < _CODE_VERIFY_MAX_ATTEMPTS


def record_verify_attempt(email: str) -> None:
    _record_attempt(f"verify:email:{email.lower()}")


def invalidate_verify_attempts(email: str) -> None:
    """Clear all verification attempts for an email (after max failures)."""
    _rate_buckets.pop(f"verify:email:{email.lower()}", None)


# ------------------------------------------------------------------ #
# Code generation
# ------------------------------------------------------------------ #

def generate_code() -> str:
    """Return a cryptographically random 6-digit string."""
    return str(secrets.randbelow(900_000) + 100_000)


def hash_code(code: str) -> str:
    """SHA-256 hash of the raw code string."""
    return hashlib.sha256(code.encode()).hexdigest()


def hash_ip(ip: str) -> str:
    """One-way hash of an IP address — never stored raw (§14.4)."""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


# ------------------------------------------------------------------ #
# LoginCode persistence
# ------------------------------------------------------------------ #

def create_login_code(
    email: str,
    db: Session,
    request_ip: str | None = None,
    expires_minutes: int = 10,
) -> tuple[str, "LoginCodeRecord"]:
    """
    Generate a code, persist a hashed record, return (raw_code, record).
    The raw code is only ever returned here — never stored.
    """
    from app.models.login_code import LoginCode

    code = generate_code()
    record = LoginCode(
        email=email.lower().strip(),
        code_hash=hash_code(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        request_ip=hash_ip(request_ip) if request_ip else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return code, record


def verify_login_code(email: str, code: str, db: Session) -> bool:
    """
    Check the code against unexpired, unused records for this email.
    Marks the code used on success. Returns True on success.
    """
    from app.models.login_code import LoginCode

    now = datetime.now(timezone.utc)
    # Fetch the most recent unexpired, unused code for this email
    record = (
        db.query(LoginCode)
        .filter(
            LoginCode.email == email.lower().strip(),
            LoginCode.used_at.is_(None),
            LoginCode.expires_at > now,
        )
        .order_by(LoginCode.expires_at.desc())
        .first()
    )

    if record is None:
        return False

    if record.code_hash != hash_code(code):
        return False

    record.used_at = now
    db.commit()
    return True


def invalidate_all_codes(email: str, db: Session) -> None:
    """Mark all unused codes for an email as used (after max failures)."""
    from app.models.login_code import LoginCode

    now = datetime.now(timezone.utc)
    db.query(LoginCode).filter(
        LoginCode.email == email.lower().strip(),
        LoginCode.used_at.is_(None),
    ).update({"used_at": now})
    db.commit()


def cleanup_expired_codes(db: Session) -> int:
    """Delete all expired login codes. Returns the count deleted."""
    from app.models.login_code import LoginCode

    now = datetime.now(timezone.utc)
    deleted = db.query(LoginCode).filter(LoginCode.expires_at <= now).delete()
    db.commit()
    return deleted


# ------------------------------------------------------------------ #
# User management (first-login auto-create)
# ------------------------------------------------------------------ #

def get_or_create_user(email: str, db: Session) -> "User":
    """Return the User for this email, creating one with role='user' on first login."""
    from app.models.user import User

    email = email.lower().strip()
    user = db.query(User).filter_by(email=email).first()
    if user is None:
        user = User(email=email, role="user")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("New user registered on first login", extra={"email": email})
    else:
        user.last_login_at = datetime.now(timezone.utc)
        db.commit()
    return user


# ------------------------------------------------------------------ #
# JWT
# ------------------------------------------------------------------ #

def create_jwt(user: "User") -> str:
    from app.config import settings

    now = datetime.now(timezone.utc)
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
