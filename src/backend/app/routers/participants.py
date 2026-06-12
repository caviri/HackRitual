from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_user, require_admin
from app.models.agent import Agent
from app.models.participant import Participant
from app.models.participant_member import ParticipantMember
from app.models.user import User
from app.schemas.participants import (
    ParticipantCreate,
    ParticipantDetailResponse,
    ParticipantListResponse,
    ParticipantMemberInfo,
    ParticipantResponse,
    ParticipantStatusUpdate,
    ParticipantUpdate,
    RelatedProject,
    RelatedTeam,
    TeamAgentAdd,
    TeamCreate,
    TeamMemberPublic,
    TeamPublicResponse,
    TeamResponse,
)
from app.services.audit import log_action
from app.services.participants import (
    add_agent_to_team,
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


def _member_public(db: Session, m: ParticipantMember) -> TeamMemberPublic | None:
    """A membership row's public face — a user's display name or an agent's
    name, plus which kind holds the seat. Rows whose account is gone → None."""
    if m.user_id:
        user = db.get(User, m.user_id)
        if user is None:
            return None
        return TeamMemberPublic(
            display_name=user.display_name or "anonymous",
            role_in_team=m.role_in_team,
            kind="human",
        )
    if m.agent_id:
        agent = db.get(Agent, m.agent_id)
        if agent is None:
            return None
        return TeamMemberPublic(
            display_name=agent.name,
            role_in_team=m.role_in_team,
            kind="agent",
        )
    return None


def _member_info(db: Session, m: ParticipantMember) -> ParticipantMemberInfo | None:
    """A membership row's authenticated view — email for humans, never for
    agents (they have none)."""
    if m.user_id:
        user = db.get(User, m.user_id)
        return ParticipantMemberInfo(
            user_id=m.user_id,
            display_name=user.email.split("@")[0] if user else "Unknown",
            email=user.email if user else None,
            role_in_team=m.role_in_team,
        )
    if m.agent_id:
        agent = db.get(Agent, m.agent_id)
        return ParticipantMemberInfo(
            agent_id=m.agent_id,
            display_name=agent.name if agent else "Unknown agent",
            role_in_team=m.role_in_team,
        )
    return None


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
        log_action(db, "participant.registered", actor_id=current_user.id,
                   target_type="participant", target_id=participant.id,
                   metadata={"handle": participant.display_name})
        db.commit()
        db.refresh(participant)
        return participant
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/participants", response_model=ParticipantListResponse)
def list_participants_endpoint(
    type: str | None = Query(None, description="Filter by type (human|agent|team)"),
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


@router.get("/participants/me", response_model=ParticipantResponse | None)
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


@router.get("/participants/{participant_id}", response_model=ParticipantDetailResponse)
def get_participant(
    participant_id: str,
    db: Session = Depends(get_db),
):
    """Public detail for any participant, with what it is bound to: proposed
    projects, the teams its people belong to, and (for teams) the roster."""
    from app.models.participant import Participant
    from app.models.participant_member import ParticipantMember
    from app.models.project import Project

    participant = get_participant_by_id(db, participant_id)
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant not found")

    response = ParticipantDetailResponse.model_validate(participant)

    response.projects = [
        RelatedProject(id=p.id, title=p.title, status=p.status, track_id=p.track_id)
        for p in (
            db.query(Project)
            .filter(Project.proposed_by_participant_id == participant.id)
            .order_by(Project.created_at)
            .all()
        )
    ]

    member_rows = get_team_members(db, participant.id)
    user_ids = [m.user_id for m in member_rows if m.user_id is not None]
    agent_ids = [m.agent_id for m in member_rows if m.agent_id is not None]
    if participant.type == "team":
        for m in member_rows:
            info = _member_public(db, m)
            if info is not None:
                response.members.append(info)
    elif user_ids or agent_ids:
        from sqlalchemy import or_

        # The teams this participant's people — or its agent credential —
        # belong to.
        membership_of_ours = []
        if user_ids:
            membership_of_ours.append(ParticipantMember.user_id.in_(user_ids))
        if agent_ids:
            membership_of_ours.append(ParticipantMember.agent_id.in_(agent_ids))
        rows = (
            db.query(Participant, ParticipantMember)
            .join(ParticipantMember, ParticipantMember.participant_id == Participant.id)
            .filter(
                or_(*membership_of_ours),
                Participant.type == "team",
                Participant.status == "active",
                Participant.id != participant.id,
            )
            .all()
        )
        seen: set[str] = set()
        for team, membership in rows:
            if team.id in seen:
                continue
            seen.add(team.id)
            response.teams.append(
                RelatedTeam(
                    id=team.id,
                    display_name=team.display_name,
                    role_in_team=membership.role_in_team,
                )
            )

    return response


# Team endpoints
@router.get("/teams", response_model=list[TeamPublicResponse])
def list_teams(db: Session = Depends(get_db)) -> list[TeamPublicResponse]:
    """Public team roster: every active team with its members by display
    name and role. No emails, no invite codes."""
    from app.models.participant import Participant

    event_id = get_event_id(db)
    teams = (
        db.query(Participant)
        .filter(
            Participant.event_id == event_id,
            Participant.type == "team",
            Participant.status == "active",
        )
        .order_by(Participant.created_at)
        .all()
    )
    out: list[TeamPublicResponse] = []
    for team in teams:
        response = TeamPublicResponse.model_validate(team)
        for m in get_team_members(db, team.id):
            info = _member_public(db, m)
            if info is not None:
                response.members.append(info)
        out.append(response)
    return out


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
        log_action(db, "team.formed", actor_id=current_user.id,
                   target_type="participant", target_id=team.id,
                   metadata={"handle": team.display_name})
        db.commit()
        db.refresh(team)
        
        # Build response with members
        member_list = [
            info
            for m in get_team_members(db, team.id)
            if (info := _member_info(db, m)) is not None
        ]

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
        join_team(db, current_user, team)
        log_action(db, "team.joined", actor_id=current_user.id,
                   target_type="participant", target_id=team.id,
                   metadata={"handle": team.display_name})
        db.commit()
        db.refresh(team)
        
        # Build response with members
        member_list = [
            info
            for m in get_team_members(db, team.id)
            if (info := _member_info(db, m)) is not None
        ]

        response = TeamResponse.model_validate(team)
        response.invite_code = team.invite_code or ""
        response.members = member_list
        return response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/teams/{team_id}/agents", status_code=status.HTTP_201_CREATED)
def enlist_agent_endpoint(
    team_id: str,
    data: TeamAgentAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enlist an agent into a team. The caller must be a member of the team
    AND own the agent — consent travels with the credential. Admins may
    enlist any active agent anywhere. Removal goes through the ordinary
    captain-only member removal."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    agent = db.get(Agent, data.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A revoked agent cannot join a team",
        )

    if current_user.role != "admin":
        if not is_team_member(db, current_user.id, team_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team members can enlist an agent",
            )
        if agent.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only enlist an agent you own",
            )

    try:
        member = add_agent_to_team(db, agent.id, team)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    log_action(db, "team.agent_enlisted", actor_id=current_user.id,
               target_type="participant", target_id=team.id,
               metadata={"handle": team.display_name, "agent": agent.name})
    db.commit()
    return {"status": "success", "member_id": member.id}


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
    
    member_list = [
        info
        for m in get_team_members(db, team_id)
        if (info := _member_info(db, m)) is not None
    ]

    return {"team_id": team_id, "members": member_list}


@router.delete("/teams/{team_id}/members/{member_id}")
def remove_member_endpoint(
    team_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a team member. Captains and admins may remove anyone; the
    owner of an enlisted agent may pull their own agent's seat."""
    team = get_participant_by_id(db, team_id)
    if not team or team.type != "team":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    member = (
        db.query(ParticipantMember)
        .filter(
            ParticipantMember.id == member_id,
            ParticipantMember.participant_id == team_id,
        )
        .first()
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    allowed = current_user.role == "admin" or is_team_captain(db, current_user.id, team_id)
    if not allowed and member.agent_id is not None:
        agent = db.get(Agent, member.agent_id)
        allowed = agent is not None and agent.owner_user_id == current_user.id
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team captain (or the agent's owner) can remove members",
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
        member_list = [
            info
            for m in get_team_members(db, team.id)
            if (info := _member_info(db, m)) is not None
        ]

        response = TeamResponse.model_validate(team)
        response.invite_code = new_code
        response.members = member_list
        log_action(db, "team.invite_regenerated", actor_id=current_user.id,
                   target_type="participant", target_id=team.id,
                   metadata={"handle": team.display_name})
        db.commit()
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
    user_id: str | None = None,
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
