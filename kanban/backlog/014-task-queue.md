---
id: "014"
title: "Task Queue & Worker"
type: feature
status: backlog
estimate: "4d"
size: L
depends_on: ["002"]
blocks: ["015"]
spec: "specs/specs/14-task-queue-worker.md"
tags: [task-queue, background-jobs, backend]
---

# Task Queue & Worker

Async background job processing using the `tasks` DB table — no external broker needed.

## Tasks

- [ ] `app/worker.py` — polling loop that picks up queued tasks from DB
- [ ] Task types: `send_email`, `score_submission`, `export_bundle`, `push_github`
- [ ] Claim-and-lock pattern: `UPDATE tasks SET status='running' WHERE status='queued' LIMIT 1`
- [ ] Retry logic: exponential backoff, max 3 attempts, `last_error` recorded
- [ ] `available_at` field enables delayed/scheduled tasks
- [ ] Worker started as background thread/asyncio task in FastAPI lifespan
- [ ] `GET /api/admin/tasks` — list tasks with status filtering
- [ ] `POST /api/admin/tasks/{id}/retry` — force retry a failed task

## Task Model

```
status: queued → running → done | failed
attempts: int (incremented on each try)
available_at: datetime (delay support)
last_error: str | None
```

## Notes

- Task model already in DB schema (Step 02) with optimal index on `(status, available_at)`
- Single-worker (one FastAPI process) — no distributed locking needed
- SQLite WAL mode allows reader queries during worker writes
