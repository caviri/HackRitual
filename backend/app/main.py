"""
HackRitual — FastAPI application entry point.

Responsibilities:
- App factory with lifespan (startup/shutdown hooks)
- CORS middleware
- Static file serving for Next.js build output
- Router registration
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

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
        from app.services.audit import log_action
        for email in settings.admin_seed_email_list:
            existing = db.query(User).filter_by(email=email).first()
            if existing is None:
                user = User(email=email, role="admin")
                db.add(user)
                db.flush()
                log_action(db, "user.admin_seeded", target_type="user", target_id=user.id,
                           metadata={"method": "seed_emails"})
                logger.info("Admin user seeded", extra={"email": email})
            elif existing.role != "admin":
                existing.role = "admin"
                log_action(db, "user.role_changed", target_type="user", target_id=existing.id,
                           metadata={"old_role": existing.role, "new_role": "admin", "method": "seed_emails"})
                logger.info("Existing user promoted to admin", extra={"email": email})
        db.commit()

    finally:
        db.close()

    yield

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
    # API routers
    # ---------------------------------------------------------------- #
    from app.routers.health import router as health_router
    from app.routers.auth import router as auth_router
    from app.routers.users import router as users_router
    from app.routers.setup import router as setup_router
    from app.routers.participants import router as participants_router
    from app.routers.scaffold import router as scaffold_router
    from app.routers.event import router as event_router
    from app.routers.tracks import router as tracks_router
    from app.routers.phases import router as phases_router
    from app.routers.pages import router as pages_router
    from app.routers.projects import router as projects_router, submissions_router
    from app.routers.uploads import router as uploads_router
    from app.routers.exports import router as exports_router
    from app.routers.me import router as me_router
    from app.routers.agents import router as agents_router, self_router as agent_self_router
    from app.routers.admin import router as admin_router
    from app.routers.repos import router as repos_router, feed_router as repos_feed_router
    from app.routers.scores import router as scores_router, score_id_router
    from app.routers.logs import router as logs_router

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(setup_router)
    app.include_router(participants_router)
    app.include_router(scaffold_router)
    app.include_router(event_router)
    app.include_router(tracks_router)
    app.include_router(phases_router)
    app.include_router(pages_router)
    app.include_router(projects_router)
    app.include_router(submissions_router)
    app.include_router(uploads_router)
    app.include_router(exports_router)
    app.include_router(me_router)
    app.include_router(agents_router)
    app.include_router(agent_self_router)
    app.include_router(admin_router)
    app.include_router(repos_router)
    app.include_router(repos_feed_router)
    app.include_router(scores_router)
    app.include_router(score_id_router)
    app.include_router(logs_router)

    # ---------------------------------------------------------------- #
    # Uploaded files (server-side dithered images) served at /uploads/*
    # ---------------------------------------------------------------- #
    from app.config import settings as _s
    if os.path.isdir(_s.upload_dir):
        app.mount("/uploads", StaticFiles(directory=_s.upload_dir), name="uploads")

    # ---------------------------------------------------------------- #
    # Scaffold companion UI (dev tool — mounted before Next.js catch-all)
    # ---------------------------------------------------------------- #
    scaffold_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scaffold")
    if os.path.isdir(scaffold_dir):
        app.mount("/scaffold", StaticFiles(directory=scaffold_dir, html=True), name="scaffold")
        logger.info("Serving scaffold UI", extra={"scaffold_dir": scaffold_dir})

    # ---------------------------------------------------------------- #
    # Static files (Next.js build output)
    # Mounted last so API routes always win.
    # ---------------------------------------------------------------- #
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "static")
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
