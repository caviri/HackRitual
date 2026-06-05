# 03 — Authentication

**Milestone:** MVP-1
**Priority:** Critical
**Dependencies:** [02-database-layer](02-database-layer.md), [12-email-system](12-email-system.md)
**Specs reference:** §6.2 (Authentication), §6.4 (Abuse Resistance), §14.9 (Cookies)

---

## Overview

Implement passwordless email-based authentication for human users using one-time magic codes. Issue JWT tokens in HTTP-only cookies for session management. Agent authentication (API keys) is covered in [13-agent-system](13-agent-system.md).

---

## Tasks

### 3.1 Magic Code Login Flow

#### Request Code: `POST /api/auth/request-code`

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Server logic:**
1. Generate a 6-digit numeric code (cryptographically random)
2. Hash the code (SHA-256 is sufficient for short-lived codes)
3. Store in `login_codes` table with:
   - `expires_at` = now + 10 minutes (configurable)
   - `request_ip` = truncated IP hash (per privacy policy §14.4)
4. Send code via email (see [12-email-system](12-email-system.md))
5. Return `204 No Content` (never reveal if email exists)

**Rate limiting:**
- Max 3 code requests per email per 15 minutes
- Max 10 code requests per IP per 15 minutes
- Return `429 Too Many Requests` when exceeded

#### Verify Code: `POST /api/auth/verify-code`

**Request:**
```json
{
  "email": "user@example.com",
  "code": "482917"
}
```

**Server logic:**
1. Look up unexpired, unused `login_codes` for that email
2. Verify code hash matches
3. Mark code as `used_at = now`
4. Create User record if first login (role = `user`)
5. Issue JWT token (see §3.2)
6. Return user info + set cookie

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "role": "user"
  }
}
```

**Security:**
- Max 5 verification attempts per email per code window
- After 5 failures, invalidate all codes for that email
- Expired codes must not be verifiable

### 3.2 JWT Session Management

**Token creation:**
```python
payload = {
    "sub": user.id,
    "email": user.email,
    "role": user.role,
    "iat": datetime.utcnow(),
    "exp": datetime.utcnow() + timedelta(hours=24),  # configurable
}
token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
```

**Cookie settings (per specs §14.9):**
```python
response.set_cookie(
    key="session",
    value=token,
    httponly=True,
    secure=True,        # HTTPS only
    samesite="lax",
    max_age=86400,      # 24 hours
    path="/",
)
```

**Token validation middleware:**
- Extract JWT from `session` cookie on every request
- Verify signature and expiration
- Attach user info to request state
- Return `401 Unauthorized` for invalid/missing tokens on protected routes

### 3.3 Logout

`POST /api/auth/logout`

- Clear the session cookie
- Optionally: if using DB sessions, delete session record

### 3.4 Session Refresh

`POST /api/auth/refresh`

- If token is valid but near expiry (e.g., within 1 hour), issue new token
- Set updated cookie
- If token is expired, return `401`

### 3.5 Current User Endpoint

`GET /api/auth/me`

- Return current user info from JWT
- Return `401` if not authenticated

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "role": "admin",
  "participant": {
    "id": "uuid",
    "display_name": "Alice",
    "type": "human"
  }
}
```

### 3.6 Auth Middleware / Dependencies

Create FastAPI dependencies:

```python
async def get_current_user(request: Request, db: Session) -> User:
    """Extract and validate JWT from cookie. Raises 401 if invalid."""

async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Raises 403 if user is not admin."""

async def require_role(roles: list[str]):
    """Factory for role-based dependencies."""
```

### 3.7 Login Code Cleanup

- Implement a periodic cleanup that deletes expired login codes
- Run on app startup and every hour (via background task or worker)
- Per specs §14.12: login codes auto-expire within minutes

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/request-code` | Public | Request magic login code |
| POST | `/api/auth/verify-code` | Public | Verify code, get session |
| POST | `/api/auth/logout` | Authenticated | Clear session |
| POST | `/api/auth/refresh` | Authenticated | Refresh JWT |
| GET | `/api/auth/me` | Authenticated | Get current user info |

---

## Acceptance Criteria

- [ ] User can request a login code and receive it via email
- [ ] Code is 6-digit, cryptographically random, hashed in DB
- [ ] Code expires after 10 minutes and is single-use
- [ ] JWT issued in HTTP-only, Secure, SameSite=Lax cookie
- [ ] Rate limiting prevents brute-force code requests
- [ ] Failed verification attempts are capped (5 per code window)
- [ ] Logout clears session cookie
- [ ] `GET /api/auth/me` returns current user or 401
- [ ] No tracking cookies — only the session cookie is set
- [ ] Admin-seeded users can log in immediately

---

## Developer Notes

- Use `secrets.randbelow(900000) + 100000` for 6-digit codes
- Use `python-jose` or `PyJWT` for JWT handling
- For rate limiting in MVP-1, use in-memory counters (dict with TTL) — move to DB-backed in task [15](15-rate-limiting-abuse.md)
- Always return 204 on code request regardless of email existence (prevent enumeration)
- The `request_ip` field should follow the IP handling policy from §14.4 (truncated or hashed, never stored raw)
