from datetime import datetime

from pydantic import BaseModel, Field


class ParticipantBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    affiliation: str | None = Field(None, max_length=200)
    links: list[str] | None = Field(default_factory=list)


class ParticipantCreate(ParticipantBase):
    type: str = Field("human", pattern="^(human|agent|team)$")


class ParticipantUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    affiliation: str | None = Field(None, max_length=200)
    links: list[str] | None = Field(default=None)


class ParticipantMemberInfo(BaseModel):
    user_id: str | None = None
    agent_id: str | None = None
    display_name: str | None = None
    email: str | None = None
    role_in_team: str


class ParticipantResponse(BaseModel):
    id: str
    event_id: str
    type: str
    display_name: str
    affiliation: str | None = None
    links: list[str] | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParticipantPublicResponse(BaseModel):
    id: str
    event_id: str
    type: str
    display_name: str
    affiliation: str | None = None
    status: str
    is_waiting: bool = False
    image: str | None = None

    model_config = {"from_attributes": True}


class RelatedProject(BaseModel):
    id: str
    title: str
    status: str
    track_id: str | None = None


class RelatedTeam(BaseModel):
    id: str
    display_name: str
    role_in_team: str


class TeamMemberPublic(BaseModel):
    """A team member as shown publicly — name, role, and whether the seat is
    held by a human or an autonomous agent. Never the email."""

    display_name: str
    role_in_team: str
    kind: str = "human"  # human|agent


class TeamPublicResponse(ParticipantPublicResponse):
    members: list[TeamMemberPublic] = Field(default_factory=list)


class ParticipantDetailResponse(ParticipantPublicResponse):
    """Public detail: the participant plus what it is bound to — the projects
    it proposed, the teams its people belong to, and (for teams) the roster."""

    projects: list[RelatedProject] = Field(default_factory=list)
    teams: list[RelatedTeam] = Field(default_factory=list)
    members: list[TeamMemberPublic] = Field(default_factory=list)


class TeamCreate(ParticipantBase):
    pass


class TeamResponse(ParticipantResponse):
    invite_code: str
    members: list[ParticipantMemberInfo] = Field(default_factory=list)


class TeamMemberAdd(BaseModel):
    user_id: str
    role_in_team: str = Field("member", pattern="^(captain|member)$")


class TeamAgentAdd(BaseModel):
    agent_id: str


class ParticipantStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|disabled|banned)$")


class ParticipantListResponse(BaseModel):
    participants: list[ParticipantPublicResponse]
    total: int
    page: int
    per_page: int
    pages: int
