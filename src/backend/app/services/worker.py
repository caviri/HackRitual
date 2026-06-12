"""
The queue worker — a single async loop draining the `tasks` table.

Runs inside the FastAPI process (started from the lifespan). Each tick claims one
due task, runs its handler, and records the outcome; failures back off and retry
via `task_queue`. Handlers are async and own their DB session.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.task import Task
from app.services import task_queue

logger = logging.getLogger(__name__)

Handler = Callable[[Session, Task], Awaitable[None]]


# --------------------------------------------------------------------------- #
# Handlers
# --------------------------------------------------------------------------- #
async def _handle_score_submission(db: Session, task: Task) -> None:
    from app.services.scoring_service import score_submission

    if not task.ref_id:
        raise ValueError("score_submission requires ref_id")
    score_submission(db, task.ref_id)
    db.commit()


async def _handle_export_bundle(db: Session, task: Task) -> None:
    from app.services.export_bundle import RedactionConfig, build_bundle

    payload = json.loads(task.payload_json or "{}")
    build_bundle(db, RedactionConfig(mode=payload.get("redaction_mode", "public")))


async def _handle_push_github(db: Session, task: Task) -> None:
    from app.services import github_push

    payload = json.loads(task.payload_json or "{}")
    export_id = payload.get("export_id", task.id)
    github_push.set_status(export_id, status="running")
    try:
        result = await github_push.run_push(payload)
    except Exception as exc:
        github_push.set_status(export_id, status="failed", error=str(exc)[:300])
        raise
    github_push.set_status(export_id, status="done", **result)


def default_handlers() -> dict[str, Handler]:
    return {
        "score_submission": _handle_score_submission,
        "export_bundle": _handle_export_bundle,
        "push_github": _handle_push_github,
    }


# --------------------------------------------------------------------------- #
# Processing
# --------------------------------------------------------------------------- #
async def process_task(db: Session, task: Task, handlers: dict[str, Handler]) -> None:
    """Run one claimed task; record done or failed (with backoff)."""
    handler = handlers.get(task.type)
    if handler is None:
        task_queue.mark_failed(db, task, f"no handler for '{task.type}'")
        return
    try:
        await handler(db, task)
        task_queue.mark_done(db, task)
    except Exception as exc:  # noqa: BLE001 — failure is a normal task outcome
        logger.warning("task failed", extra={"task_id": task.id, "type": task.type})
        # The handler may have left the session dirty; start clean to record state.
        db.rollback()
        task_queue.mark_failed(db, task, str(exc))


class Worker:
    """Polls the queue and processes tasks until stopped."""

    def __init__(
        self,
        handlers: dict[str, Handler] | None = None,
        poll_interval: float = 2.0,
    ) -> None:
        self.handlers = handlers or default_handlers()
        self.poll_interval = poll_interval
        self.running = False

    async def tick(self) -> bool:
        """Claim and process a single task. Returns True if one ran."""
        with SessionLocal() as db:
            task = task_queue.claim_next(db)
            if task is None:
                return False
            task_id = task.id
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task is not None:
                await process_task(db, task, self.handlers)
        return True

    async def run(self) -> None:
        self.running = True
        logger.info("queue worker started")
        while self.running:
            try:
                worked = await self.tick()
                if not worked:
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — never let the loop die
                logger.exception("worker tick failed")
                await asyncio.sleep(self.poll_interval)
        logger.info("queue worker stopped")
