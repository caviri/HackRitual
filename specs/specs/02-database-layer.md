# 02 — Database Layer

**Milestone:** MVP-1
**Priority:** Critical (foundation for all data)
**Dependencies:** [01-project-setup-docker](01-project-setup-docker.md)
**Specs reference:** §5 (Data Storage), §9 (Data Model)

---

## Overview

Set up SQLite with WAL mode, define all SQLAlchemy models, configure Alembic migrations, and implement the file storage layer. SQLite is the sole database — no external DB services.

---

## Tasks

### 2.1 SQLite Engine Configuration

In `backend/app/database.py`:

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_engine(
    f"sqlite:///{settings.DB_PATH}",
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
```

Key requirements from specs §5.1:
- WAL mode for concurrent reads
- `busy_timeout=5000` (configurable via env)
- Short transactions to prevent "database is locked" errors
- Single app process writing (FastAPI with thread pool)

### 2.2 SQLAlchemy Models

Define all models from specs §9. Use SQLAlchemy 2.0 declarative style.

#### `models/user.py` — Users

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[str]            # UUID
    email: Mapped[str]         # unique
    role: Mapped[str]          # 'user' | 'admin' | 'judge' | 'mod'
    created_at: Mapped[datetime]
    last_login_at: Mapped[datetime | None]
```

#### `models/login_code.py` — Login Codes

```python
class LoginCode(Base):
    __tablename__ = "login_codes"
    id: Mapped[str]
    email: Mapped[str]
    code_hash: Mapped[str]     # bcrypt or sha256 hash of the code
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    request_ip: Mapped[str | None]  # truncated/hashed per privacy policy
```

#### `models/session.py` — Sessions (optional, if not pure JWT)

```python
class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str]
    user_id: Mapped[str]       # FK → users.id
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
```

#### `models/participant.py` — Participants

```python
class Participant(Base):
    __tablename__ = "participants"
    id: Mapped[str]
    event_id: Mapped[str]
    type: Mapped[str]          # 'human' | 'agent' | 'team'
    display_name: Mapped[str]
    affiliation: Mapped[str | None]
    links_json: Mapped[str | None]  # JSON string
    status: Mapped[str]        # 'active' | 'disabled' | 'banned'
    created_at: Mapped[datetime]
```

#### `models/participant_member.py` — Team Membership

```python
class ParticipantMember(Base):
    __tablename__ = "participant_members"
    id: Mapped[str]
    participant_id: Mapped[str]  # FK → participants.id (team)
    user_id: Mapped[str | None]  # FK → users.id
    agent_id: Mapped[str | None] # FK → agents.id
    role_in_team: Mapped[str]    # 'captain' | 'member' | 'agent'
```

#### `models/agent.py` — Agents

```python
class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[str]
    name: Mapped[str]
    owner_user_id: Mapped[str | None]  # FK → users.id
    api_key_hash: Mapped[str]
    status: Mapped[str]        # 'active' | 'revoked'
    created_at: Mapped[datetime]
```

#### `models/submission.py` — Submissions

```python
class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str]
    event_id: Mapped[str]
    participant_id: Mapped[str]  # FK → participants.id
    title: Mapped[str | None]
    description: Mapped[str | None]
    payload_json: Mapped[str | None]  # structured agent payload
    status: Mapped[str]        # 'received' | 'queued' | 'scored' | 'failed' | 'withdrawn'
    created_at: Mapped[datetime]
```

#### `models/file.py` — Files

```python
class File(Base):
    __tablename__ = "files"
    id: Mapped[str]
    submission_id: Mapped[str]  # FK → submissions.id
    path: Mapped[str]           # relative path in UPLOAD_DIR
    mime_type: Mapped[str]
    size_bytes: Mapped[int]
    sha256: Mapped[str]
    created_at: Mapped[datetime]
```

#### `models/score.py` — Scores

```python
class Score(Base):
    __tablename__ = "scores"
    id: Mapped[str]
    submission_id: Mapped[str]  # FK → submissions.id
    score_value: Mapped[float]
    breakdown_json: Mapped[str | None]
    scored_at: Mapped[datetime | None]
    status: Mapped[str]        # 'pending' | 'scored' | 'failed' | 'disqualified'
    scorer_version: Mapped[str | None]
```

#### `models/task.py` — Internal Task Queue

```python
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str]
    type: Mapped[str]          # 'send_email' | 'score_submission' | 'export_bundle' | 'push_github'
    ref_id: Mapped[str | None] # reference to related entity
    status: Mapped[str]        # 'queued' | 'running' | 'done' | 'failed'
    attempts: Mapped[int]
    available_at: Mapped[datetime]
    last_error: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

#### `models/audit_log.py` — Audit Log

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[str]
    actor_user_id: Mapped[str | None]  # FK → users.id (null for system actions)
    action: Mapped[str]         # e.g., 'event.state_change', 'participant.ban'
    target_type: Mapped[str | None]
    target_id: Mapped[str | None]
    metadata_json: Mapped[str | None]
    created_at: Mapped[datetime]
```

#### `models/event.py` — Event Configuration (runtime state)

```python
class Event(Base):
    __tablename__ = "events"
    id: Mapped[str]             # from EVENT_ID env var
    title: Mapped[str]
    type: Mapped[str]
    state: Mapped[str]          # 'DRAFT' | 'OPEN' | 'FROZEN' | 'FINAL' | 'ARCHIVED'
    start_at: Mapped[datetime]
    end_at: Mapped[datetime]
    config_json: Mapped[str | None]  # submission limits, leaderboard mode, etc.
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 2.3 Alembic Setup

- Initialize Alembic in `backend/alembic/`
- Configure `alembic.ini` to read `DB_PATH` from environment
- Create initial migration with all tables above
- Entrypoint script runs `alembic upgrade head` on every container start

### 2.4 Database Session Management

- Use FastAPI dependency injection for DB sessions:
  ```python
  async def get_db():
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```
- Keep transactions short — commit as early as possible
- Use `db.refresh()` after commits when returning updated objects

### 2.5 File Storage Layer

Per specs §5.2:
- Files stored at: `/data/uploads/<event_id>/<participant_id>/<submission_id>/`
- Only metadata + paths stored in DB (never blobs)
- Implement utility functions:
  - `save_upload(file, submission_id, participant_id) -> File`
  - `get_upload_path(file_record) -> Path`
  - `delete_upload(file_record) -> bool`
- Calculate SHA-256 on upload for integrity verification

### 2.6 Admin Seeding

On first startup (in entrypoint or lifespan):
- If `ADMIN_SEED_EMAILS` is set, create User records with `role='admin'` for each email
- If users already exist, skip (idempotent)
- If `ADMIN_SETUP_TOKEN` is set instead, expose `POST /api/setup` that accepts the token and an email to create the first admin
- Create the Event record from env vars if it doesn't exist

---

## Acceptance Criteria

- [ ] SQLite database created at configured path with WAL mode enabled
- [ ] All models from specs §9 are defined and migrated
- [ ] Foreign key constraints enforced
- [ ] Alembic migrations run on container startup
- [ ] File uploads saved to correct directory structure
- [ ] Admin users seeded on first start
- [ ] Event record created from env vars on first start
- [ ] Database survives container restart when `/data` is persistent

---

## Developer Notes

- Use UUIDs (v4) for all primary keys — `str` type in SQLite, generated in Python
- Use `datetime.utcnow()` for all timestamps (store as UTC)
- Index columns that will be queried frequently: `users.email`, `participants.event_id`, `submissions.participant_id`, `scores.submission_id`
- Consider adding a `UNIQUE` constraint on `(event_id, participant_id)` in submissions if "latest counts" mode is used
- Test with both persistent and ephemeral storage to verify behavior
