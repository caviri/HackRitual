import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.user import User
from app.schemas.participants import (
    ParticipantCreate,
    ParticipantListResponse,
    ParticipantMemberInfo,
    ParticipantPublicResponse,
    ParticipantResponse,
    ParticipantStatusUpdate,
    ParticipantUpdate,
    TeamCreate,
    TeamResponse,
)
from app.services.participants import (
    can_register_participant,
    create_solo_participant,
    create_team,
    get_event_state,
    get_participant_by_id,
    get_team_by_invite_code,
    get_team_members,
    get_user_participants,
    is_team_captain,
    is_team_member,
    join_team,
    list_participants,
    regenerate_invite_code,
    remove_team_member,
    update_participant,
    update_participant_status,
)

router = APIRouter(prefix="/api", tags=["participants"])


def get_event_id(db: Session) -> str:
    """Get the current event ID."""
    from app.config import settings
    
    event = db.query(Participant).first()
    if event:
        return event.event_id
    # Fallback to settings
    return settings.event_id


@router.post("/participants", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
def create_participant(
    data: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a solo participant profile."""
    event_state = get_event_state(db)
    if not can_register_participant(event_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Participant registration is not allowed in {event_state} state",
        )
    
    event_id = get_event_id(db)
    
    try:
        participant = create_solo_participant(db, current_user, data, event_id)
        db.commit()
        db.refresh(participant)
        return participant
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/participants", response_model=ParticipantListResponse)
def list_participants_endpoint(
    type: Optional[str] = Query(None, description="Filter by type (human|agent|team)"),
    status: str = Query("active", description="Filter by status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all active participants (public endpoint)."""
    event_id = get_event_id(db)
    participants, total = list_participants(
        db, event_id, participant_type=type, status=status, page=page, per_page=per_page
    )
    
    pages = (total + per_page - 1) // per_page
    
    return ParticipantListResponse(
        participants=participants,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/participants/me", response_model=Optional[ParticipantResponse])
def get_own_participant(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's participant profile."""
    participants = get_user_participants(db, current_user.id)
    if not participants:
        return None
    # Return the first active participant, or the first one
    for p in participants:
        if p.status == "active":
            return p
    return participants[0]


@router.patch("/participants/me", response_model=ParticipantResponse)
def update_own_participant(
    data: ParticipantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the current user's participant profile."""
    participants = get_user_participants(db, current_user.id)
    if not participants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No participant profile found. Create one first.",
        )
    
    # Get the first active participant
    participant = None
    for p in participants:
        if p.status == "active":
            participant = p
            break
    
    if not participant:
        participant = participants[0]
    
    updated = update_participant(db, participant, data)
    db.commit()
    db.refresh(updated)
    return updated


@router.get("/participants/{participant_id}", response_model=ParticipantPublicResponse)
def get_participant(
    participant_id: str,
    db: Session = Depends(get_db),
):
    """Get public info for any participant."""
    participant = get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    
    return participant


# Team endpoints
@router.post("/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team_endpoint(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new team."""
    event_state = get_event_state(db)
    if not can_register_participant(event_state):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Team creation is not allowed in {event_state} state",
        )
    
    event_id = get_event_id(db)
    
    try:
        team, invite_code = create_team(db, current_user, data.display_name, data.affiliation, data.links, event_id)
        db.commit()
        db.refresh(team)
        
        # Build response with members
        members = get_team_members(db, team.id)
        member_list = []
        for m in members:
            if m.user_id:
                user = db.query(User).filter(User.id == m.user_id).first()
                member_list.append(ParticipantMemberInfo(
                    user_id=m.user_id,
                    display_name=user.email.split('@')[0] if user else "Unknown",
                    email=user.email if user else None,
                    role_in_team=m.role_in_team,
                ))
        
        response = TeamResponse.model_validate(team)
        response.invite_code = invite_code
        response.members = member_list
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/teams/join", response_model=TeamResponse)
def join_team_endpoint(
    invite_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join a team using an invite code."""
    team = get_team_by_invite_code(db, invite_code)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite code or team not found",
        )
    
    try:
        member = join_team(db, current_user, team)
        db.commit()
        db.refresh(team)
        
        # Build response with members
        members = get_team_members(db, team.id)
        member_list = []
        for m in members:
            if m.user_id:
                user = db.query(User).filter(User.id == m.user_id).first()
                member_list.append(ParticipantMemberInfo(
                    user_id=m.user_id,
                    display_name=user.email.split('@')[0] if user else "Unknown",
                    email=user.email if user else None,
                    role_in_team=m.role_in_team,
                ))
        
        response = TeamResponse.model_validate(team)
        response.invite_code = team.invite_code or ""
        response.members = member_list
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/teams/{team_id}/members")
def get_team_members_endpoint(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List team members (requires team membership)."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if not is_team_member(db, current_user.id, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team members can view team members",
        )
    
    members = get_team_members(db, team_id)
    member_list = []
    for m in members:
        if m.user_id:
            user = db.query(User).filter(User.id == m.user_id).first()
            member_list.append(ParticipantMemberInfo(
                user_id=m.user_id,
                display_name=user.email.split('@')[0] if user else "Unknown",
                email=user.email if user else None,
                role_in_team=m.role_in_team,
            ))
    
    return {"team_id": team_id, "members": member_list}


@router.delete("/teams/{team_id}/members/{member_id}")
def remove_member_endpoint(
    team_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a team member (captain only)."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if not is_team_captain(db, current_user.id, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team captain can remove members",
        )
    
    remove_team_member(db, team_id, member_id)
    db.commit()
    
    return {"status": "success", "message": "Member removed"}


@router.post("/teams/{team_id}/leave")
def leave_team_endpoint(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave a team."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if not is_team_member(db, current_user.id, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team",
        )
    
    if is_team_captain(db, current_user.id, team_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captain must transfer leadership before leaving",
        )
    
    # Find and remove the member
    member = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.participant_id == team_id,
            ParticipantMember.user_id == current_user.id,
        )
        .first()
    )
    if member:
        db.delete(member)
        db.commit()
    
    return {"status": "success", "message": "Left team"}


@router.post("/teams/{team_id}/regenerate-invite", response_model=TeamResponse)
def regenerate_invite_endpoint(
    team_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Regenerate team invite code (captain only)."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if not is_team_captain(db, current_user.id, team_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team captain can regenerate the invite code",
        )
    
    try:
        new_code = regenerate_invite_code(db, team_id)
        db.commit()
        db.refresh(team)
        
        # Build response with members
        members = get_team_members(db, team.id)
        member_list = []
        for m in members:
            if m.user_id:
                user = db.query(User).filter(User.id == m.user_id).first()
                member_list.append(ParticipantMemberInfo(
                    user_id=m.user_id,
                    display_name=user.email.split('@')[0] if user else "Unknown",
                    email=user.email if user else None,
                    role_in_team=m.role_in_team,
                ))
        
        response = TeamResponse.model_validate(team)
        response.invite_code = new_code
        response.members = member_list
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Admin endpoints
@router.get("/admin/participants")
def admin_list_participants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: List all participants with full details."""
    participants = db.query(Participant).all()
    return {"participants": participants, "total": len(participants)}


@router.post("/admin/participants", response_model=ParticipantResponse, status_code=status.HTTP_201_CREATED)
def admin_create_participant(
    data: ParticipantCreate,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: Create a participant on behalf of a user."""
    event_id = get_event_id(db)
    
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        participant = create_solo_participant(db, user, data, event_id)
    else:
        # Create without user link (for agents or special cases)
        participant = Participant(
            event_id=event_id,
            type=data.type,
            display_name=data.display_name,
            affiliation=data.affiliation,
            links_json=None if not data.links else str(data.links),
            status="active",
        )
        db.add(participant)
    
    db.commit()
    db.refresh(participant)
    return participant


@router.patch("/admin/participants/{participant_id}/status", response_model=ParticipantResponse)
def admin_update_participant_status(
    participant_id: str,
    data: ParticipantStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: Update participant status (moderation)."""
    participant = get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")
    
    updated = update_participant_status(db, participant, data.status)
    db.commit()
    db.refresh(updated)
    
    # TODO: Log to audit log
    
    return updated


@router.post("/admin/teams/{team_id}/members")
def admin_add_member(
    team_id: str,
    user_id: str,
    role_in_team: str = Query("member", description="Role in team"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin: Add a user to a team."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        member = join_team(db, user, team)
        db.commit()
        return {"status": "success", "member_id": member.id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
