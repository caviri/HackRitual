"""
Event notifications — the messages the ritual sends of its own accord.

Optional emails for the moments that matter: a phase advancing, an offering
received, a score available. Templates are plain strings (no engine needed at
MVP-1); dispatch goes through `email.send_email`, which is console-safe and
records aggregate metrics. None of this blocks the request — callers schedule it
via FastAPI `BackgroundTasks`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.submission import Submission
from app.models.user import User
from app.services.email import send_email

# Human-readable gloss for each ritual state.
_STATE_MESSAGE = {
    "DRAFT": "The circle is being drawn.",
    "OPEN": "The gates are open — submissions and registration are live.",
    "FROZEN": "The forge has cooled — submissions are closed; scoring continues.",
    "FINAL": "The verdict is inscribed — results are final.",
    "ARCHIVED": "The ritual is complete and the record sealed.",
}


# --------------------------------------------------------------------------- #
# Templates — each returns (subject, html, text)
# --------------------------------------------------------------------------- #
def phase_change_email(event_title: str, new_state: str) -> tuple[str, str, str]:
    desc = _STATE_MESSAGE.get(new_state, "")
    subject = f"{event_title} — now {new_state}"
    text = f"The ritual has moved to {new_state}.\n{desc}\n"
    html = (
        f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">'
        f"<h2>{event_title}</h2>"
        f"<p>The ritual has moved to <strong>{new_state}</strong>.</p>"
        f"<p>{desc}</p></div>"
    )
    return subject, html, text


def submission_received_email(
    event_title: str, title: str, status: str
) -> tuple[str, str, str]:
    subject = f"Submission received — {event_title}"
    text = f'Your submission "{title}" has been received.\nStatus: {status}\n'
    html = (
        f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">'
        f"<h2>Submission received</h2>"
        f'<p>Your submission "<strong>{title}</strong>" has been received.</p>'
        f"<p>Status: {status}</p></div>"
    )
    return subject, html, text


def score_available_email(
    event_title: str, title: str, score: float
) -> tuple[str, str, str]:
    subject = f"Score available — {event_title}"
    text = f'Your submission "{title}" has been scored.\nScore: {score}\n'
    html = (
        f'<div style="font-family:sans-serif;max-width:480px;margin:0 auto;">'
        f"<h2>Score available</h2>"
        f'<p>Your submission "<strong>{title}</strong>" has been scored.</p>'
        f"<p>Score: <strong>{score}</strong></p></div>"
    )
    return subject, html, text


# --------------------------------------------------------------------------- #
# Recipient resolution
# --------------------------------------------------------------------------- #
def event_recipient_emails(db: Session, event_id: str) -> list[str]:
    """Distinct emails of the humans behind a participant in the event."""
    rows = (
        db.query(User.email)
        .join(ParticipantMember, ParticipantMember.user_id == User.id)
        .join(Participant, Participant.id == ParticipantMember.participant_id)
        .filter(Participant.event_id == event_id)
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]


def participant_emails(db: Session, participant_id: str) -> list[str]:
    rows = (
        db.query(User.email)
        .join(ParticipantMember, ParticipantMember.user_id == User.id)
        .filter(ParticipantMember.participant_id == participant_id)
        .distinct()
        .all()
    )
    return [r[0] for r in rows if r[0]]


# --------------------------------------------------------------------------- #
# Notify helpers — schedule sends onto a BackgroundTasks instance
# --------------------------------------------------------------------------- #
def notify_phase_change(background, db: Session, event: Event) -> int:
    """Queue a phase-change notice to everyone in the event. Returns recipient count."""
    subject, html, text = phase_change_email(event.title, event.state)
    recipients = event_recipient_emails(db, event.id)
    for to in recipients:
        background.add_task(send_email, to, subject, html, text)
    return len(recipients)


def notify_submission_received(background, db: Session, submission: Submission) -> int:
    """Queue a submission-received notice to the submitting participant."""
    from app.config import settings

    subject, html, text = submission_received_email(
        settings.event_title, submission.title or "(untitled)", submission.status
    )
    recipients = participant_emails(db, submission.participant_id)
    for to in recipients:
        background.add_task(send_email, to, subject, html, text)
    return len(recipients)
