---
id: "003"
title: "Authentication"
type: feature
status: done
estimate: "3d"
size: L
depends_on: ["002"]
blocks: ["004", "013", "015"]
spec: "specs/specs/03-authentication.md"
tags: [auth, jwt, email, magic-link, rate-limiting]
tests_passing: 73
---

# Authentication

Passwordless magic-link authentication via 6-digit email codes, JWT session cookies, and in-memory rate limiting.

## Completed

- [x] `app/services/auth.py` — code gen (6-digit, `secrets`), SHA-256 hash, LoginCode CRUD, verify with expiry/single-use, get_or_create_user
- [x] JWT creation/decoding via `python-jose`, `is_near_expiry`
- [x] In-memory rate limiter: 3/email, 10/IP per 15 min; 5 verify attempts
- [x] `app/services/email.py` — SMTP dispatch via aiosmtplib; console/dev mode fallback; HTML+text login code template
- [x] `app/schemas/auth.py` — request/response Pydantic models; simple regex email validation
- [x] `app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` FastAPI deps
- [x] `app/routers/auth.py` — 5 endpoints: request-code, verify-code, logout, refresh, me

## Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/request-code` | Send magic code to email (rate-limited) |
| POST | `/api/auth/verify-code` | Verify code → issue JWT cookie |
| POST | `/api/auth/logout` | Clear session cookie |
| POST | `/api/auth/refresh` | Renew near-expiry token |
| GET | `/api/auth/me` | Current user info |

## Notes

- Console/dev mode active when `SMTP_HOST` is `localhost`, `127.0.0.1`, or `console`
- Bearer token auth added to middleware (in addition to cookies) for easier API testing
- `EmailStr` (pydantic + email-validator) rejects `.local` TLD; switched to simple regex per spec
