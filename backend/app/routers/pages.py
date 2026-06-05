"""Content Page CRUD — admin-authored prose pages."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.middleware.auth import require_admin
from app.models.page import Page
from app.models.user import User
from app.schemas.content import PageCreate, PageResponse, PageUpdate


router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.get("", response_model=list[PageResponse])
def list_pages(
    visible_only: bool = False,
    db: Session = Depends(get_db),
) -> list[Page]:
    q = db.query(Page)
    if visible_only:
        q = q.filter(Page.visible.is_(True))
    return q.order_by(Page.order, Page.created_at).all()


@router.get("/{page_id}", response_model=PageResponse)
def get_page(page_id: str, db: Session = Depends(get_db)) -> Page:
    page = db.get(Page, page_id)
    if not page:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "page not found")
    return page


@router.post("", response_model=PageResponse, status_code=status.HTTP_201_CREATED)
def create_page(
    body: PageCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Page:
    page = Page(
        event_id=settings.event_id,
        title=body.title,
        content=body.content,
        visible=body.visible,
        order=body.order,
        phase_id=body.phase_id,
        created_by_user_id=admin.id,
        modified_by_user_id=admin.id,
    )
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.patch("/{page_id}", response_model=PageResponse)
def update_page(
    page_id: str,
    body: PageUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> Page:
    page = db.get(Page, page_id)
    if not page:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "page not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(page, field, value)
    page.modified_by_user_id = admin.id
    db.commit()
    db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_page(
    page_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> None:
    page = db.get(Page, page_id)
    if not page:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "page not found")
    db.delete(page)
    db.commit()
