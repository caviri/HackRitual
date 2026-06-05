"""Track CRUD — thematic groupings inside the event."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.track import Track
from app.models.user import User
from app.schemas.content import TrackCreate, TrackResponse


router = APIRouter(prefix="/api/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackResponse])
def list_tracks(db: Session = Depends(get_db)) -> list[Track]:
    return db.query(Track).order_by(Track.created_at).all()


@router.post("", response_model=TrackResponse, status_code=status.HTTP_201_CREATED)
def create_track(
    body: TrackCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Track:
    track = Track(
        event_id=settings.event_id,
        name=body.name,
        description=body.description,
        created_by_user_id=admin.id,
        modified_by_user_id=admin.id,
    )
    db.add(track)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "track name already in use")
    db.refresh(track)
    return track


@router.delete("/{track_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_track(
    track_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    track = db.get(Track, track_id)
    if not track:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "track not found")
    db.delete(track)
    db.commit()
