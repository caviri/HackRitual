"""
HackRitual — FastAPI application entry point.

Responsibilities:
- App factory with lifespan (startup/shutdown hooks)
- CORS middleware
- Static file serving for Next.js build output
- Router registration
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.utils.logging import configure_logging

# ------------------------------------------------------------------ #
# Bootstrap logging before anything else
# ------------------------------------------------------------------ #
_log_level = os.environ.get("LOG_LEVEL", "INFO")
configure_logging(_log_level)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Automatic state transitions (optional, gated by AUTO_TRANSITIONS)
# ------------------------------------------------------------------ #
async def _auto_transition_loop(interval_seconds: int = 60) -> None:
    """
    Advance the ritual on its clock: DRAFT→OPEN at start, OPEN→FROZEN at end.

    Runs only when AUTO_TRANSITIONS is set. Checks every `interval_seconds`;
    each due transition is recorded in the audit log like a manual one.
    """
    from datetime import datetime

    from app.config import settings
    from app.database import SessionLocal
    from app.services.audit import log_action
    from app.services.event import get_event, next_auto_state

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            with SessionLocal() as db:
                event = get_event(db)
                target = next_auto_state(
                    event.state,
                    datetime.now(UTC),
                    settings.event_start,
                    settings.event_end,
                )
                if target:
                    previous = event.state
                    event.state = target
                    event.updated_at = datetime.now(UTC)
                    log_action(
                        db,
                        "event.transition",
                        target_type="event",
                        target_id=event.id,
                        metadata={
                            "from": previous,
                            "to": target,
                            "reason": "auto",
                            "by": "system",
                        },
                    )
                    db.commit()
                    logger.info(
                        "Event auto-transitioned",
                        extra={"from": previous, "to": target},
                    )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — never let the loop die silently
            logger.exception("auto-transition check failed")


async def _cleanup_loop(interval_seconds: int = 3600) -> None:
    """Hourly data-retention sweep: expired sessions (§14.12)."""
    from app.database import SessionLocal
    from app.services.cleanup import cleanup_expired_data

    while True:
        try:
            await asyncio.sleep(interval_seconds)
            with SessionLocal() as db:
                removed = cleanup_expired_data(db)
            if removed.get("sessions"):
                logger.info("Retention cleanup", extra=removed)
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("cleanup sweep failed")


# ------------------------------------------------------------------ #
# Lifespan
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.config import settings
    from app.database import SessionLocal
    from app.models.event import Event
    from app.models.user import User

    logger.info(
        "HackRitual starting",
        extra={
            "event_id": settings.event_id,
            "event_title": settings.event_title,
            "db_path": settings.db_path,
            "version": settings.app_version,
        },
    )

    db = SessionLocal()
    try:
        # ---- Seed Event record ----------------------------------------
        event = db.get(Event, settings.event_id)
        if event is None:
            event = Event(
                id=settings.event_id,
                title=settings.event_title,
                type=settings.event_type,
                state="DRAFT",
                start_at=settings.event_start,
                end_at=settings.event_end,
            )
            db.add(event)
            db.commit()
            logger.info("Event record created", extra={"event_id": settings.event_id})
        else:
            logger.info("Event record exists", extra={"event_id": settings.event_id})

        # ---- Seed admin users (create or promote) ---------------------
        # The first seed email is the primary admin: its access password is
        # re-synced to ADMIN_PASSWORD on every boot, so changing the env var
        # and restarting always restores access. Other seed admins get a
        # generated password on first seeding (visible in the admin panel).
        from app.services.audit import log_action
        from app.services.passwords import generate_unique_password

        primary_email = settings.admin_seed_email_list[0]
        for email in settings.admin_seed_email_list:
            existing = db.query(User).filter_by(email=email).first()
            if existing is None:
                existing = User(email=email, role="admin")
                db.add(existing)
                db.flush()
                log_action(db, "user.admin_seeded", target_type="user", target_id=existing.id,
                           metadata={"method": "seed_emails"})
                logger.info("Admin user seeded", extra={"email": email})
            elif existing.role != "admin":
                existing.role = "admin"
                log_action(db, "user.role_changed", target_type="user", target_id=existing.id,
                           metadata={"old_role": existing.role, "new_role": "admin", "method": "seed_emails"})
                logger.info("Existing user promoted to admin", extra={"email": email})

            if email == primary_email:
                if existing.access_password != settings.admin_password:
                    existing.access_password = settings.admin_password
                    logger.info("Primary admin password synced from ADMIN_PASSWORD",
                                extra={"email": email})
            elif not existing.access_password:
                existing.access_password = generate_unique_password(db)
                logger.info("Generated access password for seeded admin",
                            extra={"email": email})
        db.commit()

    finally:
        db.close()

    # ---- Optional auto-transition background task ----------------------
    auto_task: asyncio.Task | None = None
    if settings.auto_transitions:
        auto_task = asyncio.create_task(_auto_transition_loop())
        logger.info("Auto-transitions enabled")

    # ---- Queue worker (drains the tasks table) -------------------------
    worker = None
    worker_task: asyncio.Task | None = None
    if settings.enable_worker:
        from app.database import SessionLocal as _SessionLocal
        from app.services.task_queue import recover_stale
        from app.services.worker import Worker

        with _SessionLocal() as wdb:
            recovered = recover_stale(wdb)
        if recovered:
            logger.info("Recovered stale tasks", extra={"count": recovered})
        worker = Worker()
        worker_task = asyncio.create_task(worker.run())

    # ---- Hourly data-retention cleanup ---------------------------------
    cleanup_task: asyncio.Task | None = None
    if settings.enable_worker:
        cleanup_task = asyncio.create_task(_cleanup_loop())

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    if worker is not None and worker_task is not None:
        worker.running = False
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    if auto_task is not None:
        auto_task.cancel()
        try:
            await auto_task
        except asyncio.CancelledError:
            pass

    logger.info("HackRitual shutting down")


# ------------------------------------------------------------------ #
# App factory
# ------------------------------------------------------------------ #
def create_app() -> FastAPI:
    from app.config import settings
    from app.docs import API_DESCRIPTION, OPENAPI_TAGS, render_docs_html

    app = FastAPI(
        title="HackRitual",
        version=settings.app_version,
        description=API_DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        # Disable the default docs — we render a HackRitual-themed page
        # via the route below.
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # /api/docs serves the Swagger UI (the spellbook); the frontend's /docs/
    # route serves the long-form handbook (the process). They are different
    # documents serving different audiences.
    @app.get("/api/docs", include_in_schema=False)
    def custom_swagger_ui():
        return render_docs_html(openapi_url=app.openapi_url or "/api/openapi.json")

    @app.get("/api/redoc", include_in_schema=False)
    def redoc_ui():
        from app.docs import render_redoc_html

        return render_redoc_html(openapi_url=app.openapi_url or "/api/openapi.json")

    # ---------------------------------------------------------------- #
    # CORS
    # ---------------------------------------------------------------- #
    allowed_origins = [
        settings.app_base_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---------------------------------------------------------------- #
    # Rate limiting (IP/abuse layer) — gated so tests aren't throttled
    # ---------------------------------------------------------------- #
    if settings.enable_rate_limit:
        from app.middleware.rate_limit import RateLimitMiddleware

        app.add_middleware(RateLimitMiddleware)

    # ---------------------------------------------------------------- #
    # API routers
    # ---------------------------------------------------------------- #
    from app.routers.abuse import admin_abuse_router
    from app.routers.admin import router as admin_router
    from app.routers.agents import (
        admin_router as agent_admin_router,
    )
    from app.routers.agents import (
        router as agents_router,
    )
    from app.routers.agents import (
        self_router as agent_self_router,
    )
    from app.routers.auth import router as auth_router
    from app.routers.event import admin_router as event_admin_router
    from app.routers.event import public_router as event_router
    from app.routers.exports import admin_export_router
    from app.routers.exports import router as exports_router
    from app.routers.health import router as health_router
    from app.routers.logs import router as logs_router
    from app.routers.me import router as me_router
    from app.routers.metrics import admin_metrics_router, privacy_router
    from app.routers.pages import router as pages_router
    from app.routers.participants import router as participants_router
    from app.routers.phases import router as phases_router
    from app.routers.projects import (
        admin_submissions_router,
        submissions_router,
    )
    from app.routers.projects import (
        router as projects_router,
    )
    from app.routers.queue import admin_queue_router
    from app.routers.repos import feed_router as repos_feed_router
    from app.routers.repos import router as repos_router
    from app.routers.scaffold import router as scaffold_router
    from app.routers.scores import (
        admin_scores_router,
        admin_scoring_router,
        leaderboard_router,
        score_id_router,
    )
    from app.routers.scores import (
        router as scores_router,
    )
    from app.routers.scoring import admin_wasm_router, public_scoring_router
    from app.routers.tracks import router as tracks_router
    from app.routers.uploads import router as uploads_router
    from app.routers.users import router as users_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(participants_router)
    app.include_router(scaffold_router)
    app.include_router(event_router)
    app.include_router(event_admin_router)
    app.include_router(tracks_router)
    app.include_router(phases_router)
    app.include_router(pages_router)
    app.include_router(projects_router)
    app.include_router(submissions_router)
    app.include_router(admin_submissions_router)
    app.include_router(uploads_router)
    app.include_router(exports_router)
    app.include_router(admin_export_router)
    app.include_router(me_router)
    app.include_router(agents_router)
    app.include_router(agent_self_router)
    app.include_router(agent_admin_router)
    app.include_router(admin_router)
    app.include_router(repos_router)
    app.include_router(repos_feed_router)
    app.include_router(scores_router)
    app.include_router(score_id_router)
    app.include_router(admin_scoring_router)
    app.include_router(admin_scores_router)
    app.include_router(leaderboard_router)
    app.include_router(logs_router)
    app.include_router(admin_queue_router)
    app.include_router(admin_abuse_router)
    app.include_router(admin_wasm_router)
    app.include_router(public_scoring_router)
    app.include_router(admin_metrics_router)
    app.include_router(privacy_router)

    # ---------------------------------------------------------------- #
    # Uploaded files (server-side dithered images) served at /uploads/*
    # ---------------------------------------------------------------- #
    from app.config import settings as _s
    if os.path.isdir(_s.upload_dir):
        app.mount("/uploads", StaticFiles(directory=_s.upload_dir), name="uploads")

    # ---------------------------------------------------------------- #
    # Scaffold companion UI (dev tool — mounted before Next.js catch-all)
    # ---------------------------------------------------------------- #
    # Lives inside the backend package (app/scaffold) so it travels with the
    # code — present both locally and in the image (COPY src/backend → /app/backend).
    scaffold_dir = os.path.join(os.path.dirname(__file__), "scaffold")
    if os.path.isdir(scaffold_dir):
        app.mount("/scaffold", StaticFiles(directory=scaffold_dir, html=True), name="scaffold")
        logger.info("Serving scaffold UI", extra={"scaffold_dir": scaffold_dir})

    # ---------------------------------------------------------------- #
    # Static files (Next.js build output)
    # Mounted last so API routes always win.
    #
    # The production image copies the export to /app/static (../../static from
    # here). The committed static/ is gitignored build output, so for local
    # `uvicorn` runs we fall back to the canonical export at src/frontend/out.
    # ---------------------------------------------------------------- #
    _here = os.path.dirname(__file__)
    static_dir = next(
        (
            d
            for d in (
                os.path.join(_here, "..", "..", "static"),       # image: /app/static
                os.path.join(_here, "..", "..", "frontend", "out"),  # local: src/frontend/out
            )
            if os.path.isdir(d)
        ),
        os.path.join(_here, "..", "..", "static"),
    )
    if os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        logger.info("Serving frontend static files", extra={"static_dir": static_dir})
    else:
        logger.warning(
            "Static directory not found — frontend will not be served",
            extra={"static_dir": static_dir},
        )

    return app


# ------------------------------------------------------------------ #
# Module-level app instance (used by uvicorn)
# ------------------------------------------------------------------ #
app = create_app()
