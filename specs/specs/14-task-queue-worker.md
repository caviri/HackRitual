# 14 — Task Queue & Worker

**Milestone:** MVP-2
**Priority:** High
**Dependencies:** [02-database-layer](02-database-layer.md)
**Specs reference:** §9 (Tasks table), §7.5 (Async scoring), §7.6 (Email queue)

---

## Overview

Implement an internal task queue backed by the SQLite `tasks` table and a worker loop that runs inside the same container. This replaces the simple `BackgroundTasks` from MVP-1 with a persistent, retryable queue for scoring, email sending, export generation, and GitHub push operations.

---

## Tasks

### 14.1 Task Model (already defined in 02)

```python
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str]
    type: Mapped[str]          # 'send_email' | 'score_submission' | 'export_bundle' | 'push_github'
    ref_id: Mapped[str | None] # FK to related entity
    payload_json: Mapped[str | None]  # task-specific payload
    status: Mapped[str]        # 'queued' | 'running' | 'done' | 'failed' | 'dead'
    attempts: Mapped[int]      # attempt counter
    max_attempts: Mapped[int]  # default 3
    available_at: Mapped[datetime]    # for delayed/retry scheduling
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    last_error: Mapped[str | None]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 14.2 Task Enqueue Service

```python
class TaskQueueService:
    def enqueue(
        self,
        db: Session,
        task_type: str,
        ref_id: str | None = None,
        payload: dict | None = None,
        delay_seconds: int = 0,
    ) -> Task:
        """Create a new task in the queue."""
        task = Task(
            id=str(uuid4()),
            type=task_type,
            ref_id=ref_id,
            payload_json=json.dumps(payload) if payload else None,
            status="queued",
            attempts=0,
            max_attempts=3,
            available_at=datetime.utcnow() + timedelta(seconds=delay_seconds),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(task)
        db.commit()
        return task
```

Usage examples:
```python
# Queue a scoring task
queue.enqueue(db, "score_submission", ref_id=submission.id)

# Queue an email with delay
queue.enqueue(db, "send_email", payload={"to": email, "template": "login_code", "code": code})

# Queue export generation
queue.enqueue(db, "export_bundle", payload={"redaction_mode": "public"})
```

### 14.3 Worker Loop

A background worker that polls the `tasks` table and processes tasks:

```python
class Worker:
    def __init__(self, handlers: dict[str, TaskHandler]):
        self.handlers = handlers
        self.running = True
        self.poll_interval = 2  # seconds

    async def run(self):
        """Main worker loop — runs in a background thread/task."""
        while self.running:
            task = self.claim_next_task()
            if task:
                await self.process_task(task)
            else:
                await asyncio.sleep(self.poll_interval)

    def claim_next_task(self) -> Task | None:
        """Atomically claim the next available task."""
        # Use UPDATE ... WHERE to atomically claim
        # This prevents double-processing in concurrent scenarios
        with get_db_session() as db:
            task = db.query(Task).filter(
                Task.status == "queued",
                Task.available_at <= datetime.utcnow(),
            ).order_by(Task.available_at.asc()).first()

            if task:
                task.status = "running"
                task.attempts += 1
                task.started_at = datetime.utcnow()
                task.updated_at = datetime.utcnow()
                db.commit()
            return task

    async def process_task(self, task: Task):
        """Execute a task with error handling."""
        handler = self.handlers.get(task.type)
        try:
            await handler.execute(task)
            task.status = "done"
            task.completed_at = datetime.utcnow()
        except Exception as e:
            task.last_error = str(e)
            if task.attempts >= task.max_attempts:
                task.status = "dead"  # permanently failed
            else:
                task.status = "queued"
                # Exponential backoff: 30s, 120s, 480s
                delay = 30 * (4 ** (task.attempts - 1))
                task.available_at = datetime.utcnow() + timedelta(seconds=delay)
        finally:
            task.updated_at = datetime.utcnow()
```

### 14.4 Task Handlers

Register handlers for each task type:

```python
class ScoreSubmissionHandler(TaskHandler):
    async def execute(self, task: Task):
        submission_id = task.ref_id
        scoring_service.score_submission(db, submission_id)

class SendEmailHandler(TaskHandler):
    async def execute(self, task: Task):
        payload = json.loads(task.payload_json)
        await email_service.send(
            to=payload["to"],
            subject=...,
            body_html=...,
        )

class ExportBundleHandler(TaskHandler):
    async def execute(self, task: Task):
        payload = json.loads(task.payload_json)
        export_service.generate_bundle(db, RedactionConfig(**payload))

class PushGitHubHandler(TaskHandler):
    async def execute(self, task: Task):
        github_service.push_export(task.ref_id)
```

### 14.5 Worker Startup

Start the worker as part of the FastAPI lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start worker in background
    worker = Worker(handlers={
        "score_submission": ScoreSubmissionHandler(),
        "send_email": SendEmailHandler(),
        "export_bundle": ExportBundleHandler(),
        "push_github": PushGitHubHandler(),
    })
    worker_task = asyncio.create_task(worker.run())

    yield

    # Shutdown worker gracefully
    worker.running = False
    await worker_task
```

### 14.6 Stale Task Recovery

On startup, recover tasks that were `running` when the container stopped:

```python
def recover_stale_tasks(db: Session):
    """Reset running tasks back to queued (container restart recovery)."""
    stale = db.query(Task).filter(Task.status == "running").all()
    for task in stale:
        task.status = "queued"
        task.updated_at = datetime.utcnow()
    db.commit()
    if stale:
        logger.info(f"Recovered {len(stale)} stale tasks")
```

### 14.7 Admin Queue Monitoring

#### Queue status
`GET /api/admin/queue/status`

```json
{
  "queued": 5,
  "running": 1,
  "done_last_hour": 42,
  "failed_last_hour": 2,
  "dead": 0,
  "by_type": {
    "score_submission": { "queued": 3, "running": 1 },
    "send_email": { "queued": 2, "running": 0 }
  }
}
```

#### List failed tasks
`GET /api/admin/queue/failed`

#### Retry dead task
`POST /api/admin/queue/{task_id}/retry`

Resets a `dead` task back to `queued` with attempts reset.

#### Purge completed tasks
`POST /api/admin/queue/purge`

Deletes `done` tasks older than a configurable threshold (default: 24 hours).

---

## API Endpoints Summary

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/admin/queue/status` | Admin | Queue overview |
| GET | `/api/admin/queue/failed` | Admin | List failed tasks |
| POST | `/api/admin/queue/{id}/retry` | Admin | Retry dead task |
| POST | `/api/admin/queue/purge` | Admin | Purge completed |

---

## Acceptance Criteria

- [ ] Tasks are persisted in SQLite and survive container restarts
- [ ] Worker loop picks up and processes tasks in order
- [ ] Failed tasks retry with exponential backoff
- [ ] Tasks marked `dead` after max attempts
- [ ] Stale `running` tasks recovered on startup
- [ ] Scoring runs asynchronously via queue
- [ ] Email sending runs via queue with retry
- [ ] Admin can monitor queue status and retry failures
- [ ] No duplicate task processing (atomic claim)
- [ ] Worker shuts down gracefully on container stop

---

## Developer Notes

- This is a "poor man's task queue" — no Redis/RabbitMQ needed, just SQLite
- The atomic claim query is critical: use `UPDATE ... WHERE status='queued' AND id = (SELECT id FROM tasks WHERE ... LIMIT 1)` to prevent race conditions
- Single worker is fine for MVP — multiple workers would need row-level locking
- Poll interval of 2 seconds is a good balance between responsiveness and DB load
- Monitor the `tasks` table size — purge old completed tasks regularly
- Log task execution times for the admin scoring status dashboard
- Consider adding a `priority` column if certain task types need to run first
