from __future__ import annotations

import re

from pydantic import BaseModel, field_validator

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Invalid email address")
    return v


class RequestCodeInput(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)


class VerifyCodeInput(BaseModel):
    email: str
    code: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return _validate_email(v)


class UserOut(BaseModel):
    id: str
    email: str
    role: str

    model_config = {"from_attributes": True}


class PortraitInfo(BaseModel):
    """The user's portrait — dithered/halftoned face. None if not uploaded yet."""

    url: str | None = None
    effect: str | None = None
    contrast: float | None = None
    brightness: int | None = None
    scale: float | None = None


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    display_name: str | None = None
    participant: dict | None = None
    portrait: PortraitInfo | None = None

    model_config = {"from_attributes": True}


class VerifyCodeResponse(BaseModel):
    user: UserOut
