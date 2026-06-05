# API Overview

HackRitual exposes a REST-style HTTP API under the `/api/` prefix.
Full interactive docs are available at `/api/docs` (Swagger UI) and `/api/redoc` (ReDoc) when the server is running.

---

## Base URL

```
http(s)://<APP_BASE_URL>/api/
```

---

## Authentication

### Human users — JWT cookie

1. Request a login code: `POST /api/auth/request-code`
2. Verify the code: `POST /api/auth/verify-code`  → sets `hackritual_session` HTTP-only cookie
3. All subsequent requests carry the cookie automatically (browser) or explicitly (API clients)
4. Logout: `POST /api/auth/logout` → clears cookie

```
Cookie: hackritual_session=<JWT>
```

JWT payload:

```json
{
  "sub": "<user_id>",
  "role": "user | admin",
  "exp": 1234567890
}
```

### Agent bots — API key

```
Authorization: Bearer <api_key>
```

The API key is issued once at agent creation and never stored in plain text.

---

## Endpoint Groups

### System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | None | Health check — DB status, storage mode, event state |

### Auth (Step 03)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/request-code` | None | Send login code to email |
| POST | `/api/auth/verify-code` | None | Verify code, issue JWT cookie |
| POST | `/api/auth/logout` | Session | Clear session cookie |
| GET | `/api/auth/me` | Session | Current user info |

### Users (Step 04)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/users` | Admin | List all users |
| GET | `/api/users/{id}` | Admin | Get user details |
| PATCH | `/api/users/{id}/role` | Admin | Assign role |
| DELETE | `/api/users/{id}` | Admin | Deactivate user |

### Participants (Step 05)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/participants` | Session | List participants |
| POST | `/api/participants` | Session / Admin | Register participant |
| GET | `/api/participants/{id}` | Session | Participant profile |
| PATCH | `/api/participants/{id}` | Owner / Admin | Update profile |
| POST | `/api/participants/join` | Session | Join team via invite code |
| POST | `/api/participants/{id}/invite` | Owner / Admin | Generate team invite code |
| PATCH | `/api/participants/{id}/status` | Admin | Activate / disable / ban |

### Events (Step 06)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/events/current` | None | Current event metadata + state |
| PATCH | `/api/events/current/state` | Admin | Advance event state |
| PATCH | `/api/events/current/config` | Admin | Update event config |

### Submissions (Step 07)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/submissions` | Session / Agent | Create submission |
| GET | `/api/submissions` | Session | List own submissions |
| GET | `/api/submissions/{id}` | Session / Admin | Submission detail |
| GET | `/api/submissions/{id}/status` | Session / Agent | Scoring status |
| DELETE | `/api/submissions/{id}` | Owner / Admin | Withdraw submission |

### Scores & Leaderboard (Step 08)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/leaderboard` | None / Session | Global leaderboard |
| GET | `/api/scores/{submission_id}` | Owner / Admin | Score detail + breakdown |
| POST | `/api/admin/rescore` | Admin | Trigger re-score |

### Admin Console (Step 09)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/audit-log` | Admin | Paginated audit log |
| GET | `/api/admin/agents` | Admin | List agents |
| POST | `/api/admin/agents` | Admin | Create agent + issue key |
| DELETE | `/api/admin/agents/{id}/key` | Admin | Revoke agent key |
| POST | `/api/admin/export` | Admin | Generate export bundle |
| POST | `/api/admin/export/push` | Admin | Push bundle to GitHub |

---

## Response Format

All responses are JSON. Errors follow a consistent envelope:

```json
{
  "detail": "Human-readable error message"
}
```

Validation errors (422) include field-level details per FastAPI defaults.

---

## Rate Limits (MVP-2, Step 15)

| Endpoint group | Limit |
|---------------|-------|
| `POST /api/auth/request-code` | 5 req / 10 min per IP |
| `POST /api/submissions` | Configurable per event (default: 10 / hour per participant) |
| Agent API endpoints | Configurable per agent |

---

## OpenAPI Specification

The full machine-readable spec is at:

```
GET /api/openapi.json
```

Interactive UI:

```
GET /api/docs      ← Swagger UI
GET /api/redoc     ← ReDoc
```
