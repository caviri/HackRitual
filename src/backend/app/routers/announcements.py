"""
Announcement endpoints — dispatches from the keeper.

Public:
  GET    /api/announcements                 visible dispatches, newest first

Admin:
  GET    /api/admin/announcements           all dispatches (hidden included)
  POST   /api/admin/announcements           write a dispatch
  PATCH  /api/admin/announcements/{id}      edit / toggle visibility
  DELETE /api/admin/announcements/{id}      remove
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.announcement import Announcement
from app.schemas.announcements import (
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementUpdate,
)
from app.services.audit import log_action

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/announcements", tags=["announcements"])
admin_router = APIRouter(prefix="/api/admin/announcements", tags=["announcements"])


@public_router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[Announcement]:
    """Visible dispatches, newest first."""
    return (
        db.query(Announcement)
        .filter(
            Announcement.event_id == settings.event_id,
            Announcement.visible.is_(True),
        )
        .order_by(Announcement.created_at.desc())
        .limit(limit)
        .all()
    )


@admin_router.get("", response_model=list[AnnouncementOut])
def list_all_announcements(
    db: Session = Depends(get_db),
    _admin=Depends(require_admin),
) -> list[Announcement]:
    return (
        db.query(Announcement)
        .filter(Announcement.event_id == settings.event_id)
        .order_by(Announcement.created_at.desc())
        .all()
    )


@admin_router.post("", response_model=AnnouncementOut, status_code=status.HTTP_201_CREATED)
def create_announcement(
    body: AnnouncementCreate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> Announcement:
    row = Announcement(
        event_id=settings.event_id,
        title=body.title.strip(),
        body=body.body.strip(),
        visible=body.visible,
        author_user_id=admin.id,
    )
    db.add(row)
    db.flush()
    log_action(db, "announcement.created", actor_id=admin.id,
               target_type="announcement", target_id=row.id,
               metadata={"title": row.title})
    db.commit()
    db.refresh(row)
    return row


def _get_or_404(announcement_id: str, db: Session) -> Announcement:
    row = db.get(Announcement, announcement_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "announcement not found")
    return row


@admin_router.patch("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: str,
    body: AnnouncementUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> Announcement:
    row = _get_or_404(announcement_id, db)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "no fields to update")
    if "title" in changes:
        row.title = changes["title"].strip()
    if "body" in changes:
        row.body = changes["body"].strip()
    if "visible" in changes:
        row.visible = changes["visible"]
    log_action(db, "announcement.updated", actor_id=admin.id,
               target_type="announcement", target_id=row.id,
               metadata={"fields": sorted(changes.keys())})
    db.commit()
    db.refresh(row)
    return row


@admin_router.delete(
    "/{announcement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
) -> None:
    row = _get_or_404(announcement_id, db)
    log_action(db, "announcement.deleted", actor_id=admin.id,
               target_type="announcement", target_id=row.id,
               metadata={"title": row.title})
    db.delete(row)
    db.commit()
