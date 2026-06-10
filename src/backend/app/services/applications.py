"""
Applications service — the petition desk.

Public visitors file an application; the keeper approves or rejects. Approval
mints a User with a generated access password, which the admin then delivers
by hand (copy/mailto in the panel). CSV imports reuse the same machinery with
`source="import"` and immediate approval.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.user import User
from app.services.audit import log_action
from app.services.passwords import generate_unique_password

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """Raised on conflicts (duplicate email, already decided)."""


def create_application(
    db: Session,
    *,
    name: str,
    email: str,
    team: str | None = None,
    project_interest: str | None = None,
    source: str = "form",
) -> Application:
    """File a new pending application. Raises ApplicationError on duplicates."""
    email = email.strip().lower()

    if db.query(Application).filter(Application.email == email).first():
        raise ApplicationError("An application with this email already exists.")
    if db.query(User).filter(User.email == email).first():
        raise ApplicationError("A user with this email already exists.")

    application = Application(
        name=name.strip(),
        email=email,
        team=(team or "").strip() or None,
        project_interest=(project_interest or "").strip() or None,
        status="pending",
        source=source,
    )
    db.add(application)
    db.flush()
    return application


def approve_application(
    db: Session,
    application: Application,
    *,
    decided_by: str | None = None,
) -> Application:
    """Approve a pending application: create the User + access password.

    Flushes but does not commit — caller owns the transaction.
    Raises ApplicationError if already decided or the email collided since.
    """
    if application.status != "pending":
        raise ApplicationError(f"Application is already {application.status}.")
    if db.query(User).filter(User.email == application.email).first():
        raise ApplicationError("A user with this email already exists.")

    user = User(
        email=application.email,
        display_name=application.name,
        role="user",
        access_password=generate_unique_password(db),
    )
    db.add(user)
    db.flush()

    application.status = "approved"
    application.user_id = user.id
    application.decided_by = decided_by
    application.decided_at = datetime.now(UTC)

    log_action(
        db,
        "application.approved",
        actor_id=decided_by,
        target_type="application",
        target_id=application.id,
        metadata={"user_id": user.id},
    )
    return application


def reject_application(
    db: Session,
    application: Application,
    *,
    decided_by: str | None = None,
) -> Application:
    """Reject a pending application. Flushes but does not commit."""
    if application.status != "pending":
        raise ApplicationError(f"Application is already {application.status}.")

    application.status = "rejected"
    application.decided_by = decided_by
    application.decided_at = datetime.now(UTC)

    log_action(
        db,
        "application.rejected",
        actor_id=decided_by,
        target_type="application",
        target_id=application.id,
    )
    return application
