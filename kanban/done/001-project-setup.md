---
id: "001"
title: "Project Setup & Docker"
type: chore
status: done
estimate: "2d"
size: M
depends_on: []
blocks: ["002"]
spec: "specs/specs/01-project-setup-docker.md"
tags: [docker, infrastructure, fastapi]
tests_passing: 14
---

# Project Setup & Docker

Repository scaffolding, FastAPI skeleton, Docker image, health endpoint, and structured logging.

## Completed

- [x] Repository directory structure
- [x] `backend/app/main.py` — FastAPI skeleton, CORS, static files, lifespan
- [x] `backend/app/config.py` — Pydantic Settings with all env vars (fail-fast validation)
- [x] `docker/Dockerfile` — multi-stage (Node 20 + Python 3.11-slim)
- [x] `docker/entrypoint.sh` — mkdir, migrations, seed, uvicorn
- [x] `GET /api/health` — DB check + persistent storage check
- [x] Structured JSON logging to stdout, `LOG_LEVEL` env var
- [x] `docker-compose.yml` + `.env.example` for local dev

## Notes

- Port 7860 (HF Spaces default) used consistently across local dev and prod
- Frontend static dir warning is expected until Step 10 builds Next.js
- `docker build` not validated locally (no Docker daemon in devcontainer)
