# AGENTS.md

Guidance for AI coding agents working in this repository. This is the canonical
agent guide; `CLAUDE.md` points here. Read it before making changes.

## What this is

HackRitual is a **portable, single-container** event platform for hackathons and
time-bounded collaborative invention. One Docker image, one process, one SQLite
file. The whole state of an event lives in that file; tear down the container and
the ritual is gone.

**Single container, single process, single SQLite file.** A FastAPI backend serves
both the REST API and a Next.js static export. No Node.js runtime, no external DB,
no sidecar processes in production. Deploy target is Hugging Face Spaces (Docker
runtime), port 7860.

## Repository layout

```
backend/      FastAPI app, the source of truth for all behavior
  app/        application package (see "Backend key files")
  alembic/    migrations  (alembic.ini lives at backend/alembic.ini)
  tests/      pytest suite
  pyproject.toml, uv.lock
frontend/     Next.js 14 (static export), pnpm, Tailwind, Playwright
  src/app/    route segments (admin, participants, teams, submissions, …)
  src/components, src/lib, src/styles
docs/         architecture, data-model, event-lifecycle, api, deployment, writing-style
docker/       Dockerfile and container assets
specs/        per-step specifications
PROGRESS.md   implementation status tracker (single source of truth for status)
RISKS.md      risk register
```

## Commands

Run from the repo root via `make`, or from `backend/` with `uv run`.

```bash
# Setup
make install-dev          # install all deps including dev/test tools (uv sync --extra dev)

# Development
make serve                # dev server, hot-reload, port 7860
make migrate              # Alembic migrations (upgrade head)

# Testing
make test                 # full backend suite
cd backend && uv run pytest -v                    # all tests, verbose
cd backend && uv run pytest tests/test_auth.py -v # one file
cd backend && uv run pytest -k "test_name" -v     # one test by name

# Code quality
make lint                 # ruff check
make fmt                  # ruff format

# Diagnostics
make health               # health of a running server
make info                 # current config, secrets masked
```

The `hackritual` CLI (Typer) is available after `uv sync`:

```bash
cd backend && uv run hackritual serve --reload
cd backend && uv run hackritual migrate      # also: health, info
```

### Tests & simulation in Docker

The compose file carries two profiled helper services so the suite and the
end-to-end simulator both run in a container (no local Python needed):

```bash
docker compose run --rm test    # full backend suite (uv image, repo mounted)
docker compose run --rm test python -m pytest tests/test_event.py -v
docker compose run --rm sim     # the Rite of Many Hands — full lifecycle sim
```

The **ritual simulator** (`backend/app/services/ritual_sim.py`, also
`hackritual simulate`) summons human + machine agents and drives one event
through every state over the real REST API — registration, team formation, the
state-machine wards, and the audit chronicle. It's both a living demo and an
end-to-end test (`tests/test_ritual_sim.py`). The phase coordinator (`PHASES`)
is data-driven; the phases already run the full arc — register, form teams,
propose projects, offer submissions (auto-scored), weigh the leaderboard, and
advance the ritual to ARCHIVED. New phases slot in by adding a method and a
`PHASES` entry.

### Frontend

```bash
cd frontend && pnpm install
pnpm dev                  # next dev on port 3000
pnpm build                # static export (served by FastAPI in production)
pnpm lint                 # next lint
pnpm test:screenshots     # Playwright
```

Use **pnpm** (pinned via `packageManager`), not npm or yarn. Node 20+.

## Backend key files

- `backend/app/main.py` — FastAPI factory (`create_app()`), lifespan (DB seeding), CORS, static mount
- `backend/app/config.py` — `Settings` (pydantic-settings); module-level singleton `settings`. Fails fast at import if required env vars are missing. Requires `ADMIN_SEED_EMAILS` and `ADMIN_PASSWORD`.
- `backend/app/database.py` — SQLAlchemy engine with WAL/FK/busy_timeout pragmas, `SessionLocal`, `get_db()` dependency
- `backend/app/cli.py` — Typer CLI (`serve`, `migrate`, `health`, `info`)
- `backend/app/models/` — SQLAlchemy ORM models (all imported in `models/__init__.py` so Alembic sees them)
- `backend/app/routers/` — one module per domain (`health`, `auth`, `users`, `applications`, `participants`, …)
- `backend/app/services/` — business logic with no HTTP concerns (`auth.py`, `passwords.py`, `applications.py`, `participants.py`, `audit.py`)
- `backend/app/schemas/` — Pydantic request/response models
- `backend/app/middleware/auth.py` — `get_current_user`, `require_admin`, `require_role` dependencies
- `backend/tests/conftest.py` — session-scoped fixtures that inject a temp SQLite DB and minimal env vars; no real `.env` needed for tests

Keep HTTP concerns in routers, business logic in services. Add new ORM models to
`models/__init__.py` or Alembic will not see them.

## Domain model

### Event lifecycle

`DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`. A single `Event` record is created at
startup from env vars. Participant registration is only allowed in `DRAFT` or `OPEN`.
See `docs/event-lifecycle.md` for the full state machine.

### Auth flow

Admin-distributed access passwords. Each user holds one generated password
(`word-word-NNNN`, see `services/passwords.py`) stored in plaintext on the
unique `users.access_password` column — the password alone identifies the user
at `POST /api/auth/login`. On success a JWT is issued as an HTTP-only cookie
(`session`). The middleware also accepts `Authorization: Bearer <token>` for
API/agent access. Failed logins are throttled in memory: 10 per IP per 15 min
(load-bearing — it is what makes the password entropy sufficient).

Joining: visitors petition at `POST /api/applications` (or arrive via the admin
CSV import). Approval in `/admin/applications/` mints the User + password; the
admin delivers it by hand (copy/mailto buttons). The platform sends no email.
The first `ADMIN_SEED_EMAILS` address gets its password re-synced from
`ADMIN_PASSWORD` on every boot — the lockout recovery path.

### Storage

- SQLite at `DB_PATH` (default `/data/app.db`), WAL mode
- File uploads at `UPLOAD_DIR` (default `/data/uploads`)
- The health endpoint reports `persistent_storage: false` if `/data` is not a
  persistent mount — expected in dev

## Testing conventions

- Tests use `pytest-asyncio`; the `client` fixture is an async `httpx.AsyncClient`
  wired via `ASGITransport`.
- The `_set_env` session fixture sets all required env vars **before any app module
  is imported** — never import app modules at module level in test files. Import
  them inside the test function or fixture.
- `pydantic-settings` env var overrides take precedence over constructor kwargs;
  session-scoped env is intentional.
- Run `make lint` and `make fmt` before considering a change done. Add or update
  tests for behavioral changes.

## Writing style

This project has a deliberate voice: hacker culture meets ritual ceremony — "a
wizard who also reads RFCs." Earnest, technically precise, dry, never corporate; no
emoji, no exclamation marks, no marketing speak. The ritual metaphor (summon,
dispel, bind, the gathered) must always still make technical sense. This applies to
docs, changelog entries, comments, and user-facing strings — **not** to code
identifiers, which stay conventional and descriptive. See `docs/writing-style.md`.

## Status

See `PROGRESS.md` for the authoritative task breakdown and `specs/` for per-step
specifications. **MVP-1 and MVP-2 backends are complete** (Steps 01–08, 11–15;
**258 tests passing**). Steps 09/10 are backend-complete with UI remainders
(admin console wiring; submission-create form + `AuthGuard`). The Next.js app
builds as a static export. MVP-3 (16, WASM scoring) and MVP-4 (17, GitHub export)
are backend-complete; cross-cutting Steps 18–20 are done (**284 tests passing**;
`docs/openapi.json` snapshot committed). **All 20 spec steps are addressed.** The
submission-create form (`/submissions/new`) and the admin `AuthGuard` are now wired,
and the admin state machine uses the real `/api/admin/event/state` endpoint. What
remains is deferred frontend polish (admin dashboard/scoring/audit views still use
client-side aggregation rather than the dedicated `/api/admin/*` roll-ups; WASM
client preview) and a template Rust scorer. Update `PROGRESS.md` and `CHANGELOG.md`
when you complete a step.

DB schema changes need an Alembic migration (`backend/alembic/versions/`, chained
on the current head) — tests use `create_all`, but production runs `alembic
upgrade head`. Verify a new migration applies on a fresh DB before relying on it.

The frontend builds in Docker with `MSYS_NO_PATHCONV=1 docker run --rm -v
"$PWD/src/frontend":/app -w /app node:20-alpine sh -c "corepack enable && corepack
prepare pnpm@9.12.3 --activate && pnpm install --frozen-lockfile && pnpm build"`
(the `MSYS_NO_PATHCONV` prefix matters on Windows/Git Bash — see memory).

The `corepack prepare pnpm@9.12.3 --activate` step is **required**: bare `corepack
enable` resolves to the latest pnpm (11.x), which needs Node 22 and dies on
`node:20-alpine` with `ERR_UNKNOWN_BUILTIN_MODULE: node:sqlite`. Pin to the
`packageManager` version (pnpm 9.12.3) before installing. This applies to the
production image too — `tools/image/docker/Dockerfile` runs the same `corepack
prepare … --activate` in its frontend stage. On PowerShell, drop the
`MSYS_NO_PATHCONV` prefix and use a literal mount path (`-v
"C:\path\to\src\frontend:/app"`); `${PWD}` does not expand reliably there.

Full production image (frontend + backend, the HF target):
`docker build -f tools/image/docker/Dockerfile -t hackritual .` (context = repo
root). HF Spaces require the Dockerfile at the repo root, so the sync workflow
(`.github/workflows/sync-to-hf.yml`) copies it there before pushing.
