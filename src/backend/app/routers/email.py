"""Email endpoints — aggregate delivery metrics for operators."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.middleware.auth import require_admin
from app.models.user import User
from app.services import email_metrics


admin_email_router = APIRouter(prefix="/api/admin/email", tags=["email"])


@admin_email_router.get("/metrics")
def get_email_metrics(_admin: User = Depends(require_admin)) -> dict:
    """Counts only — sent / succeeded / failed and the last send time."""
    return email_metrics.snapshot()
