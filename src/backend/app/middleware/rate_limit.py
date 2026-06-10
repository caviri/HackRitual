"""
Rate limiting & IP abuse resistance (Step 15).

A sliding-window limiter keyed by truncated IP (public), session-token hash
(users), or API-key hash (agents) — whichever fits the request. Plus an
ephemeral IP blocklist for admin abuse response. Everything here is in-memory
and privacy-preserving: full IPs are never stored, only /24 (v4) or /64 (v6)
networks, and the windows clear on restart.

The auth-code and submission-cap limits live elsewhere (Steps 03 / 07); this is
the global IP/abuse layer, and it stamps `X-RateLimit-*` on every API response.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.services import abuse_metrics


def truncate_ip(ip: str) -> str:
    """Privacy-preserving network key: keep /24 (IPv4) or /64 (IPv6)."""
    if ":" in ip:  # IPv6 — keep the first four hextets
        parts = ip.split(":")[:4]
        return ":".join(parts) + "::/64"
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3]) + ".0/24"
    return ip  # not an address we recognise — use as-is


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


class SlidingWindowRateLimiter:
    """In-memory sliding-window counter. One process, one source of truth."""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(
        self, key: str, max_requests: int, window_seconds: int
    ) -> tuple[bool, dict]:
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            hits = [t for t in self._windows[key] if t > cutoff]
            remaining = max_requests - len(hits)
            allowed = remaining > 0
            if allowed:
                hits.append(now)
                remaining -= 1
            self._windows[key] = hits
        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(int(now + window_seconds)),
        }
        return allowed, headers

    def cleanup(self) -> None:
        now = time.time()
        with self._lock:
            dead = [
                k
                for k, v in self._windows.items()
                if not v or max(v) < now - 3600
            ]
            for k in dead:
                del self._windows[k]


class IPBlocklist:
    """Ephemeral, auto-expiring block of IP networks."""

    def __init__(self) -> None:
        self._blocks: dict[str, float] = {}  # network → expiry epoch
        self._lock = threading.Lock()

    def block(self, ip_prefix: str, duration_seconds: int, reason: str = "") -> float:
        expiry = time.time() + duration_seconds
        with self._lock:
            self._blocks[ip_prefix] = expiry
        return expiry

    def is_blocked(self, ip: str) -> bool:
        network = truncate_ip(ip)
        now = time.time()
        with self._lock:
            # Drop expired entries lazily.
            for prefix in list(self._blocks):
                if self._blocks[prefix] < now:
                    del self._blocks[prefix]
            return network in self._blocks or ip in self._blocks

    def active(self) -> dict[str, float]:
        now = time.time()
        with self._lock:
            return {p: e for p, e in self._blocks.items() if e >= now}


# Module-level singletons — shared by the middleware and the admin endpoints.
limiter = SlidingWindowRateLimiter()
blocklist = IPBlocklist()

# Paths exempt from limiting (health probes hit constantly).
_EXEMPT = {"/api/health"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Applies the IP/abuse layer and stamps rate-limit headers on responses."""

    def __init__(
        self,
        app,
        public_limit: tuple[int, int] = (60, 60),
        user_limit: tuple[int, int] = (120, 60),
        agent_limit: tuple[int, int] = (60, 60),
    ) -> None:
        super().__init__(app)
        self.public_limit = public_limit
        self.user_limit = user_limit
        self.agent_limit = agent_limit

    def _resolve(self, request: Request, ip: str) -> tuple[str, int, int]:
        path = request.url.path
        auth = request.headers.get("Authorization", "")
        api_key = request.headers.get("X-API-Key")

        if path.startswith("/api/agent") and (api_key or auth.startswith("Bearer ak_")):
            raw = api_key or auth[len("Bearer ") :]
            return f"agent:{_hash(raw)}", *self.agent_limit

        session = request.cookies.get("session")
        if auth.startswith("Bearer ") or session:
            token = auth[len("Bearer ") :] if auth.startswith("Bearer ") else session
            return f"user:{_hash(token or '')}", *self.user_limit

        return f"ip:{truncate_ip(ip)}", *self.public_limit

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if not path.startswith("/api") or path in _EXEMPT:
            return await call_next(request)

        ip = request.client.host if request.client else "anon"

        if blocklist.is_blocked(ip):
            abuse_metrics.record_trigger()
            return JSONResponse(
                status_code=403,
                content={"detail": "Your network is temporarily blocked."},
            )

        key, max_req, window = self._resolve(request, ip)
        allowed, headers = limiter.is_allowed(key, max_req, window)

        if not allowed:
            abuse_metrics.record_trigger()
            retry = max(1, int(headers["X-RateLimit-Reset"]) - int(time.time()))
            headers = {**headers, "Retry-After": str(retry)}
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after_seconds": retry,
                },
                headers=headers,
            )

        response = await call_next(request)
        for k, v in headers.items():
            response.headers[k] = v
        return response
