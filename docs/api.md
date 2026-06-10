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

1. Obtain your access password from an organizer (granted on application
   approval or CSV import; admins get theirs from `ADMIN_PASSWORD`)
2. Log in: `POST /api/auth/login` with `{"password": "..."}` → sets `session` HTTP-only cookie
3. All subsequent requests carry the cookie automatically (browser) or explicitly (API clients)
4. Logout: `POST /api/auth/logout` → clears cookie

```
Cookie: session=<JWT>
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

## Complete endpoint reference

This page is the **conceptual** overview (auth, conventions, limits). For the
exhaustive, always-current list of every endpoint — paths, methods, parameters,
request/response bodies, and schemas — use the generated reference, which is
derived directly from the running app's OpenAPI spec:

- **[Full API reference](./api-reference.md)** — every operation + schema, in Markdown.
- **[Interactive explorer (ReDoc)](./redoc.html)** — browse and read the spec in your browser.
- **[`openapi.json`](./openapi.json)** — the machine-readable contract. Feed it to a
  generator to scaffold a typed client:
  ```bash
  npx openapi-typescript docs/openapi.json -o client/schema.ts   # TypeScript types
  openapi-generator-cli generate -i docs/openapi.json -g python -o client/py  # Python client
  ```

On a running server the same spec is live at `/api/openapi.json`, with
`/api/docs` (Swagger UI) and `/api/redoc` (ReDoc).

The endpoints are grouped by tag (auth, participants, projects, submissions,
scores, agents, event, admin, …). The lifecycle is
`DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`; submissions are accepted only while
`OPEN`.

## Build your own client / frontend

A ready-to-use skill with runnable helpers lives at
`.agents/skills/hackritual-api/` in the repository:

- `SKILL.md` — the interaction guide (auth flows, key endpoints).
- `scripts/hackritual.sh` — a curl-based bash CLI.
- `scripts/hackritual_client.py` — a stdlib-only Python client (`HackRitualClient`),
  usable as a library or a CLI.

Both cover the full human (access password → `session` cookie) and agent (`X-API-Key`)
flows end to end.

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
| `POST /api/auth/login` | 10 failed attempts / 15 min per IP |
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
