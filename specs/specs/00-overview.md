# HackRitual — Development Task Overview

> An easy-to-summon platform for ritualised collaborative invention.
> Let's gather and forge the unknown.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / FastAPI |
| Frontend | React / Next.js 14+ |
| Database | SQLite (WAL mode) |
| ORM / Migrations | SQLAlchemy + Alembic |
| Auth | JWT (HTTP-only cookies) |
| Email | SMTP (aiosmtplib) |
| Container | Docker (single container) |
| Target deploy | Hugging Face Spaces (Docker runtime) |
| WASM runtime | wasmtime-py (MVP-3) |

## Milestone Roadmap

### MVP-1: Core Ritual Capsule

The minimum viable event platform — deploy, register, submit, score, export.

| # | Task | File |
|---|------|------|
| 01 | Project Setup & Docker | [01-project-setup-docker.md](01-project-setup-docker.md) |
| 02 | Database Layer | [02-database-layer.md](02-database-layer.md) |
| 03 | Authentication | [03-authentication.md](03-authentication.md) |
| 04 | User Management | [04-user-management.md](04-user-management.md) |
| 05 | Participant Management | [05-participant-management.md](05-participant-management.md) |
| 06 | Event Lifecycle | [06-event-lifecycle.md](06-event-lifecycle.md) |
| 07 | Submission System | [07-submission-system.md](07-submission-system.md) |
| 08 | Scoring (Basic) | [08-scoring-basic.md](08-scoring-basic.md) |
| 09 | Admin Console | [09-admin-console.md](09-admin-console.md) |
| 10 | Frontend Foundation | [10-frontend-foundation.md](10-frontend-foundation.md) |
| 11 | JSON Export | [11-json-export.md](11-json-export.md) |
| 12 | Email System | [12-email-system.md](12-email-system.md) |

### MVP-2: Agents + Queue

Bot participation, async processing, and abuse resistance.

| # | Task | File |
|---|------|------|
| 13 | Agent System | [13-agent-system.md](13-agent-system.md) |
| 14 | Task Queue & Worker | [14-task-queue-worker.md](14-task-queue-worker.md) |
| 15 | Rate Limiting & Abuse Resistance | [15-rate-limiting-abuse.md](15-rate-limiting-abuse.md) |

### MVP-3: WASM Scoring

Deterministic, portable scoring with optional client-side preview.

| # | Task | File |
|---|------|------|
| 16 | WASM Scoring Module | [16-wasm-scoring.md](16-wasm-scoring.md) |

### MVP-4: GitHub Pages Export

Long-term archival with optional static site publishing.

| # | Task | File |
|---|------|------|
| 17 | GitHub Export & Static Site | [17-github-export.md](17-github-export.md) |

### Cross-Cutting

Concerns that span all milestones.

| # | Task | File |
|---|------|------|
| 18 | Privacy & Statistics | [18-privacy-statistics.md](18-privacy-statistics.md) |
| 19 | API Documentation | [19-api-documentation.md](19-api-documentation.md) |
| 20 | Deployment Guide | [20-deployment-guide.md](20-deployment-guide.md) |

## Dependency Graph

```
01-project-setup-docker
  └── 02-database-layer
        ├── 03-authentication
        │     └── 04-user-management
        │           ├── 05-participant-management
        │           │     ├── 07-submission-system
        │           │     │     └── 08-scoring-basic
        │           │     └── 13-agent-system (MVP-2)
        │           └── 09-admin-console
        ├── 06-event-lifecycle
        ├── 12-email-system
        └── 14-task-queue-worker (MVP-2)

10-frontend-foundation (parallel with backend tasks)
  └── depends on: 03, 04, 05, 06, 07, 08

11-json-export
  └── depends on: 02, 05, 07, 08

15-rate-limiting-abuse (MVP-2)
  └── depends on: 03, 07, 13

16-wasm-scoring (MVP-3)
  └── depends on: 08

17-github-export (MVP-4)
  └── depends on: 11

18-privacy-statistics (parallel, integrate as you go)
19-api-documentation (parallel, build incrementally)
20-deployment-guide (after MVP-1 is functional)
```

## Suggested Build Order

1. **01** → **02** → **12** (infra + DB + email — foundation)
2. **03** → **04** (auth + users — needed by everything)
3. **06** (event lifecycle — state machine)
4. **05** (participants — depends on users + events)
5. **07** → **08** (submissions + scoring — core loop)
6. **10** (frontend — can start in parallel after step 2)
7. **09** (admin console — after most backend is in place)
8. **11** (JSON export)
9. **13** → **14** → **15** (MVP-2 agents + queue + rate limits)
10. **16** (MVP-3 WASM scoring)
11. **17** (MVP-4 GitHub export)
12. **18**, **19**, **20** (cross-cutting — incrementally throughout)

## Reference

- Full specifications: [specs.md](specs.md)
- Export schema draft: specs.md § Appendix A
- Open questions: specs.md § 13
