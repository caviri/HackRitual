# 20 — Deployment Guide & Documentation

**Milestone:** Cross-cutting (finalize after MVP-1 is functional)
**Priority:** Medium
**Dependencies:** [01-project-setup-docker](01-project-setup-docker.md)
**Specs reference:** §4 (Deployment Requirements), §10.1 (Deployer Flow)

---

## Overview

Comprehensive documentation for deployers, admins, and contributors. Covers deployment on Hugging Face Spaces, local Docker, configuration reference, troubleshooting, and contributor guidelines.

---

## Tasks

### 20.1 README.md (Root)

The project README should contain:

```markdown
# HackRitual

> An easy-to-summon platform for ritualised collaborative invention.
> Let's gather and forge the unknown.

## What is HackRitual?

A portable, single-container platform for hackathons, challenges, study-a-thons,
and similar time-bounded gatherings. Deploy it, run your event, export the results,
and shut it down.

## Quick Start

### Docker (local)
docker build -t hackritual .
docker run -p 7860:7860 --env-file .env -v hackritual-data:/data hackritual

### Hugging Face Spaces
1. Create a new Space (Docker SDK)
2. Set environment variables (see Configuration)
3. Enable persistent storage
4. Deploy

## Configuration
See [docs/configuration.md](docs/configuration.md) for full env var reference.

## Architecture
See [docs/architecture.md](docs/architecture.md) for technical overview.

## API
Interactive API docs available at `/api/docs` (Swagger UI).

## License
[TBD]
```

### 20.2 Configuration Reference

Create `docs/configuration.md`:

#### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `APP_BASE_URL` | Public URL of the instance | `https://myevent.hf.space` |
| `JWT_SECRET` | Secret key for JWT signing (min 32 chars) | `$(openssl rand -hex 32)` |
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | `noreply@example.com` |
| `SMTP_PASS` | SMTP password or app password | `xxxx-xxxx-xxxx-xxxx` |
| `SMTP_FROM` | Sender email address | `noreply@example.com` |
| `EVENT_ID` | Unique event identifier (no spaces) | `hackritual-bern-2026` |
| `EVENT_TITLE` | Display title | `HackRitual Bern 2026` |
| `EVENT_START` | ISO 8601 start datetime | `2026-03-01T09:00:00+01:00` |
| `EVENT_END` | ISO 8601 end datetime | `2026-03-02T17:00:00+01:00` |

#### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `/data/app.db` | SQLite database path |
| `UPLOAD_DIR` | `/data/uploads` | File upload directory |
| `EVENT_TYPE` | `hackathon` | Event type label |
| `ADMIN_SEED_EMAILS` | — | Comma-separated admin emails |
| `ADMIN_SETUP_TOKEN` | — | One-time admin setup token |
| `GITHUB_EXPORT_REPO` | — | GitHub repo for export (e.g., `org/repo`) |
| `GITHUB_TOKEN` | — | GitHub PAT for export push |
| `GITHUB_EXPORT_BRANCH` | `gh-pages` | Target branch for export |
| `LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `AUTO_TRANSITIONS` | `false` | Auto-transition states at start/end times |
| `WASM_TIME_LIMIT_MS` | `5000` | WASM scorer time limit |
| `WASM_MEMORY_LIMIT_MB` | `64` | WASM scorer memory limit |

### 20.3 Hugging Face Spaces Deployment Guide

Create `docs/hf-spaces-deployment.md`:

```markdown
# Deploying HackRitual on Hugging Face Spaces

## Prerequisites
- A Hugging Face account
- SMTP credentials for email delivery

## Step-by-Step

### 1. Create a New Space
- Go to huggingface.co/new-space
- Select "Docker" as the SDK
- Choose visibility (public or private)

### 2. Configure the Space

#### Dockerfile
The repo's Dockerfile is designed for Spaces. No changes needed.

#### Environment Variables
Go to Space Settings → Variables and Secrets.
Add all required variables (see Configuration Reference).

**Important:** Add sensitive values (JWT_SECRET, SMTP_PASS, GITHUB_TOKEN) as **Secrets**, not Variables.

### 3. Enable Persistent Storage
- Go to Space Settings → Persistent Storage
- Enable it (minimum size recommended)
- This mounts at `/data` — required for data to survive restarts

### 4. Deploy
- Push code to the Space repo, or connect your GitHub repo
- Space will build and deploy automatically

### 5. Verify
- Visit your Space URL
- Check `/api/health` returns `{"status": "ok"}`
- Log in with an admin seed email

### 6. Run Your Event
- Open Admin Console
- Set event state to OPEN
- Share the URL with participants

### Troubleshooting

**Container keeps restarting:**
- Check logs in the Space "Logs" tab
- Common cause: missing required env vars

**Emails not sending:**
- Verify SMTP credentials
- Check if SMTP port is reachable from Spaces
- Use port 587 (STARTTLS) — port 465 may be blocked

**Data lost after restart:**
- Ensure persistent storage is enabled
- Verify DB_PATH is set to `/data/app.db`

**Health endpoint shows persistent_storage: false:**
- Persistent storage may not be mounted yet
- Wait for Space to fully initialize
```

### 20.4 Local Development Guide

Create `docs/development.md`:

```markdown
# Local Development Setup

## Prerequisites
- Python 3.11+
- Node.js 20+
- Docker (optional, for container testing)

## Backend Setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # Edit with your values

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload --port 7860

## Frontend Setup
cd frontend
npm install
npm run dev  # Starts on port 3000 with API proxy to 7860

## Docker (full container)
docker build -t hackritual .
docker run -p 7860:7860 --env-file .env -v hackritual-data:/data hackritual

## Testing
cd backend && pytest
cd frontend && npm test

## Email Testing
# Use Mailpit for local SMTP testing
docker run -p 1025:1025 -p 8025:8025 axllent/mailpit
# Set SMTP_HOST=localhost SMTP_PORT=1025 in .env
# View emails at http://localhost:8025
```

### 20.5 Architecture Documentation

Create `docs/architecture.md`:

```markdown
# Architecture Overview

## Single-Container Design

┌─────────────────────────────────────────┐
│              Docker Container           │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │     FastAPI Application           │  │
│  │  ┌──────────┐  ┌──────────────┐   │  │
│  │  │ API      │  │ Static Files │   │  │
│  │  │ Routes   │  │ (Next.js)    │   │  │
│  │  └──────────┘  └──────────────┘   │  │
│  │  ┌──────────┐  ┌──────────────┐   │  │
│  │  │ Worker   │  │ WASM Runtime │   │  │
│  │  │ Loop     │  │ (wasmtime)   │   │  │
│  │  └──────────┘  └──────────────┘   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  ┌─────────────┐  ┌─────────────────┐   │
│  │ SQLite DB   │  │ File Storage    │   │
│  │ /data/app.db│  │ /data/uploads/  │   │
│  └─────────────┘  └─────────────────┘   │
└─────────────────────────────────────────┘

## Data Flow

1. User → HTTPS → FastAPI → JWT validation → Route handler
2. Route handler → SQLAlchemy → SQLite (WAL mode)
3. Submissions → File storage + DB metadata
4. Scoring → Task queue → Worker → WASM/Python scorer → Score record
5. Export → JSON generation → ZIP → Download or GitHub push

## Key Design Decisions

- **SQLite with WAL**: Single-process writes, concurrent reads
- **Task queue in SQLite**: No external message broker needed
- **Static Next.js export**: No SSR, served as static files from FastAPI
- **JWT in HTTP-only cookies**: Secure, stateless sessions
- **WASM scoring**: Deterministic, sandboxed, portable
```

### 20.6 Admin Guide

Create `docs/admin-guide.md`:

Covers the admin workflow from specs §10.2:
- First login and admin console tour
- Event preparation checklist
- Opening the event
- Monitoring during the event
- Handling incidents (disabling participants, revoking keys)
- Freezing and finalizing
- Exporting and archiving
- Shutting down the instance

### 20.7 Agent/Bot Integration Guide

Create `docs/agent-guide.md`:

```markdown
# Agent/Bot Integration Guide

## Getting Started

1. Get an API key from the event admin
2. All requests use Bearer token auth:
   Authorization: Bearer hr_your_api_key_here

## Submit
POST /api/agent/submissions
Content-Type: application/json
Authorization: Bearer hr_...

{
  "title": "Run #42",
  "payload_json": {
    "predictions": [0.95, 0.87, 0.92]
  }
}

## Check Score
GET /api/agent/submissions/{id}
Authorization: Bearer hr_...

## View Leaderboard
GET /api/agent/leaderboard
Authorization: Bearer hr_...

## Rate Limits
- 20 submissions per hour
- 60 API requests per minute
- Check X-RateLimit-Remaining header

## Example (Python)
import requests

API_URL = "https://myevent.hf.space/api/agent"
API_KEY = "hr_your_key_here"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Submit
resp = requests.post(f"{API_URL}/submissions", json={...}, headers=headers)
submission_id = resp.json()["id"]

# Poll for score
resp = requests.get(f"{API_URL}/submissions/{submission_id}", headers=headers)
print(resp.json()["score"])
```

### 20.8 Contributing Guide

Create `CONTRIBUTING.md`:

- How to set up the development environment
- Code style and conventions
- Branch naming and PR process
- How to add a new API endpoint
- How to add a new admin console page
- Testing requirements

### 20.9 .env.example

Create a well-documented `.env.example`:

```bash
# ===========================================
# HackRitual Configuration
# ===========================================

# --- Required ---
APP_BASE_URL=http://localhost:7860
JWT_SECRET=change-me-to-a-random-string-at-least-32-chars

# --- SMTP (required for login) ---
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASS=
SMTP_FROM=noreply@hackritual.local

# --- Event ---
EVENT_ID=hackritual-local-dev
EVENT_TITLE=Local Dev Event
EVENT_START=2026-03-01T09:00:00Z
EVENT_END=2026-03-02T17:00:00Z

# --- Admin ---
ADMIN_SEED_EMAILS=admin@example.com

# --- Storage ---
DB_PATH=./data/app.db
UPLOAD_DIR=./data/uploads

# --- Optional: GitHub Export ---
# GITHUB_EXPORT_REPO=org/repo
# GITHUB_TOKEN=ghp_...
# GITHUB_EXPORT_BRANCH=gh-pages

# --- Optional: Logging ---
LOG_LEVEL=DEBUG
```

---

## Files to Create

| File | Description |
|------|-------------|
| `README.md` | Project overview and quick start |
| `docs/configuration.md` | Full env var reference |
| `docs/hf-spaces-deployment.md` | HF Spaces guide |
| `docs/development.md` | Local dev setup |
| `docs/architecture.md` | Technical architecture |
| `docs/admin-guide.md` | Admin workflow guide |
| `docs/agent-guide.md` | Bot/agent integration guide |
| `CONTRIBUTING.md` | Contributor guidelines |
| `.env.example` | Example environment file |

---

## Acceptance Criteria

- [ ] README provides clear quick start for both Docker and HF Spaces
- [ ] All environment variables documented with descriptions and examples
- [ ] HF Spaces deployment guide covers complete flow including troubleshooting
- [ ] Local development setup documented and tested
- [ ] Architecture diagram accurately represents the system
- [ ] Admin guide covers full event lifecycle
- [ ] Agent integration guide includes working code examples
- [ ] `.env.example` contains all variables with helpful comments
- [ ] Contributing guide enables new developers to get started

---

## Developer Notes

- Keep docs in `/docs` directory (Markdown files)
- Use Mermaid diagrams if GitHub rendering is desired (or ASCII for simplicity)
- Update docs when APIs change — consider this part of the definition of done for every task
- The agent guide should be testable with `curl` — include curl examples too
- Consider adding a `docs/faq.md` after the first real deployment
