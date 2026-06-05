# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands run from the repo root via `make`, or directly from `backend/` with `uv run`.

```bash
# Setup
make install-dev          # install all deps including dev/test tools

# Development
make serve                # start dev server with hot-reload on port 7860
make migrate              # run Alembic migrations (upgrade head)

# Testing
make test                 # run all tests
cd backend && uv run pytest -v                        # run all tests (verbose)
cd backend && uv run pytest tests/test_auth.py -v     # run a single test file
cd backend && uv run pytest -k "test_name" -v         # run a specific test by name

# Code quality
make lint                 # ruff check
make fmt                  # ruff format

# Diagnostics
make health               # check health of running server
make info                 # print current config (secrets masked)
```

The `hackritual` CLI is also available directly:
```bash
cd backend && uv run hackritual serve --reload
cd backend && uv run hackritual migrate
```

## Architecture

**Single container, single process, single SQLite file.** HackRitual is a FastAPI backend that also serves a Next.js static export. No Node.js runtime, no external DB, no sidecar processes in production.

### Key files

- `backend/app/main.py` — FastAPI factory (`create_app()`), lifespan (DB seeding), CORS, static mount
- `backend/app/config.py` — `Settings` (pydantic-settings); module-level singleton `settings`. Fails fast at import if required env vars are missing. Requires at least one of `ADMIN_SEED_EMAILS` or `ADMIN_SETUP_TOKEN`.
- `backend/app/database.py` — SQLAlchemy engine with WAL/FK/busy_timeout pragmas, `SessionLocal`, `get_db()` FastAPI dependency
- `backend/app/cli.py` — Typer CLI (`serve`, `migrate`, `health`, `info`)
- `backend/app/models/` — SQLAlchemy ORM models (all imported in `models/__init__.py` so Alembic sees them)
- `backend/app/routers/` — one module per domain (`health`, `auth`, `users`, `setup`, `participants`, ...)
- `backend/app/services/` — business logic with no HTTP concerns (`auth.py`, `email.py`, `participants.py`, `audit.py`)
- `backend/app/schemas/` — Pydantic request/response models
- `backend/app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` FastAPI dependencies
- `backend/alembic/` — migrations; `alembic.ini` is at `backend/alembic.ini`
- `backend/tests/conftest.py` — session-scoped fixtures that inject a temp SQLite DB and minimal env vars; no real `.env` needed for tests

### Auth flow

Passwordless magic-link via 6-digit codes. Code is generated, SHA-256 hashed, stored in DB, emailed via SMTP. On verification, a JWT is issued as an HTTP-only cookie (`session`). The middleware also accepts `Authorization: Bearer <token>` for API/agent access. In-memory rate limiting (3/email, 10/IP per 15 min; 5 verify attempts).

### Event lifecycle

`DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`. A single `Event` record is created at startup from env vars. Participant registration is only allowed in `DRAFT` or `OPEN` states.

### Storage

- SQLite at `DB_PATH` (default `/data/app.db`), WAL mode
- File uploads at `UPLOAD_DIR` (default `/data/uploads`)
- Health endpoint reports `persistent_storage: false` if `/data` is not a persistent mount — this is expected in dev

### Testing conventions

- Tests use `pytest-asyncio`; the `client` fixture is an async `httpx.AsyncClient` wired via `ASGITransport`
- The `_set_env` session fixture sets all required env vars before any app module is imported — never import app modules at module level in test files
- `pydantic-settings` env var overrides take precedence over constructor kwargs; session-scoped env is intentional

### SMTP / email in dev

Set `SMTP_HOST=localhost`, `127.0.0.1`, or `console` to activate console/dev mode — login codes are printed to stdout instead of sent via SMTP.

### Implementation status

Steps 01–05 are complete (110 tests passing). Steps 06–20 are pending. See `PROGRESS.md` for the full task breakdown and `specs/specs/` for the specifications for each step.
