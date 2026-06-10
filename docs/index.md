# HackRitual — Documentation

> An easy-to-summon platform for ritualised collaborative invention.
> Let's gather and forge the unknown.

## What is HackRitual?

HackRitual is a **portable, single-container** event platform for hackathons, study-a-thons, challenges, and other time-bounded collaborative gatherings.

The lifecycle of every deployment follows the **Ritual**:

```
Summon → Gather → Create → Conclude → Archive → Release
```

Deploy it, run your event, export a structured JSON archive, then tear it down.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [Architecture](./architecture.md) | System components, container layout, data flow |
| [Data Model](./data-model.md) | Entity relationships and database schema |
| [Event Lifecycle](./event-lifecycle.md) | State machine for the Ritual |
| [API Overview](./api.md) | REST endpoint groups and auth model |
| [API Reference (full)](./api-reference.md) | Every endpoint, params, schemas — generated from the spec |
| [API Explorer (ReDoc)](./redoc.html) | Interactive browser for the OpenAPI spec |
| [Configuration](./configuration.md) | Full environment-variable reference |
| [Deployment](./deployment.md) | How to deploy on Hugging Face Spaces or locally |
| [Development](./development.md) | Local dev setup, tests, migrations |
| [Admin Guide](./admin-guide.md) | Running an event end to end |
| [Agent Guide](./agent-guide.md) | Bot/agent API integration with examples |
| `CONTRIBUTING.md` (repo root) | Conventions and PR process |
| [Writing Style](./writing-style.md) | Voice and tone for docs |

---

## Quick Links

| Resource | Location |
|----------|----------|
| Specs overview | `specs/specs/00-overview.md` |
| Full SRD | `specs/specs/specs.md` |
| Progress tracker | `PROGRESS.md` |
| Changelog | `CHANGELOG.md` |
| Risk register | `RISKS.md` |
| Environment variables | `.env.example` |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React / Next.js 14+ (static export) |
| Database | SQLite (WAL mode) |
| ORM / Migrations | SQLAlchemy 2 + Alembic |
| Auth | Admin-distributed access passwords → JWT in HTTP-only cookies |
| Container | Docker (single image) |
| Target deploy | Hugging Face Spaces (port 7860) |
| WASM runtime | wasmtime-py (MVP-3) |


<!-- Test modification at Fri Mar  6 17:11:34 UTC 2026 -->
