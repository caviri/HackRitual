---
id: "015"
title: "Rate Limiting & Abuse Resistance"
type: feature
status: backlog
estimate: "3d"
size: M
depends_on: ["003", "007", "013"]
blocks: []
spec: "specs/specs/15-rate-limiting-abuse.md"
tags: [rate-limiting, security, backend]
---

# Rate Limiting & Abuse Resistance

Replace in-memory rate limiting (Step 03) with DB-backed rate limiting and add submission abuse prevention.

## Tasks

- [ ] DB-backed rate limit table (replaces `_rate_buckets` in `app/services/auth.py`)
- [ ] Configurable limits per endpoint via env vars or event config
- [ ] Submission rate limiting: max N submissions per participant per hour
- [ ] Agent submission rate limiting: max N requests per API key per minute
- [ ] IP-based blocking for repeated auth failures
- [ ] `GET /api/admin/rate-limits` — current limit state and blocked IPs
- [ ] `POST /api/admin/rate-limits/reset/{key}` — manually clear a rate limit
- [ ] Middleware integration: return `429 Too Many Requests` with `Retry-After` header

## Notes

- Current in-memory rate limits in `app/services/auth.py` are reset on restart; DB-backed is persistent
- Token bucket or sliding window algorithm
- Works with single-process constraint (no Redis needed)
