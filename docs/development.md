# Local Development

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and pnpm (for the frontend)
- Docker (optional, for container testing — and the easiest way to run the suite)

## Backend

```bash
cd src/backend
uv sync --extra dev                 # create .venv, install all deps
cp ../.env.example .env             # edit values (JWT_SECRET, ADMIN_*, EVENT_*)
uv run hackritual migrate           # apply Alembic migrations
uv run hackritual serve --reload    # → http://localhost:7860
```

Or from the repo root via `make`: `make install-dev`, `make migrate`, `make serve`.

## Frontend

```bash
cd src/frontend
pnpm install
pnpm dev          # → http://localhost:3000, proxies /api/* to :7860
```

For production, the frontend is a **static export** (`pnpm build` → `out/`) that
FastAPI serves from the same container — no Node runtime in prod.

## Tests

Run the backend suite in Docker (no local Python needed) — this is what CI does:

```bash
docker compose run --rm test                          # full suite
docker compose run --rm test python -m pytest tests/test_event.py -v
```

Or locally: `make test` (`uv run pytest`). Lint/format: `make lint`, `make fmt`.

## The ritual simulator

A one-command end-to-end run — humans and an autonomous agent walk the whole
lifecycle (register → submit → score → leaderboard → export → notify):

```bash
docker compose run --rm sim          # narrated, self-contained
hackritual simulate                  # same, in your dev env
```

## Migrations

DB schema changes need an Alembic migration (tests use `create_all`, but
production runs `alembic upgrade head`):

```bash
cd src/backend
uv run alembic revision -m "add my column"     # then edit the generated file
uv run alembic upgrade head
```

Chain `down_revision` on the current head. Verify it applies on a fresh DB before
relying on it.

## Building the production image

```bash
docker build -f tools/image/docker/Dockerfile -t hackritual .
docker run -p 7860:7860 --env-file .env -v "$PWD/data:/data" hackritual
curl http://localhost:7860/api/health
```
