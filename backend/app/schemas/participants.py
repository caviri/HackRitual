from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ParticipantBase(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    affiliation: Optional[str] = Field(None, max_length=200)
    links: Optional[list[str]] = Field(default_factory=list)


class ParticipantCreate(ParticipantBase):
    type: str = Field("human", pattern="^(human|agent|team)$")


class ParticipantUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    affiliation: Optional[str] = Field(None, max_length=200)
    links: Optional[list[str]] = Field(default=None)


class ParticipantMemberInfo(BaseModel):
    user_id: Optional[str] = None
    display_name: Optional[str] = None
    email: Optional[str] = None
    role_in_team: str


class ParticipantResponse(BaseModel):
    id: str
    event_id: str
    type: str
    display_name: str
    affiliation: Optional[str] = None
    links: Optional[list[str]] = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ParticipantPublicResponse(BaseModel):
    id: str
    event_id: str
    type: str
    display_name: str
    affiliation: Optional[str] = None
    status: str
    is_waiting: bool = False

    model_config = {"from_attributes": True}


class TeamCreate(ParticipantBase):
    pass


class TeamResponse(ParticipantResponse):
    invite_code: str
    members: list[ParticipantMemberInfo] = Field(default_factory=list)


class TeamMemberAdd(BaseModel):
    user_id: str
    role_in_team: str = Field("member", pattern="^(captain|member)$")


class ParticipantStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|disabled|banned)$")


class ParticipantListResponse(BaseModel):
    participants: list[ParticipantPublicResponse]
    total: int
    page: int
    per_page: int
    pages: int
