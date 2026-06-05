---
id: "002"
title: "Database Layer"
type: chore
status: done
estimate: "2d"
size: L
depends_on: ["001"]
blocks: ["003", "005", "006", "011", "012", "014"]
spec: "specs/specs/02-database-layer.md"
tags: [database, sqlalchemy, alembic, sqlite]
tests_passing: 37
---

# Database Layer

SQLAlchemy ORM models, Alembic migrations, SQLite WAL configuration, and file upload utilities.

## Completed

- [x] `backend/app/database.py` — engine, WAL/busy_timeout/FK pragmas, SessionLocal, check_db
- [x] All 11 SQLAlchemy models: user, login_code, session, participant, participant_member, agent, submission, file, score, task, audit_log, event
- [x] `models/__init__.py` — imports all models for Alembic autogenerate
- [x] `alembic/env.py` — wired to Base.metadata, render_as_batch for SQLite
- [x] Initial migration (`4801ca88b7f6_initial_schema.py`) — 12 tables
- [x] `app/utils/files.py` — save_upload, get_upload_path, delete_upload, SHA-256 integrity
- [x] `main.py` lifespan — seeds Event record + admin users from env on first start
- [x] `routers/health.py` — reads real event_state from Event table

## SQLite Config

WAL mode, `synchronous=NORMAL`, `busy_timeout=5000ms`, `foreign_keys=ON` — set on every connection via event listener.

## Notes

- `datetime.utcnow()` deprecation warnings expected (Python 3.12); will address later
- `ASGITransport` does not trigger FastAPI lifespans — seeding tested via direct logic calls
