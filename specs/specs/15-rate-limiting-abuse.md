# 15 — Rate Limiting & Abuse Resistance

**Milestone:** MVP-2
**Priority:** High
**Dependencies:** [03-authentication](03-authentication.md), [07-submission-system](07-submission-system.md), [13-agent-system](13-agent-system.md)
**Specs reference:** §6.4 (Abuse Resistance)

---

## Overview

Implement rate limiting and abuse prevention across all public and authenticated endpoints. This includes IP-based rate limiting for public endpoints, user/agent-based limits for authenticated endpoints, and submission caps. Also covers admin moderation tools for abuse response.

---

## Tasks

### 15.1 Rate Limiting Strategy

Three layers of rate limiting:

| Layer | Scope | Storage | Purpose |
|-------|-------|---------|---------|
| Global | Per IP | In-memory (sliding window) | Prevent DDoS / scanning |
| Auth | Per user/agent | In-memory | Prevent credential stuffing |
| Submission | Per participant | DB query | Enforce event rules |

### 15.2 Rate Limiter Implementation

Use a sliding window counter in memory:

```python
# backend/app/middleware/rate_limiter.py

from collections import defaultdict
from time import time

class SlidingWindowRateLimiter:
    def __init__(self):
        self.windows: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> tuple[bool, dict]:
        now = time()
        cutoff = now - window_seconds

        # Clean old entries
        self.windows[key] = [t for t in self.windows[key] if t > cutoff]

        # Check limit
        remaining = max_requests - len(self.windows[key])
        allowed = remaining > 0

        if allowed:
            self.windows[key].append(now)
            remaining -= 1

        reset_at = int(now + window_seconds)
        headers = {
            "X-RateLimit-Limit": str(max_requests),
            "X-RateLimit-Remaining": str(max(0, remaining)),
            "X-RateLimit-Reset": str(reset_at),
        }
        return allowed, headers

    def cleanup(self):
        """Periodic cleanup of expired windows."""
        now = time()
        expired_keys = [k for k, v in self.windows.items() if not v or max(v) < now - 3600]
        for k in expired_keys:
            del self.windows[k]
```

### 15.3 Rate Limit Configuration

| Endpoint | Key | Limit | Window |
|----------|-----|-------|--------|
| `POST /api/auth/request-code` | IP | 10 | 15 min |
| `POST /api/auth/request-code` | Email | 3 | 15 min |
| `POST /api/auth/verify-code` | Email | 5 | 10 min |
| `POST /api/submissions` | User ID | 20 | 1 hour |
| `POST /api/agent/submissions` | Agent ID | 20 | 1 hour |
| `GET /api/*` (authenticated) | User ID | 120 | 1 min |
| `* /api/agent/*` | Agent ID | 60 | 1 min |
| `* /api/*` (public) | IP | 60 | 1 min |

### 15.4 FastAPI Middleware

```python
# backend/app/middleware/rate_limit_middleware.py

class RateLimitMiddleware:
    def __init__(self, app, limiter: SlidingWindowRateLimiter):
        self.app = app
        self.limiter = limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        client_ip = self._get_client_ip(scope)

        # Determine rate limit key and config based on path
        key, max_req, window = self._get_limit_config(path, client_ip, scope)

        allowed, headers = self.limiter.is_allowed(key, max_req, window)

        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers=headers,
            )
            await response(scope, receive, send)
            return

        # Add rate limit headers to response
        # ... proceed with request
```

### 15.5 IP Handling (Privacy-Compliant)

Per specs §14.4:

```python
def get_rate_limit_key(ip: str) -> str:
    """Generate a privacy-respecting rate limit key from IP."""
    # Truncate: keep only /24 for IPv4, /64 for IPv6
    if ":" in ip:  # IPv6
        parts = ip.split(":")[:4]
        truncated = ":".join(parts) + "::/64"
    else:  # IPv4
        parts = ip.split(".")[:3]
        truncated = ".".join(parts) + ".0/24"
    return f"ip:{truncated}"
```

- Rate limit keys use truncated IPs, never full IPs
- In-memory only — never written to DB or logs
- Memory is cleared on container restart (acceptable)

### 15.6 Submission Caps

Separate from rate limiting — these are event-rule enforced limits:

```python
class SubmissionCapService:
    def check_cap(self, db: Session, participant_id: str, event_config: dict) -> bool:
        """Check if participant has exceeded submission cap."""
        limit = event_config.get("submission_limit_per_participant", 10)
        window_hours = event_config.get("submission_limit_window_hours", 24)

        window_start = datetime.utcnow() - timedelta(hours=window_hours)
        count = db.query(Submission).filter(
            Submission.participant_id == participant_id,
            Submission.created_at >= window_start,
            Submission.status != "withdrawn",
        ).count()

        return count < limit

    def get_remaining(self, db, participant_id, event_config) -> dict:
        """Return remaining submissions and reset time."""
        # ... calculate remaining count and window reset
```

### 15.7 Admin Moderation Tools

Quick-action endpoints for abuse response:

#### Disable participant
`PATCH /api/admin/participants/{id}/status`
```json
{ "status": "disabled", "reason": "Suspected bot behavior" }
```

#### Revoke agent key
`POST /api/admin/agents/{id}/revoke`
```json
{ "reason": "Excessive automated submissions" }
```

#### Freeze submissions (global)
Already handled by event state → `FROZEN`

#### Ban IP range (temporary)
`POST /api/admin/abuse/block-ip`
```json
{
  "ip_prefix": "192.168.1.0/24",
  "duration_hours": 24,
  "reason": "DDoS attempt"
}
```
- In-memory blocklist only
- Auto-expires after duration
- Not persisted (clears on restart)

### 15.8 Rate Limit Metrics

Track aggregate counters per specs §14.5:

```python
# Increment daily counter when rate limit is triggered
metrics_service.increment("rate_limit_triggered", date=today)
```

- Count of rate limit triggers per day (aggregate only)
- No per-user or per-IP metrics stored

### 15.9 Rate Limit Response Format

When a limit is hit, return:

```json
{
  "detail": "Too many requests. Please try again later.",
  "retry_after_seconds": 45
}
```

**HTTP 429 headers:**
```
Retry-After: 45
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1709312400
```

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| PATCH | `/api/admin/participants/{id}/status` | Admin | Disable/ban participant |
| POST | `/api/admin/agents/{id}/revoke` | Admin | Revoke agent key |
| POST | `/api/admin/abuse/block-ip` | Admin | Temporary IP block |
| GET | `/api/admin/abuse/stats` | Admin | Abuse metrics overview |

---

## Acceptance Criteria

- [ ] Public endpoints rate-limited by (truncated) IP
- [ ] Auth endpoints rate-limited by user/email
- [ ] Agent endpoints rate-limited by agent ID
- [ ] Submission caps enforced per participant per time window
- [ ] Rate limit headers present in all API responses
- [ ] 429 responses include `Retry-After` header
- [ ] Admin can disable participants and revoke agent keys
- [ ] IP handling complies with privacy policy (no full IPs stored)
- [ ] Rate limit counters are in-memory only (cleared on restart)
- [ ] Aggregate rate limit metrics tracked for admin dashboard

---

## Developer Notes

- In-memory rate limiting is acceptable for a single-container deployment
- The sliding window approach is more accurate than fixed windows for burst protection
- Consider using `slowapi` (Starlette rate limiter) as an alternative to custom implementation
- Run `cleanup()` periodically (every 5 minutes) to prevent memory growth
- For the login code flow, rate limit by both IP AND email to prevent distributed attacks
- Test rate limits with `ab` or `hey` to verify they work under load
- The IP blocklist is intentionally ephemeral — persistent blocking would need DB storage
