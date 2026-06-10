# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code
in this repository.

**See [AGENTS.md](AGENTS.md) for the full guide.** It is the canonical agent
documentation — commands, architecture, key files, the event lifecycle and auth
flow, testing conventions, and the project's writing voice. Everything below is a
quick reference; AGENTS.md is the source of truth.

## Quick reference

```bash
make install-dev   # install all deps (uv sync --extra dev)
make serve         # dev server, hot-reload, port 7860
make migrate       # Alembic migrations (upgrade head)
make test          # full backend suite
make lint          # ruff check
make fmt           # ruff format

# In Docker (no local Python needed):
docker compose run --rm test   # full backend suite
docker compose run --rm sim    # the ritual simulator (full lifecycle, narrated)
```

- **Single container, single process, single SQLite file.** FastAPI backend serves
  the REST API and a Next.js static export. No Node.js runtime in production.
- Backend is the source of truth — see `backend/app/` (routers = HTTP, services =
  logic, models = ORM, schemas = Pydantic).
- Event lifecycle: `DRAFT → OPEN → FROZEN → FINAL → ARCHIVED`.
- Auth: admin-distributed access password (`POST /api/auth/login`) → JWT in HTTP-only `session` cookie. No email is ever sent.
- Tests: `pytest-asyncio`; never import app modules at module level in test files.
- Voice/tone in `docs/writing-style.md`.
