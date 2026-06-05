# Chronicle of HackRitual

All notable changes are inscribed here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Bound — MVP-1 Step 03: Authentication (2026-03-06)

The gates are bound. A bearer presents their email; a six-digit code arrives by post;
the code is exchanged for a signed token sealed in a cookie. The session persists until
the bearer dissolves it or the seal expires.

- `backend/app/services/auth.py` — 6-digit code generation (`secrets.randbelow`), SHA-256 hashing, LoginCode CRUD with expiry and single-use enforcement, `get_or_create_user` on first login, JWT creation/decoding via `python-jose`, in-memory rate limiter (3/email, 10/IP per 15 min; 5 verify attempts)
- `backend/app/services/email.py` — async SMTP dispatch via `aiosmtplib`; console/dev mode when `SMTP_HOST` is `localhost`; HTML + plain text login code templates
- `backend/app/schemas/auth.py` — Pydantic models for all auth endpoints; simple regex email validation (per spec §12.5)
- `backend/app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` FastAPI dependencies
- `backend/app/routers/auth.py` — 5 endpoints: `POST /api/auth/request-code`, `POST /api/auth/verify-code`, `POST /api/auth/logout`, `POST /api/auth/refresh`, `GET /api/auth/me`
- `requirements.txt` — added `email-validator==2.2.0`
- `backend/tests/test_auth.py` — 36 new tests; **73/73 total tests passing**

---

### Bound — MVP-1 Step 02: Database Layer (2026-03-06)

The schema is inscribed. The SQLite stone is carved with 12 tables, all relationships
sealed with foreign keys, WAL mode lit for concurrent reads. The entity graph is complete:
users, sessions, login codes, participants, teams, agents, submissions, files, scores,
tasks, audit logs, and the event record itself.

- `backend/app/database.py` — SQLAlchemy engine with WAL mode, `busy_timeout=5000`, FK enforcement; `SessionLocal` factory; `check_db()` heartbeat probe
- `backend/app/models/` — 11 model files covering the full data model from specs §9: `User`, `LoginCode`, `Session`, `Participant`, `ParticipantMember`, `Agent`, `Submission`, `File`, `Score`, `Task`, `AuditLog`, `Event`
- `backend/app/models/__init__.py` — collects all models so Alembic autogenerate sees the full schema
- `backend/alembic/versions/4801ca88b7f6_initial_schema.py` — initial migration: all 12 tables, all indexes, all FK constraints
- `backend/alembic/env.py` — wired to `Base.metadata`; `render_as_batch=True` for SQLite-safe schema evolution
- `backend/app/utils/files.py` — `save_upload`, `get_upload_path`, `delete_upload`; SHA-256 integrity on every upload; stored at `<UPLOAD_DIR>/<event_id>/<participant_id>/<submission_id>/`
- `backend/app/main.py` — lifespan seeds the `Event` record from env vars and admin `User` rows from `ADMIN_SEED_EMAILS` on first invocation (idempotent)
- `backend/app/routers/health.py` — `GET /api/health` now reads real `event_state` from the `Event` table
- `backend/tests/test_database.py` — 23 new tests covering pragmas, all model CRUD, file utilities, seeding logic, health integration; **37/37 total tests passing**

---

### Bound — MVP-1 Step 01: Project Setup & Docker (2026-03-06)

The circle is drawn. The container skeleton stands. The health endpoint breathes.

- Repository directory structure: `backend/`, `frontend/`, `docker/`, `specs/`
- `backend/app/main.py` — FastAPI app factory with lifespan, CORS, static file serving
- `backend/app/config.py` — Pydantic `BaseSettings` for all 17 env vars; fail-fast validation
- `backend/app/utils/logging.py` — JSON structured logging to stdout; `LOG_LEVEL` configurable
- `backend/app/routers/health.py` — `GET /api/health` with DB ping and persistent storage heuristic
- `docker/Dockerfile` — multi-stage build (Node 20 Alpine → Python 3.11-slim); port 7860
- `docker/entrypoint.sh` — creates `/data` dirs, runs Alembic migrations, starts uvicorn
- `docker-compose.yml` — local dev with volume mounts for hot-reload
- `.env.example` — documented template for all environment variables
- `backend/requirements.txt` + `backend/requirements-dev.txt`
- `backend/alembic/` — migration scaffolding wired to `DB_PATH` env var
- `backend/tests/` — 14 tests covering config validation, health endpoint, JSON logging; **14/14 passing**

---

<!-- Future rituals will be inscribed above this line -->
