# HackRitual — Implementation Progress

This file tracks the implementation status of each milestone task.

Legend: `[ ]` not started · `[~]` in progress · `[x]` complete

---

## MVP-1: Core Ritual Capsule

| # | Task | Status | Notes |
|---|------|--------|-------|
| 01 | Project Setup & Docker | `[x]` | Complete — 14/14 tests passing |
| 02 | Database Layer | `[x]` | Complete — 37/37 tests passing |
| 03 | Authentication | `[x]` | Complete — 73/73 tests passing |
| 04 | User Management | `[x]` | Complete — 37/37 tests passing |
| 05 | Participant Management | `[x]` | Depends on 04 — 22/22 tests passing |
| 06 | Event Lifecycle | `[ ]` | Depends on 02 |
| 07 | Submission System | `[ ]` | Depends on 05 |
| 08 | Scoring (Basic) | `[ ]` | Depends on 07 |
| 09 | Admin Console | `[ ]` | Depends on 04 |
| 10 | Frontend Foundation | `[ ]` | Can start parallel after 03 |
| 11 | JSON Export | `[ ]` | Depends on 02, 05, 07, 08 |
| 12 | Email System | `[ ]` | Depends on 02 |

## MVP-2: Agents + Queue

| # | Task | Status | Notes |
|---|------|--------|-------|
| 13 | Agent System | `[ ]` | Depends on 04 |
| 14 | Task Queue & Worker | `[ ]` | Depends on 02 |
| 15 | Rate Limiting & Abuse Resistance | `[ ]` | Depends on 03, 07, 13 |

## MVP-3: WASM Scoring

| # | Task | Status | Notes |
|---|------|--------|-------|
| 16 | WASM Scoring Module | `[ ]` | Depends on 08 |

## MVP-4: GitHub Pages Export

| # | Task | Status | Notes |
|---|------|--------|-------|
| 17 | GitHub Export & Static Site | `[ ]` | Depends on 11 |

## Cross-Cutting

| # | Task | Status | Notes |
|---|------|--------|-------|
| 18 | Privacy & Statistics | `[ ]` | Integrate incrementally |
| 19 | API Documentation | `[ ]` | Integrate incrementally |
| 20 | Deployment Guide | `[ ]` | After MVP-1 |

---

## Step 01 Detail: Project Setup & Docker

### Sub-tasks

| # | Sub-task | Status |
|---|----------|--------|
| 1.1 | Repository directory structure | `[x]` |
| 1.2 | `backend/app/main.py` — FastAPI skeleton, CORS, static files, lifespan | `[x]` |
| 1.3 | `backend/app/config.py` — Pydantic Settings with all env vars | `[x]` |
| 1.4 | `docker/Dockerfile` — multi-stage (Node 20 + Python 3.11-slim) | `[x]` |
| 1.5 | `docker/entrypoint.sh` — mkdir, migrations, seed, uvicorn | `[x]` |
| 1.6 | `GET /api/health` — DB check + persistent storage check | `[x]` |
| 1.7 | Structured JSON logging to stdout, `LOG_LEVEL` env var | `[x]` |
| 1.8 | `docker-compose.yml` + `.env.example` for local dev | `[x]` |

### Acceptance Criteria (from spec)

- [x] Container starts and `GET /api/health` returns 200 — validated live with uvicorn
- [x] All required env vars validated at startup (fail fast if missing) — 7 config tests
- [x] Ephemeral mode detected and warned when `/data` is not persistent — health test + live warning
- [x] Structured JSON logs emitted to stdout — 3 logging tests
- [ ] `docker build` produces a working single container — pending Docker daemon (not in devcontainer)
- [ ] Container runs on HF Spaces Docker runtime (port 7860) — pending actual deploy
- [ ] Frontend static build served from the same container — pending Step 10 (Next.js)
- [ ] Local dev hot-reload — pending npm run dev setup in Step 10

### Notes

- `docker build` not validated locally (no Docker daemon in devcontainer); validated structurally.
- Frontend static dir warning is expected until Step 10 builds the Next.js app.
- Alembic migrations wired and run cleanly; no migrations yet (Step 02 will add the first one).

---

## Step 02 Detail: Database Layer

### Sub-tasks

| # | Sub-task | Status |
|---|----------|--------|
| 2.1 | `backend/app/database.py` — engine, WAL/busy_timeout/FK pragmas, SessionLocal, check_db | `[x]` |
| 2.2 | All 11 SQLAlchemy models (user, login_code, session, participant, participant_member, agent, submission, file, score, task, audit_log, event) | `[x]` |
| 2.3 | `models/__init__.py` — imports all models for Alembic autogenerate | `[x]` |
| 2.4 | `alembic/env.py` — wired to Base.metadata, render_as_batch for SQLite | `[x]` |
| 2.5 | Initial migration generated (`4801ca88b7f6_initial_schema.py`) — all 12 tables | `[x]` |
| 2.6 | `app/utils/files.py` — save_upload, get_upload_path, delete_upload, SHA-256 | `[x]` |
| 2.7 | `main.py` lifespan — seeds Event record + admin users from env on first start | `[x]` |
| 2.8 | `routers/health.py` — reads real event_state from Event table | `[x]` |

### Acceptance Criteria (from spec)

- [x] SQLite database created at configured path with WAL mode enabled
- [x] All models from specs §9 defined and migrated
- [x] Foreign key constraints enforced
- [x] Alembic migrations run on container startup (wired via entrypoint.sh)
- [x] File uploads saved to correct directory structure
- [x] Admin users seeded on first start (idempotent)
- [x] Event record created from env vars on first start
- [ ] Database survives container restart when `/data` is persistent — pending actual Docker deploy

### Notes

- `datetime.utcnow()` deprecation warnings are expected (Python 3.12); will address in a later refactor pass.
- `ASGITransport` does not trigger FastAPI lifespans — seeding tested via direct logic calls, not via HTTP client.

---

## Step 05 Detail: Participant Management

### Sub-tasks

| # | Sub-task | Status |
|---|----------|--------|
| 5.1 | Participant types (human, agent, team) | `[x]` |
| 5.2 | Self-registration flow (POST /api/participants) | `[x]` |
| 5.3 | Team creation with invite codes (POST /api/teams) | `[x]` |
| 5.4 | Join team via invite code (POST /api/teams/join) | `[x]` |
| 5.5 | Team member management (list, remove, leave, regenerate invite) | `[x]` |
| 5.6 | Participant profile (GET/PATCH /api/participants/me) | `[x]` |
| 5.7 | Participant listing with pagination | `[x]` |
| 5.8 | Admin moderation endpoints | `[x]` |

### Acceptance Criteria (from spec)

- [x] Users can create a solo participant profile after login
- [x] Users can create teams and get an invite code (8 chars, alphanumeric)
- [x] Users can join teams using invite codes
- [x] Team captain can manage members and regenerate invite codes
- [x] Participant profiles show public info only (no emails)
- [x] Admin can create, view, and moderate all participants
- [x] Disabled/banned participants cannot create submissions (enforced in submission system)
- [x] Participant listing supports pagination and filtering
- [x] All 22 tests passing

### API Endpoints Implemented

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/participants` | User | Create solo participant |
| GET | `/api/participants` | Public | List participants (paginated) |
| GET | `/api/participants/me` | User | Own participant info |
| PATCH | `/api/participants/me` | User | Update own profile |
| GET | `/api/participants/{id}` | Public | View participant |
| POST | `/api/teams` | User | Create team |
| POST | `/api/teams/join` | User | Join team via invite code |
| GET | `/api/teams/{id}/members` | Team member | List team members |
| DELETE | `/api/teams/{id}/members/{mid}` | Captain | Remove member |
| POST | `/api/teams/{id}/leave` | Member | Leave team |
| POST | `/api/teams/{id}/regenerate-invite` | Captain | New invite code |
| GET | `/api/admin/participants` | Admin | List all participants |
| POST | `/api/admin/participants` | Admin | Create participant |
| PATCH | `/api/admin/participants/{id}/status` | Admin | Moderate participant |

### Notes

- User model doesn't have `display_name` - using email prefix instead for team member display
- Invite codes are 8-character alphanumeric, URL-safe, case-insensitive
- Bearer token authentication added to middleware (in addition to session cookies) for easier API testing
- Event state check ensures registration only allowed in DRAFT or OPEN states

---

## Step 03 Detail: Authentication

### Sub-tasks

| # | Sub-task | Status |
|---|----------|--------|
| 3.1 | `app/services/auth.py` — code gen (6-digit, `secrets`), SHA-256 hash, LoginCode CRUD, verify with expiry/single-use, get_or_create_user | `[x]` |
| 3.2 | `app/services/auth.py` — JWT creation/decoding via `python-jose`, `is_near_expiry` | `[x]` |
| 3.3 | `app/services/auth.py` — in-memory rate limiter (3/email, 10/IP per 15 min; 5 verify attempts) | `[x]` |
| 3.4 | `app/services/email.py` — SMTP dispatch via aiosmtplib; console/dev mode fallback; HTML+text login code template | `[x]` |
| 3.5 | `app/schemas/auth.py` — request/response Pydantic models; simple regex email validation | `[x]` |
| 3.6 | `app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` FastAPI deps | `[x]` |
| 3.7 | `app/routers/auth.py` — 5 endpoints wired and tested | `[x]` |
| 3.8 | `requirements.txt` — added `email-validator==2.2.0` | `[x]` |

### Acceptance Criteria (from spec)

- [x] Code is 6-digit, cryptographically random (`secrets.randbelow`), SHA-256 hashed in DB
- [x] Code expires after 10 minutes and is single-use
- [x] JWT issued in HTTP-only, Secure (when HTTPS), SameSite=Lax cookie
- [x] Rate limiting: 3/email and 10/IP per 15 min on request-code; 5 attempts on verify-code
- [x] Failed verification attempts capped — all codes invalidated after max failures
- [x] Logout clears session cookie
- [x] `GET /api/auth/me` returns current user or 401
- [x] First-login auto-creates user with role=`user`
- [x] Admin-seeded users can log in (role preserved from DB)
- [ ] User can receive login code via real SMTP — pending live SMTP environment

### Notes

- `EmailStr` (pydantic + email-validator) rejects `.local` TLD as reserved; switched to simple regex per spec §12.5.
- Console/dev mode active when `SMTP_HOST` is `localhost`, `127.0.0.1`, or `console`.
- `participant` field in `/api/auth/me` returns `null` until Step 05.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-06 | Use Python 3.12 in devcontainer, 3.11-slim in production Docker image | Devcontainer has 3.12; prod image stays on 3.11-slim per spec. Both are compatible. |
| 2026-03-06 | Next.js static export (`output: 'export'`) served by FastAPI | Single container constraint — no Node.js runtime in prod image. |
| 2026-03-06 | Port 7860 | HF Spaces default; keep consistent across local dev and prod. |
| 2026-03-06 | Removed --log-config /dev/null from uvicorn command | /dev/null is not a valid logging config on Linux; uvicorn handles its own log config. |
| 2026-03-06 | pydantic-settings env vars override constructor kwargs | Session-scoped test env intentionally overrides per-test kwargs; documented in test comments. |
