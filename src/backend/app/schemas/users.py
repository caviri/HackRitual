from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

VALID_ROLES = {"user", "admin", "judge", "mod"}


class UserDetail(BaseModel):
    id: str
    email: str
    role: str
    status: str
    created_at: datetime
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    users: list[UserDetail]
    total: int
    page: int
    per_page: int


class UpdateRoleInput(BaseModel):
    role: str

    def validate_role(self) -> str:
        if self.role not in VALID_ROLES:
            raise ValueError(f"role must be one of {VALID_ROLES}")
        return self.role


class SetupInput(BaseModel):
    token: str
    email: str
