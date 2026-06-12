"""
Tests for Rate Limiting & Abuse Resistance (Step 15): the sliding-window
limiter, privacy-preserving IP truncation, the ephemeral blocklist, the
middleware (429 + headers), and the admin abuse endpoints.
"""

import uuid

import pytest
from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _reset_limiter():
    """Each test starts from clean in-memory state."""
    from app.middleware.rate_limit import blocklist, limiter
    from app.services import abuse_metrics

    limiter._windows.clear()
    blocklist._blocks.clear()
    abuse_metrics.reset()
    yield
    limiter._windows.clear()
    blocklist._blocks.clear()
    abuse_metrics.reset()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _admin_token() -> str:
    from app.database import SessionLocal
    from app.models.user import User
    from app.services.auth import create_jwt

    with SessionLocal() as db:
        user = User(email=f"ab_{uuid.uuid4()}@test.local", role="admin")
        db.add(user)
        db.commit()
        db.refresh(user)
        return create_jwt(user)


# ============================================================================ #
# Limiter unit
# ============================================================================ #
class TestSlidingWindow:
    def test_allows_then_denies(self):
        from app.middleware.rate_limit import SlidingWindowRateLimiter

        rl = SlidingWindowRateLimiter()
        a1, h1 = rl.is_allowed("k", 2, 60)
        a2, h2 = rl.is_allowed("k", 2, 60)
        a3, h3 = rl.is_allowed("k", 2, 60)
        assert a1 and a2 and not a3
        assert h1["X-RateLimit-Limit"] == "2"
        assert h1["X-RateLimit-Remaining"] == "1"
        assert h2["X-RateLimit-Remaining"] == "0"
        assert h3["X-RateLimit-Remaining"] == "0"

    def test_keys_are_independent(self):
        from app.middleware.rate_limit import SlidingWindowRateLimiter

        rl = SlidingWindowRateLimiter()
        assert rl.is_allowed("a", 1, 60)[0] is True
        assert rl.is_allowed("a", 1, 60)[0] is False
        assert rl.is_allowed("b", 1, 60)[0] is True


class TestTruncateIP:
    def test_ipv4_keeps_24(self):
        from app.middleware.rate_limit import truncate_ip

        assert truncate_ip("192.168.1.42") == "192.168.1.0/24"

    def test_ipv6_keeps_64(self):
        from app.middleware.rate_limit import truncate_ip

        assert truncate_ip("2001:db8:1:2:3:4:5:6") == "2001:db8:1:2::/64"


class TestBlocklist:
    def test_block_and_expire(self):
        import time as _t

        from app.middleware.rate_limit import IPBlocklist

        bl = IPBlocklist()
        bl.block("10.0.0.0/24", duration_seconds=3600)
        assert bl.is_blocked("10.0.0.7") is True
        assert bl.is_blocked("8.8.8.8") is False

        # Force expiry.
        bl._blocks["10.0.0.0/24"] = _t.time() - 1
        assert bl.is_blocked("10.0.0.7") is False


# ============================================================================ #
# Middleware integration (its own tiny app, limiting enabled)
# ============================================================================ #
class TestMiddleware:
    def _app(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, public_limit=(2, 60))

        @app.get("/api/ping")
        def ping():
            return {"ok": True}

        return app

    @pytest.mark.asyncio
    async def test_headers_and_429(self):
        transport = ASGITransport(app=self._app())
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            r1 = await ac.get("/api/ping")
            r2 = await ac.get("/api/ping")
            r3 = await ac.get("/api/ping")

        assert r1.status_code == 200
        assert r1.headers["X-RateLimit-Limit"] == "2"
        assert r2.status_code == 200
        assert r3.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry-After" in r3.headers
        body = r3.json()
        assert "retry_after_seconds" in body

    @pytest.mark.asyncio
    async def test_health_is_exempt(self):
        from app.middleware.rate_limit import RateLimitMiddleware

        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, public_limit=(1, 60))

        @app.get("/api/health")
        def health():
            return {"status": "ok"}

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            for _ in range(5):
                assert (await ac.get("/api/health")).status_code == 200


# ============================================================================ #
# Admin abuse endpoints
# ============================================================================ #
class TestAbuseEndpoints:
    @pytest.mark.asyncio
    async def test_block_ip_and_stats(self, client):
        token = _admin_token()
        resp = await client.post(
            "/api/admin/abuse/block-ip",
            json={"ip_prefix": "203.0.113.0/24", "duration_hours": 2, "reason": "scan"},
            headers=_headers(token),
        )
        assert resp.status_code == 200
        assert resp.json()["blocked"] == "203.0.113.0/24"

        stats = await client.get("/api/admin/abuse/stats", headers=_headers(token))
        assert stats.status_code == 200
        body = stats.json()
        assert "203.0.113.0/24" in body["blocked_prefixes"]
        assert "rate_limit" in body

    @pytest.mark.asyncio
    async def test_abuse_requires_admin(self, client):
        from app.database import SessionLocal
        from app.models.user import User
        from app.services.auth import create_jwt

        with SessionLocal() as db:
            u = User(email=f"abu_{uuid.uuid4()}@test.local", role="user")
            db.add(u)
            db.commit()
            db.refresh(u)
            token = create_jwt(u)
        resp = await client.get("/api/admin/abuse/stats", headers=_headers(token))
        assert resp.status_code == status.HTTP_403_FORBIDDEN
