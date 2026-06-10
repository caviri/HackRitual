# Contributing to HackRitual

Thanks for helping forge the ritual. This guide gets you from clone to merged PR.

## Setup

See [docs/development.md](docs/development.md) for the full local setup. The short
version:

```bash
cd backend && uv sync --extra dev
docker compose run --rm test        # confirm the suite is green
```

The canonical agent/contributor reference is [AGENTS.md](AGENTS.md) — read it
first. It covers the architecture, commands, conventions, and the project's voice.

## Conventions

- **Backend** (`backend/app/`): routers handle HTTP, services hold business logic,
  models are SQLAlchemy ORM, schemas are Pydantic. Keep HTTP concerns out of
  services. New ORM models must be imported in `models/__init__.py`.
- **Style**: `make lint` (ruff check) and `make fmt` (ruff format) before pushing.
- **Voice**: docs, changelog entries, comments, and user-facing strings follow
  the ritual voice (see [docs/writing-style.md](docs/writing-style.md)) — code
  identifiers stay conventional.

## Adding an API endpoint

1. Add the route to the relevant router in `backend/app/routers/` (or a new one,
   registered in `app/main.py`). Give it a `tags=[...]` that exists in
   `app/docs.py`'s `OPENAPI_TAGS`.
2. Define request/response Pydantic schemas in `app/schemas/`.
3. Put logic in a service under `app/services/`.
4. Gate it appropriately — `require_admin` / `get_current_user` /
   `get_current_actor`, and `EventGuard`/`submission_rules` for state gating.
5. Add tests under `backend/tests/`. `tests/test_openapi.py` will fail if your
   operation is untagged or uses an undeclared tag.

## Database changes

Add an Alembic migration chained on the current head (see development.md). Tests
use `create_all`, but production runs `alembic upgrade head` — verify your
migration applies on a fresh DB.

## Testing requirements

- New behavior needs tests. Run the **full suite in Docker** before pushing:
  `docker compose run --rm test` (must stay green).
- Tests use `pytest-asyncio` with an async `httpx` client. Never import app
  modules at module top-level in test files — the env is injected first by
  `conftest.py`.
- For privacy: never store or log full IP addresses; metrics are aggregate-only.

## Pull requests

- Branch off `main`; keep PRs focused.
- Update `PROGRESS.md` and `CHANGELOG.md` when you complete a spec step.
- Regenerate `docs/openapi.json` if you changed the API surface.
- A green suite, clean lint, and updated docs are the definition of done.
