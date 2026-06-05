# Architecture

## Overview

HackRitual runs as a **single Docker container** exposing one HTTP endpoint that serves both the REST API and the Next.js frontend (as a static build). There are no sidecars, no external databases, and no message brokers — everything is self-contained.

---

## Container Layout

```
┌─────────────────────────────────────────────────────────┐
│                   Docker Container                       │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │              uvicorn  (port 7860)                │    │
│  │                                                  │    │
│  │  ┌────────────────┐   ┌───────────────────────┐ │    │
│  │  │  FastAPI app   │   │  Static file mount    │ │    │
│  │  │  /api/*        │   │  / (Next.js export)   │ │    │
│  │  └───────┬────────┘   └───────────────────────┘ │    │
│  │          │                                       │    │
│  │  ┌───────▼────────┐   ┌───────────────────────┐ │    │
│  │  │  Routers       │   │  Background tasks     │ │    │
│  │  │  /api/health   │   │  (email, scoring)     │ │    │
│  │  │  /api/auth     │   │  (MVP-2: task queue)  │ │    │
│  │  │  /api/events   │   └───────────────────────┘ │    │
│  │  │  /api/...      │                              │    │
│  │  └───────┬────────┘                              │    │
│  │          │                                       │    │
│  │  ┌───────▼────────┐                              │    │
│  │  │  SQLAlchemy    │                              │    │
│  │  │  (sync + WAL)  │                              │    │
│  │  └───────┬────────┘                              │    │
│  └──────────┼──────────────────────────────────────┘    │
│             │                                            │
│  ┌──────────▼──────────────────────────────────────┐    │
│  │  /data  (persistent volume or ephemeral tmpfs)   │    │
│  │    app.db         ← SQLite WAL                   │    │
│  │    uploads/       ← uploaded files               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Request Flow

### Human participant — login + submission

```
Browser
  │
  ├─ GET  /            → Next.js static SPA (HTML/JS/CSS)
  │
  ├─ POST /api/auth/request-code   → SMTP → user's email
  ├─ POST /api/auth/verify-code    → JWT cookie issued
  │
  ├─ POST /api/submissions         → submission created
  │                                  → scoring task queued
  └─ GET  /api/leaderboard         → official scores returned
```

### Agent (bot) — API key submission

```
Agent
  │
  ├─ POST /api/submissions   (Authorization: Bearer <api_key>)
  │        → validated, submission created, task queued
  └─ GET  /api/submissions/{id}/status
```

---

## Backend Directory Structure

```
backend/
├── app/
│   ├── main.py           ← FastAPI factory, lifespan, CORS, static mount
│   ├── config.py         ← Pydantic Settings (all env vars, fail-fast)
│   ├── database.py       ← SQLite engine + session factory (Step 02)
│   ├── models/           ← SQLAlchemy ORM models (Step 02)
│   ├── routers/          ← Route modules (one per domain)
│   │   ├── health.py     ← GET /api/health  ✓ (Step 01)
│   │   ├── auth.py       ← login, logout    (Step 03)
│   │   ├── users.py      ← user management  (Step 04)
│   │   ├── participants.py                  (Step 05)
│   │   ├── events.py     ← lifecycle        (Step 06)
│   │   ├── submissions.py                   (Step 07)
│   │   ├── scores.py                        (Step 08)
│   │   └── admin.py                         (Step 09)
│   ├── services/         ← Business logic (no HTTP concerns)
│   ├── schemas/          ← Pydantic request/response models
│   ├── middleware/       ← Auth, rate-limit middleware
│   └── utils/
│       ├── logging.py    ← JSON structured logging  ✓ (Step 01)
│       ├── email.py      ← SMTP helpers              (Step 12)
│       └── hashing.py    ← bcrypt, token utils       (Step 03)
├── alembic/              ← DB migrations (wired to DB_PATH)
├── tests/                ← pytest suite
├── requirements.txt
└── requirements-dev.txt
```

---

## Multi-Stage Docker Build

```
┌─────────────────────────┐
│  Stage 1: frontend-build │
│  node:20-alpine          │
│                          │
│  npm ci                  │
│  npm run build           │  ← Next.js static export → /out
└────────────┬────────────┘
             │ COPY --from=frontend-build /app/frontend/out ./static/
┌────────────▼────────────┐
│  Stage 2: production     │
│  python:3.11-slim        │
│                          │
│  pip install -r req.txt  │
│  COPY backend/           │
│  COPY static/            │
│  EXPOSE 7860             │
│  CMD entrypoint.sh       │
└─────────────────────────┘
```

---

## Persistence Model

```
  Persistent storage?
          │
    ┌─────┴─────┐
   YES          NO
    │            │
  /data        /data
  mounted      on ephemeral tmpfs
  (HF Spaces   ├── health reports persistent_storage: false
   volume or   ├── startup WARNING logged
   bind mount) └── export before shutdown!
    │
  app.db       ← SQLite WAL, busy_timeout=5000ms
  uploads/     ← files stored by path, not in DB
```

---

## Security Boundaries

```
      UNTRUSTED                    TRUSTED
  ┌──────────────┐           ┌──────────────────┐
  │   Browser    │           │  FastAPI backend  │
  │              │           │                  │
  │  Client WASM │  HTTP(S)  │  Server scoring  │
  │  (preview    ├──────────►│  (authoritative) │
  │   only)      │           │                  │
  │              │           │  SQLite DB       │
  └──────────────┘           │  File storage    │
                             └──────────────────┘
  Client score = UX preview only.
  Official score = server-side only.
  Leaderboard reads only from DB scores table.
```
