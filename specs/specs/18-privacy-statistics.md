# 18 — Privacy & Statistics

**Milestone:** Cross-cutting (implement incrementally across all MVPs)
**Priority:** High
**Dependencies:** [02-database-layer](02-database-layer.md)
**Specs reference:** §14 (Privacy-Respecting Statistics & Minimal Cookies)

---

## Overview

HackRitual collects only what is strictly necessary to operate the event. No tracking, no profiling, no third-party analytics. Statistics are aggregate-only. This task covers the metrics system, IP handling policy, cookie policy, data retention, and the privacy notice page.

---

## Tasks

### 18.1 Aggregate Metrics Table

```sql
CREATE TABLE metrics_daily (
    date TEXT NOT NULL,                    -- YYYY-MM-DD
    submissions_count INTEGER DEFAULT 0,
    logins_count INTEGER DEFAULT 0,
    agent_submissions_count INTEGER DEFAULT 0,
    email_sent_count INTEGER DEFAULT 0,
    rate_limit_triggered_count INTEGER DEFAULT 0,
    scoring_avg_ms REAL DEFAULT 0,
    scoring_max_ms REAL DEFAULT 0,
    PRIMARY KEY (date)
);
```

### 18.2 Metrics Service

```python
# backend/app/services/metrics_service.py

class MetricsService:
    def increment(self, db: Session, metric: str, value: int = 1):
        """Increment a daily metric counter."""
        today = date.today().isoformat()
        # UPSERT: INSERT OR UPDATE
        db.execute(text("""
            INSERT INTO metrics_daily (date, {metric})
            VALUES (:date, :value)
            ON CONFLICT(date)
            DO UPDATE SET {metric} = {metric} + :value
        """), {"date": today, "value": value})
        db.commit()

    def record_scoring_time(self, db: Session, duration_ms: float):
        """Update scoring average and max for today."""
        # ...

    def get_daily_stats(self, db: Session, start: date, end: date) -> list[dict]:
        """Retrieve daily metrics for a date range."""
```

**Where to increment:**
- `logins_count` → after successful code verification
- `submissions_count` → after submission created
- `agent_submissions_count` → after agent submission
- `email_sent_count` → after email sent
- `rate_limit_triggered_count` → when rate limit returns 429
- `scoring_avg_ms` / `scoring_max_ms` → after scoring completes

### 18.3 Page View Counter (Optional)

```sql
CREATE TABLE page_views (
    route TEXT PRIMARY KEY,
    count INTEGER DEFAULT 0
);
```

- Increment per route, not per user
- No session tracking, no identity
- Example: "Leaderboard viewed 240 times"

Implementation as lightweight middleware:
```python
class PageViewMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "GET":
            route = scope["path"]
            # Debounce: batch updates every N requests
            self.buffer[route] = self.buffer.get(route, 0) + 1
            if sum(self.buffer.values()) >= 50:
                self.flush_to_db()
```

### 18.4 IP Handling Implementation

Per specs §14.4:

```python
# backend/app/utils/privacy.py

import hashlib
from datetime import date

# Daily rotating salt for IP hashing
def get_daily_salt() -> str:
    return f"hackritual-{date.today().isoformat()}"

def hash_ip(ip: str) -> str:
    """Hash IP with daily-rotating salt. Expires implicitly."""
    salt = get_daily_salt()
    return hashlib.sha256(f"{salt}:{ip}".encode()).hexdigest()[:16]

def truncate_ip(ip: str) -> str:
    """Truncate IP to /24 (IPv4) or /64 (IPv6)."""
    if ":" in ip:
        return ":".join(ip.split(":")[:4]) + "::"
    return ".".join(ip.split(".")[:3]) + ".0"
```

Rules:
- **Default:** Do not store IPs in the database
- **Rate limiting:** Use truncated IP transiently (in-memory only)
- **Login codes:** Store `request_ip` as hashed value with daily salt
- **Audit log:** Do not include IPs
- **Export:** Never include IP data

### 18.5 Cookie Policy Implementation

Per specs §14.9:

**Only one cookie:** the session JWT.

```python
# In auth response
response.set_cookie(
    key="session",
    value=jwt_token,
    httponly=True,
    secure=True,
    samesite="lax",
    max_age=86400,
    path="/",
)
```

Checklist:
- [ ] No analytics cookies
- [ ] No marketing cookies
- [ ] No third-party cookies
- [ ] No fingerprinting scripts
- [ ] No localStorage tracking identifiers
- [ ] No `document.cookie` access from JS (HttpOnly)

### 18.6 Privacy Notice Page

Create `/privacy` route in the frontend with static content:

```markdown
# Privacy Notice

## What We Collect
- **Email address**: Used for authentication (magic code login).
- **Display name and affiliation**: Provided voluntarily for your participant profile.
- **Submissions**: Content you submit during the event.

## Cookies
HackRitual uses a single session cookie required for authentication.
No tracking, profiling, or third-party analytics cookies are used.

## Statistics
Operational statistics are stored only in aggregate form.
No per-user analytics are collected.

## IP Addresses
IP addresses are not stored in our database.
They are used transiently for rate limiting and abuse prevention only.

## Data Retention
- Event data is retained until export or deletion.
- Login codes expire within 10 minutes.
- Upon archival, the runtime database may be deleted.
- The public export contains only curated, aggregate data.

## Contact
[Deployer/admin contact information]

## Your Rights
Under GDPR, you have the right to access, rectify, or request deletion
of your personal data. Contact the event administrator.
```

### 18.7 Data Retention Implementation

Per specs §14.12:

| Data | Retention |
|------|-----------|
| Login codes | Auto-expire in 10 minutes, cleanup hourly |
| Sessions (if DB) | Auto-expire per JWT TTL, cleanup daily |
| Rate limit IP hashes | In-memory only, cleared on restart |
| Active event data | Until export or deletion |
| Export bundle | Until admin deletes |
| Metrics | Kept for event duration |

Implement cleanup jobs:
```python
async def cleanup_expired_data(db: Session):
    """Run periodically (hourly) to purge expired data."""
    # Delete expired login codes
    db.query(LoginCode).filter(LoginCode.expires_at < datetime.utcnow()).delete()
    # Delete expired sessions (if using DB sessions)
    db.query(SessionModel).filter(SessionModel.expires_at < datetime.utcnow()).delete()
    db.commit()
```

### 18.8 What Must NOT Be Stored

Enforce via code review and automated checks:

- Full IP addresses (in DB or logs)
- User agents for fingerprinting
- Referrer tracking data
- Cross-session analytics identifiers
- Third-party analytics scripts or pixels
- SMTP response bodies or email content

### 18.9 Export Privacy Controls

When generating export:
- Public mode: hash emails with `sha256(email + event_id)`
- Audit log: hash actor emails in public mode
- Never include: IPs, session data, login codes, rate limit data
- Include: aggregate metrics from `metrics_daily`

### 18.10 Admin Metrics Dashboard

`GET /api/admin/metrics`

**Query params:** `?start=2026-03-01&end=2026-03-02`

```json
{
  "daily": [
    {
      "date": "2026-03-01",
      "submissions": 45,
      "logins": 32,
      "agent_submissions": 12,
      "emails_sent": 35,
      "rate_limits_triggered": 3,
      "scoring_avg_ms": 120,
      "scoring_max_ms": 450
    }
  ],
  "totals": {
    "participants": 42,
    "submissions": 150,
    "teams": 8,
    "agents": 3
  }
}
```

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/metrics` | Admin | Aggregate metrics |
| GET | `/api/admin/metrics/daily` | Admin | Daily breakdown |

---

## Acceptance Criteria

- [ ] Only one cookie set (session, HttpOnly, Secure, SameSite=Lax)
- [ ] No third-party analytics or tracking scripts
- [ ] IP addresses never stored in database
- [ ] Aggregate metrics collected (daily counters)
- [ ] No per-user analytics data
- [ ] Privacy notice page accessible at `/privacy`
- [ ] Expired login codes and sessions auto-cleaned
- [ ] Export does not contain IPs, sessions, or secrets
- [ ] Email hashing works in public export mode
- [ ] Admin can view aggregate metrics in dashboard

---

## Developer Notes

- Privacy compliance is not optional — enforce from the start
- Add a CI check that greps for `request.client.host` to catch accidental IP storage
- The `metrics_daily` table uses UPSERT — works well with SQLite
- Page view tracking is optional and can be disabled via config
- Keep the privacy notice in sync with actual data practices
- Consider adding a `GET /api/privacy` endpoint returning structured privacy info (for programmatic consumers)
