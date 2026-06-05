# 01 — Project Setup & Docker

**Milestone:** MVP-1
**Priority:** Critical (foundation for everything)
**Dependencies:** None
**Specs reference:** §4 (Deployment Requirements), §4.4 (Environment Variables)

---

## Overview

Set up the monorepo structure, Docker single-container build, environment configuration, and health endpoint. The container must run on Hugging Face Spaces Docker runtime and be operable with limited CPU/RAM.

---

## Tasks

### 1.1 Repository Structure

Create the following directory layout:

```
hackritual/
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py           # FastAPI app entry, lifespan, CORS
│   │   ├── config.py         # Pydantic Settings (env vars)
│   │   ├── database.py       # SQLite engine, session factory
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # API route modules
│   │   ├── services/         # Business logic
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── middleware/        # Auth, rate-limit middleware
│   │   └── utils/            # Helpers (email, hashing, etc.)
│   ├── alembic/              # DB migrations
│   ├── alembic.ini
│   ├── requirements.txt
│   └── tests/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/              # App Router pages
│   │   ├── components/       # React components
│   │   ├── lib/              # API client, utils
│   │   └── styles/
│   ├── package.json
│   └── next.config.js
├── docker/
│   ├── Dockerfile            # Multi-stage build
│   └── entrypoint.sh         # Startup script
├── specs/                    # This documentation
├── .env.example              # Documented env vars
├── docker-compose.yml        # Local dev convenience
└── README.md
```

### 1.2 FastAPI Application Skeleton

- Create `backend/app/main.py` with:
  - FastAPI app instance with lifespan handler
  - CORS middleware (configurable origins)
  - Static file serving for the Next.js build output
  - Health endpoint: `GET /api/health`
- Create `backend/app/config.py` using Pydantic `BaseSettings`:
  - Load all env vars listed in specs §4.4
  - Validate required vs optional values
  - Provide sensible defaults

### 1.3 Environment Variables

Implement configuration for all env vars from the specs:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_BASE_URL` | Yes | — | Public URL for callbacks/links |
| `SMTP_HOST` | Yes | — | SMTP server host |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | Yes | — | SMTP username |
| `SMTP_PASS` | Yes | — | SMTP password |
| `SMTP_FROM` | Yes | — | Sender email address |
| `DB_PATH` | No | `/data/app.db` | SQLite database path |
| `UPLOAD_DIR` | No | `/data/uploads` | File upload directory |
| `JWT_SECRET` | Yes | — | JWT signing key |
| `ADMIN_SEED_EMAILS` | No* | — | Comma-separated admin emails |
| `ADMIN_SETUP_TOKEN` | No* | — | One-time admin setup token |
| `GITHUB_EXPORT_REPO` | No | — | GitHub repo for export |
| `GITHUB_TOKEN` | No | — | GitHub PAT for export |
| `EVENT_ID` | Yes | — | Unique event identifier |
| `EVENT_TITLE` | Yes | — | Display title |
| `EVENT_TYPE` | No | `hackathon` | Event type label |
| `EVENT_START` | Yes | — | ISO 8601 start datetime |
| `EVENT_END` | Yes | — | ISO 8601 end datetime |

*At least one of `ADMIN_SEED_EMAILS` or `ADMIN_SETUP_TOKEN` is required.

### 1.4 Dockerfile (Multi-Stage)

Build a single container that serves both backend and frontend:

```dockerfile
# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/out ./static/
COPY docker/entrypoint.sh ./
RUN chmod +x entrypoint.sh
EXPOSE 7860
CMD ["./entrypoint.sh"]
```

Key considerations:
- HF Spaces uses port `7860` by default
- Final image should be as small as possible
- Use `python:3.11-slim` as base
- Next.js should be built as static export (`output: 'export'`)

### 1.5 Entrypoint Script

`docker/entrypoint.sh` must:
1. Create `/data` directory if not exists
2. Create `/data/uploads` directory if not exists
3. Run Alembic migrations (`alembic upgrade head`)
4. Seed admin users if `ADMIN_SEED_EMAILS` is set and users don't exist yet
5. Start uvicorn: `uvicorn backend.app.main:app --host 0.0.0.0 --port 7860`

### 1.6 Health Endpoint

`GET /api/health` — returns:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "event_id": "hackritual-2026-bern",
  "event_state": "DRAFT",
  "persistent_storage": true,
  "db_ok": true
}
```

- Check DB connectivity (simple query)
- Check if `/data` is a persistent mount (heuristic: write + read a marker file)
- If storage is ephemeral, set `persistent_storage: false` and log a warning

### 1.7 Logging

- Configure Python logging to stdout/stderr (container-native per specs §4.5)
- Use structured JSON logging format
- Log levels configurable via `LOG_LEVEL` env var (default: `INFO`)

### 1.8 Local Development Setup

- `docker-compose.yml` for local development:
  - Mount backend source for hot-reload
  - Mount frontend source
  - Map port 7860
  - Provide `.env.example` with documented defaults
- Backend dev: `uvicorn backend.app.main:app --reload`
- Frontend dev: `npm run dev` (Next.js dev server with API proxy)

---

## Acceptance Criteria

- [ ] `docker build` produces a working single container
- [ ] Container starts and `GET /api/health` returns 200
- [ ] All required env vars are validated at startup (fail fast if missing)
- [ ] Container runs successfully on HF Spaces Docker runtime (port 7860)
- [ ] Ephemeral mode detected and warned when `/data` is not persistent
- [ ] Frontend static build is served from the same container
- [ ] Local dev setup works with hot-reload for both backend and frontend

---

## Developer Notes

- Use `python-dotenv` for local development `.env` loading
- Consider `pydantic-settings` for env var validation — it integrates well with FastAPI
- For HF Spaces compatibility, ensure no privileged operations in Dockerfile
- The container should start in under 30 seconds on Spaces hardware
- Test with `docker run -p 7860:7860 --env-file .env hackritual` locally
