"""
CSV bulk import — many petitions granted at once.

The keeper uploads a CSV (`name,email,team,project` header; team and project
optional) and each valid row becomes an approved Application plus a User with
a generated access password. Rows sharing a team value are gathered into a
team Participant (first member is captain). Existing emails are skipped and
reported, bad rows are collected as errors — one poisoned row never aborts
the batch.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.participant import Participant
from app.models.user import User
from app.schemas.auth import _EMAIL_RE
from app.services.applications import approve_application
from app.services.audit import log_action

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("name", "email")
KNOWN_COLUMNS = ("name", "email", "team", "project")

MAX_FILE_BYTES = 1024 * 1024  # 1 MB — thousands of rows, far beyond any event


class CsvFormatError(Exception):
    """Raised when the file as a whole is unusable (bad headers, too big)."""


@dataclass
class ImportReport:
    created: list[dict] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)


def _parse_rows(raw: bytes) -> list[dict]:
    """Decode and parse the CSV, normalising headers. Raises CsvFormatError."""
    if len(raw) > MAX_FILE_BYTES:
        raise CsvFormatError("File too large (max 1 MB).")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CsvFormatError("File must be UTF-8 encoded.")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise CsvFormatError("Empty file.")

    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [c for c in REQUIRED_COLUMNS if c not in headers]
    if missing:
        raise CsvFormatError(
            f"Missing required column(s): {', '.join(missing)}. "
            f"Expected header: name,email,team,project"
        )

    rows = []
    for row in reader:
        rows.append(
            {
                (k or "").strip().lower(): (v or "").strip()
                for k, v in row.items()
                if k is not None
            }
        )
    return rows


def _team_for(db: Session, event_id: str, team_name: str, cache: dict) -> Participant:
    """Find or create the active team Participant with this display name."""
    from app.services.participants import generate_invite_code

    key = team_name.lower()
    if key in cache:
        return cache[key]

    team = (
        db.query(Participant)
        .filter(
            Participant.event_id == event_id,
            Participant.type == "team",
            Participant.status == "active",
            Participant.display_name == team_name,
        )
        .first()
    )
    if team is None:
        invite_code = generate_invite_code()
        while db.query(Participant).filter(Participant.invite_code == invite_code).first():
            invite_code = generate_invite_code()
        team = Participant(
            event_id=event_id,
            type="team",
            display_name=team_name,
            invite_code=invite_code,
            status="active",
        )
        db.add(team)
        db.flush()
    cache[key] = team
    return team


def import_csv(db: Session, raw: bytes, *, admin_id: str, event_id: str) -> ImportReport:
    """Run the import. Commits once at the end. Raises CsvFormatError only
    for whole-file problems; per-row trouble lands in the report."""
    from app.models.participant_member import ParticipantMember

    rows = _parse_rows(raw)
    report = ImportReport()
    team_cache: dict[str, Participant] = {}

    for index, row in enumerate(rows, start=2):  # header is line 1
        name = row.get("name", "")
        email = row.get("email", "").lower()
        team_name = row.get("team", "")
        project = row.get("project", "")

        if not name and not email:
            continue  # blank line
        if not name:
            report.errors.append({"row": index, "reason": "missing name"})
            continue
        if not email or not _EMAIL_RE.match(email):
            report.errors.append({"row": index, "reason": f"invalid email '{email}'"})
            continue

        if db.query(User).filter(User.email == email).first():
            report.skipped.append({"row": index, "email": email, "reason": "user already exists"})
            continue
        if db.query(Application).filter(Application.email == email).first():
            report.skipped.append(
                {"row": index, "email": email, "reason": "application already exists"}
            )
            continue

        application = Application(
            name=name,
            email=email,
            team=team_name or None,
            project_interest=project or None,
            status="pending",
            source="import",
        )
        db.add(application)
        db.flush()
        approve_application(db, application, decided_by=admin_id)

        user = db.get(User, application.user_id)

        if team_name:
            team = _team_for(db, event_id, team_name, team_cache)
            already_member = (
                db.query(ParticipantMember)
                .filter(
                    ParticipantMember.participant_id == team.id,
                    ParticipantMember.user_id == user.id,
                )
                .first()
            )
            if not already_member:
                first_member = (
                    db.query(ParticipantMember)
                    .filter(ParticipantMember.participant_id == team.id)
                    .first()
                    is None
                )
                db.add(
                    ParticipantMember(
                        participant_id=team.id,
                        user_id=user.id,
                        role_in_team="captain" if first_member else "member",
                    )
                )
                db.flush()

        report.created.append(
            {
                "application_id": application.id,
                "user_id": user.id,
                "name": name,
                "email": email,
                "team": team_name or None,
                "access_password": user.access_password,
            }
        )

    log_action(
        db,
        "users.csv_imported",
        actor_id=admin_id,
        metadata={
            "created": len(report.created),
            "skipped": len(report.skipped),
            "errors": len(report.errors),
        },
    )
    db.commit()
    return report
