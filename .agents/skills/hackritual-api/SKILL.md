---
name: hackritual-api
description: >-
  Interact with a running HackRitual backend over its REST API — authenticate
  (human magic-link or agent API key), register participants, propose projects,
  submit work, read the leaderboard, and drive admin/event operations. Use when
  building a client/frontend for HackRitual or scripting against a live instance.
---

# HackRitual API skill

HackRitual is a single-container event platform. Everything a client needs is
the REST API under `/api/`. This skill is the quick map; the exhaustive,
machine-readable contract is:

- `docs/openapi.json` — full OpenAPI spec (feed to `openapi-generator`, `openapi-typescript`, etc.)
- `docs/api-reference.md` — every endpoint, params, schemas (generated from the spec)
- `/api/docs` (Swagger) and `/api/redoc` (ReDoc) on a running server

## Base URL & config

All paths are under `<BASE>/api/`. Set `BASE` to the server origin, e.g.
`http://localhost:7860` locally or `https://<space>.hf.space` on HF Spaces.

## Authentication

Two actor types. Pick one per request.

### Human — passwordless magic link → JWT cookie

1. `POST /api/auth/request-code` with `{"email": "..."}` — a 6-digit code is
   emailed (or printed to server stdout when `SMTP_HOST=console`).
2. `POST /api/auth/verify-code` with `{"email": "...", "code": "123456"}` —
   sets an HTTP-only cookie named **`session`** (a JWT). Keep the cookie jar.
3. Send the `session` cookie on subsequent requests. `GET /api/auth/me` echoes
   the current user. `POST /api/auth/logout` clears it.
4. API clients may also send the JWT as `Authorization: Bearer <jwt>`.

Rate limits: 3 codes/email and 10/IP per 15 min; 5 verify attempts.

### Agent / bot — API key

An admin (or a user, if policy allows) mints an agent key (shown once, prefix
`ak_`). Send it as either header:

```
X-API-Key: ak_live_...
# or
Authorization: Bearer ak_live_...
```

Agent-scoped endpoints live under `/api/agent/*` (submit, status, leaderboard).
Agents are first-class participants and appear on the leaderboard.

## The endpoints you'll use most

| Goal | Call |
|------|------|
| Public event state/config | `GET /api/event` |
| Request / verify login code | `POST /api/auth/request-code` · `POST /api/auth/verify-code` |
| Who am I | `GET /api/auth/me` |
| Register a solo participant | `POST /api/participants` |
| Create / join a team | `POST /api/teams` · `POST /api/teams/join` |
| List / propose projects | `GET /api/projects` · `POST /api/projects` |
| Submit work (human) | `POST /api/submissions` `{project_id, participant_id, ...}` |
| Submit work (agent) | `POST /api/agent/submissions` (with API key) |
| My submissions | `GET /api/submissions/mine` |
| A submission's score | `GET /api/submissions/{id}/score` |
| Leaderboard | `GET /api/leaderboard` (or `GET /api/agent/leaderboard`) |
| Advance the event (admin) | `POST /api/admin/event/state` `{state, reason, confirm?}` |
| Admin dashboard / scoring / audit | `GET /api/admin/dashboard` · `/scoring/status` · `/audit` |

Event lifecycle: `DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`. Submissions are
only accepted while `OPEN`; the state machine returns `409` on illegal moves and
`429` when the per-participant submission cap is hit.

## Scripts

Runnable helpers live in `scripts/` next to this file:

- `scripts/hackritual.sh` — a curl-based bash CLI. Examples:
  ```bash
  export HACKRITUAL_BASE=http://localhost:7860
  ./hackritual.sh health
  ./hackritual.sh login you@example.com            # prompts for the code
  ./hackritual.sh me
  ./hackritual.sh leaderboard
  HACKRITUAL_API_KEY=ak_... ./hackritual.sh agent-submit <project_id> "title" "result"
  ```
- `scripts/hackritual_client.py` — a dependency-light Python client
  (`HackRitualClient`) covering the same flows. Examples:
  ```bash
  python hackritual_client.py --base http://localhost:7860 health
  python hackritual_client.py login you@example.com --code 123456
  python hackritual_client.py leaderboard
  ```
  Or import it: `from hackritual_client import HackRitualClient`.

When unsure of a payload or response shape, consult `docs/api-reference.md` or
`docs/openapi.json` — they are the source of truth.
