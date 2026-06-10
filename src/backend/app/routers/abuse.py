"""Admin abuse-response tools (Step 15): IP blocking + abuse metrics."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import require_admin
from app.middleware.rate_limit import blocklist
from app.models.user import User
from app.services import abuse_metrics
from app.services.audit import log_action


admin_abuse_router = APIRouter(prefix="/api/admin/abuse", tags=["abuse"])


class BlockIPRequest(BaseModel):
    ip_prefix: str = Field(..., description="Network to block, e.g. 192.168.1.0/24")
    duration_hours: int = Field(24, ge=1, le=24 * 30)
    reason: Optional[str] = None


@admin_abuse_router.post("/block-ip")
def block_ip(
    body: BlockIPRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict:
    """Temporarily block an IP network (in-memory, auto-expiring)."""
    expiry = blocklist.block(
        body.ip_prefix, body.duration_hours * 3600, body.reason or ""
    )
    log_action(
        db,
        "abuse.ip_blocked",
        actor_id=admin.id,
        target_type="ip",
        target_id=body.ip_prefix,
        metadata={"duration_hours": body.duration_hours, "reason": body.reason},
    )
    db.commit()
    return {
        "blocked": body.ip_prefix,
        "expires_at": datetime.fromtimestamp(expiry, tz=timezone.utc).isoformat(),
    }


@admin_abuse_router.get("/stats")
def abuse_stats(_admin: User = Depends(require_admin)) -> dict:
    """Aggregate rate-limit triggers and the active IP blocks."""
    active = blocklist.active()
    return {
        "rate_limit": abuse_metrics.snapshot(),
        "blocked_prefixes": sorted(active.keys()),
        "blocked_count": len(active),
    }
