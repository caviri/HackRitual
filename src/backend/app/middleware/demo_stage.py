"""
Demo-stage routing — five snapshots, one container.

Active only when DEMO_STAGES=true. Picks the request's database from the
`?stage=` query param (wins), the `X-Demo-Stage` header, or the `demo_stage`
cookie; anything else falls through to the primary database. The header is
the workhorse: cookies die inside the huggingface.co iframe (third-party,
SameSite), so the frontend sends the stage explicitly on every API call.
Pure ASGI middleware so the ContextVar is set and reset in the same task
that runs the endpoint.
"""

from __future__ import annotations

from urllib.parse import parse_qs

from fastapi import HTTPException, status

from app.database import DEMO_STAGE_NAMES, active_demo_stage


class DemoStageMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw: str | None = None
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        if qs.get("stage"):
            raw = qs["stage"][0]
        if raw is None:
            header = next(
                (v for k, v in scope.get("headers", []) if k == b"x-demo-stage"),
                None,
            )
            if header:
                raw = header.decode("latin-1")
        if raw is None:
            cookie_header = next(
                (v for k, v in scope.get("headers", []) if k == b"cookie"), b""
            ).decode("latin-1")
            for part in cookie_header.split(";"):
                key, _, value = part.strip().partition("=")
                if key == "demo_stage":
                    raw = value
                    break

        stage = raw.upper() if raw and raw.upper() in DEMO_STAGE_NAMES else None
        token = active_demo_stage.set(stage)
        try:
            await self.app(scope, receive, send)
        finally:
            active_demo_stage.reset(token)


def require_primary_db() -> None:
    """Dependency for endpoints that must not run inside a stage sandbox
    (anything that enqueues work for the primary-DB queue worker, or writes
    shared on-disk artifacts like export bundles)."""
    if active_demo_stage.get() is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Not available inside a demo stage sandbox. "
            "Switch the stage bar to live and retry.",
        )
