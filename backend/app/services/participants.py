import secrets
import string
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.user import User
from app.schemas.participants import ParticipantCreate, ParticipantUpdate


def generate_invite_code(length: int = 8) -> str:
    """Generate a URL-safe, case-insensitive invite code."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def get_event_state(db: Session) -> Optional[str]:
    """Get the current event state."""
    event = db.query(Event).first()
    return event.state if event else None


def can_register_participant(event_state: Optional[str]) -> bool:
    """Check if participant registration is allowed."""
    return event_state in ("DRAFT", "OPEN")


def create_solo_participant(
    db: Session,
    user: User,
    data: ParticipantCreate,
    event_id: str,
) -> Participant:
    """Create a solo participant for a user."""
    # Check if user already has a solo participant
    existing = (
        db.query(Participant)
        .join(ParticipantMember)
        .filter(
            ParticipantMember.user_id == user.id,
            Participant.type == "human",
            Participant.status == "active",
        )
        .first()
    )
    if existing:
        raise ValueError("User already has an active solo participant")

    participant = Participant(
        event_id=event_id,
        type=data.type,
        display_name=data.display_name,
        affiliation=data.affiliation,
        links_json=None if not data.links else str(data.links),
        status="active",
    )
    db.add(participant)
    db.flush()

    # Create member link
    member = ParticipantMember(
        participant_id=participant.id,
        user_id=user.id,
        role_in_team="captain",
    )
    db.add(member)
    db.flush()

    return participant


def create_team(
    db: Session,
    user: User,
    display_name: str,
    affiliation: Optional[str],
    links: Optional[list[str]],
    event_id: str,
) -> tuple[Participant, str]:
    """Create a team and return (team, invite_code)."""
    # Generate unique invite code
    invite_code = generate_invite_code()
    while db.query(Participant).filter(Participant.invite_code == invite_code).first():
        invite_code = generate_invite_code()
    
    team = Participant(
        event_id=event_id,
        type="team",
        display_name=display_name,
        affiliation=affiliation,
        links_json=None if not links else str(links),
        invite_code=invite_code,
        status="active",
    )
    db.add(team)
    db.flush()

    member = ParticipantMember(
        participant_id=team.id,
        user_id=user.id,
        role_in_team="captain",
    )
    db.add(member)
    db.flush()

    return team, invite_code


def get_team_by_invite_code(db: Session, invite_code: str) -> Optional[Participant]:
    """Get a team by its invite code (case-insensitive)."""
    team = (
        db.query(Participant)
        .filter(
            Participant.invite_code == invite_code.upper(),
            Participant.type == "team",
            Participant.status == "active",
        )
        .first()
    )
    return team


def join_team(
    db: Session,
    user: User,
    team: Participant,
) -> ParticipantMember:
    """Add a user to a team."""
    # Check if user is already a member
    existing = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.participant_id == team.id,
            ParticipantMember.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise ValueError("User is already a member of this team")

    member = ParticipantMember(
        participant_id=team.id,
        user_id=user.id,
        role_in_team="member",
    )
    db.add(member)
    return member


def get_user_participants(db: Session, user_id: str) -> list[Participant]:
    """Get all participants a user is a member of."""
    result = (
        db.query(Participant)
        .join(ParticipantMember)
        .filter(ParticipantMember.user_id == user_id)
        .all()
    )
    return result


def get_participant_by_id(db: Session, participant_id: str) -> Optional[Participant]:
    """Get a participant by ID."""
    return db.query(Participant).filter(Participant.id == participant_id).first()


def get_team_members(db: Session, team_id: str) -> list[ParticipantMember]:
    """Get all members of a team."""
    return (
        db.query(ParticipantMember)
        .filter(ParticipantMember.participant_id == team_id)
        .all()
    )


def is_team_captain(db: Session, user_id: str, team_id: str) -> bool:
    """Check if a user is the captain of a team."""
    member = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.participant_id == team_id,
            ParticipantMember.user_id == user_id,
            ParticipantMember.role_in_team == "captain",
        )
        .first()
    )
    return member is not None


def is_team_member(db: Session, user_id: str, team_id: str) -> bool:
    """Check if a user is a member of a team."""
    member = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.participant_id == team_id,
            ParticipantMember.user_id == user_id,
        )
        .first()
    )
    return member is not None


def remove_team_member(
    db: Session,
    team_id: str,
    member_id: str,
) -> None:
    """Remove a member from a team."""
    member = db.query(ParticipantMember).filter(
        ParticipantMember.id == member_id,
        ParticipantMember.participant_id == team_id,
    ).first()
    if member:
        db.delete(member)


def regenerate_invite_code(db: Session, team_id: str) -> str:
    """Generate a new invite code for a team."""
    team = db.query(Participant).filter(Participant.id == team_id).first()
    if not team:
        raise ValueError("Team not found")
    
    invite_code = generate_invite_code()
    while db.query(Participant).filter(Participant.invite_code == invite_code).first():
        invite_code = generate_invite_code()
    
    team.invite_code = invite_code
    db.flush()
    return invite_code


def update_participant(
    db: Session,
    participant: Participant,
    data: ParticipantUpdate,
) -> Participant:
    """Update a participant's profile."""
    if data.display_name is not None:
        participant.display_name = data.display_name
    if data.affiliation is not None:
        participant.affiliation = data.affiliation
    if data.links is not None:
        participant.links_json = None if not data.links else str(data.links)
    
    db.flush()
    return participant


def list_participants(
    db: Session,
    event_id: str,
    participant_type: Optional[str] = None,
    status: str = "active",
    page: int = 1,
    per_page: int = 20,
) -> tuple[list[Participant], int]:
    """List participants with pagination and filtering."""
    query = db.query(Participant).filter(
        Participant.event_id == event_id,
        Participant.status == status,
    )
    
    if participant_type:
        query = query.filter(Participant.type == participant_type)
    
    total = query.count()
    offset = (page - 1) * per_page
    participants = query.offset(offset).limit(per_page).all()
    
    return participants, total


def update_participant_status(
    db: Session,
    participant: Participant,
    new_status: str,
) -> Participant:
    """Update a participant's status (admin only)."""
    participant.status = new_status
    db.flush()
    return participant
