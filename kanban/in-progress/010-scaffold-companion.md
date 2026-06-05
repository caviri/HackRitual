---
id: "010"
title: "Scaffold Companion"
type: chore
status: in-progress
estimate: "2d"
size: M
depends_on: ["003"]
blocks: []
spec: "specs/specs/10-frontend-foundation.md"
tags: [frontend, mobile, kanban, scaffold, dev-tool]
---

# Scaffold Companion

A mobile-first development companion app served at `/scaffold/` — a living documentation browser, Kanban board, and project status dashboard for developers working on HackRitual.

## Tasks

- [x] Add PyYAML to declared dependencies (pyproject.toml + requirements.txt)
- [x] Create `kanban/` directory with ticket files for all 20 steps
- [ ] `backend/app/routers/scaffold.py` — 5 API endpoints for tickets, docs, and status
- [ ] Register scaffold router and static mount in `main.py`
- [ ] `scaffold/index.html` — full SPA (HTML + CSS + JS, no build step)
- [ ] `backend/tests/test_scaffold.py` — router tests

## Design

- **Board tab** — 4 swipeable Kanban columns (Backlog / Todo / In Progress / Done)
- **Docs tab** — browse and render all docs/*.md files
- **Log tab** — CHANGELOG.md rendered
- **Status tab** — live step counts + event state from DB
- Dark ritual theme (amber accent #f5a623, dark base #0d0f14)
- CSS `scroll-snap` for column swiping — no JS gesture library needed
- Slide-in panel for ticket and doc detail views
- Safe area insets for notch phones

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/scaffold/tickets` | List all ticket metadata |
| GET | `/api/scaffold/tickets/{id}` | Single ticket with body |
| GET | `/api/scaffold/docs` | List doc files |
| GET | `/api/scaffold/docs/{filename}` | Raw markdown content |
| GET | `/api/scaffold/status` | Aggregate stats + event state |

## Notes

- No auth required (dev tool only)
- `scaffold/` directory is not copied into Docker image — guarded by `if os.path.isdir()`
- Tickets are Markdown files with YAML frontmatter in `kanban/` at repo root
