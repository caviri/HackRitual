# HackRitual

> *An easy-to-summon platform for ritualised collaborative invention.*
> *Gather your participants. Forge something from nothing. Export the artefact. Dispel the container.*

HackRitual is a **portable, single-container** event platform for hackathons, challenges, and time-bounded collaborative invention. It lives in one Docker image, persists its memory in a single SQLite file, and vanishes without a trace when the ritual is over.

Summon it. Run the event. Export a structured JSON archive. Tear it down.

---

## The Ritual States

Every event moves through five sacred phases:

```
DRAFT → OPEN → FROZEN → FINAL → ARCHIVED
```

| State | Meaning |
|-------|---------|
| `DRAFT` | The circle is drawn. Configuration is being set. No participants yet. |
| `OPEN` | The gates are open. Participants join, teams form, submissions flow. |
| `FROZEN` | The forge cools. Submissions close; scoring begins. |
| `FINAL` | The verdict is inscribed. Results are public, no changes permitted. |
| `ARCHIVED` | The ritual is complete. The record is sealed and ready for export. |

See [docs/event-lifecycle.md](docs/event-lifecycle.md) for the full state machine.

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Python 3.11+
- Node.js 20+ (for frontend development)
- Docker (for production builds)

### Invoke the Dev Server

```bash
# 1. Clone the grimoire
git clone <repo-url>
cd HackRitual

# 2. Bind the dependencies
cd backend && uv sync --extra dev && cd ..

# 3. Inscribe your environment
cp .env.example .env
# Edit .env — set JWT_SECRET, SMTP_*, EVENT_*, ADMIN_SEED_EMAILS

# 4. Run the migrations (bind the schema to the stone)
cd backend && uv run hackritual migrate && cd ..

# 5. Summon the server
cd backend && uv run hackritual serve --reload
# → http://localhost:7860
```

### Test the Bindings

```bash
cd backend && uv run pytest -v
```

---

## CLI

After `uv sync`, the `hackritual` CLI is available in your venv:

```
hackritual --help

Commands:
  serve     Summon the API server (uvicorn)
  migrate   Bind the database schema (Alembic)
  health    Query the vital signs of a running instance
  info      Reveal configuration (secrets masked)
```

Examples:

```bash
# Dev server with hot-reload
uv run hackritual serve --reload

# Check a deployed instance
uv run hackritual health --url https://my-space.hf.space

# Inspect configuration
uv run hackritual info
```

---

## Docker

```bash
# Forge the image
docker build -f docker/Dockerfile -t hackritual .

# Invoke locally
docker run -p 7860:7860 --env-file .env -v $(pwd)/data:/data hackritual

# Verify the summoning
curl http://localhost:7860/api/health
```

---

## Deploy to Hugging Face Spaces

HackRitual is designed for the HF Spaces Docker runtime. One Space, one event, one container.

1. Create a new Space (SDK: **Docker**)
2. Enable **Persistent Storage** — without it the ritual memory is ephemeral and will vanish on restart
3. Set environment variables from `.env.example`
4. Push this repository to the Space
5. Verify: `https://<your-space>.hf.space/api/health`

See [docs/deployment.md](docs/deployment.md) for the full invocation guide.

---

## Architecture

One container. One process. One file on disk.

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React / Next.js 14+ (static export, served by FastAPI) |
| Database | SQLite WAL mode + Alembic migrations |
| Auth | JWT in HTTP-only cookies — passwordless email magic links |
| Email | SMTP via aiosmtplib |
| CLI | Typer + Rich |
| Container | Docker, single image, port 7860 |
| Deploy target | Hugging Face Spaces |

The frontend is compiled to static files at build time and served directly by the FastAPI process — no Node.js runtime in production. The database is a single SQLite file at `/data/app.db`. The entire state of the event lives in that file.

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | System design, container layout, request flows |
| [docs/data-model.md](docs/data-model.md) | Entity relationships and database schema |
| [docs/event-lifecycle.md](docs/event-lifecycle.md) | The Ritual state machine |
| [docs/api.md](docs/api.md) | REST API reference |
| [docs/deployment.md](docs/deployment.md) | Deployment (HF Spaces, Docker, local) |
| [PROGRESS.md](PROGRESS.md) | Implementation status tracker |
| [CHANGELOG.md](CHANGELOG.md) | Chronicle of changes |
| [RISKS.md](RISKS.md) | Risk register and wards |
| [docs/writing-style.md](docs/writing-style.md) | Voice and tone guide for all documentation |

---

## Current Status

| Step | Ritual | Status |
|------|--------|--------|
| 01 | Project Setup & Docker | ✓ Complete |
| 02 | Database Layer | ✓ Complete |
| 03 | Authentication | ✓ Complete |
| 04 | User Management | ✓ Complete |
| 05–12 | Submissions, Scoring, Email, Export… | pending |

110/110 tests passing.
