from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import _validate_email


class ApplicationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str
    team: str | None = Field(default=None, max_length=80)
    project_interest: str | None = Field(default=None, max_length=2000)

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)

    @field_validator("name", "team")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ApplicationUserOut(BaseModel):
    """The user created on approval — password included for the admin's
    copy/mailto distribution buttons."""

    id: str
    email: str
    display_name: str | None = None
    access_password: str | None = None

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: str
    name: str
    email: str
    team: str | None = None
    project_interest: str | None = None
    status: str
    source: str
    user_id: str | None = None
    created_at: datetime
    decided_at: datetime | None = None
    user: ApplicationUserOut | None = None


class ApplicationCreatedResponse(BaseModel):
    id: str
    status: str


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationOut]
    total: int
    counts: dict[str, int]
