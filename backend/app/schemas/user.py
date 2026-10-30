from datetime import datetime
from typing import Annotated

from pydantic import AliasChoices, Field, field_validator

from app.core.roles import RoleName
from app.core.security import validate_password_strength
from app.schemas.common import ORMModel, StrictInput

# Login identifiers: letters, digits, dot, underscore, hyphen.
UserIdStr = Annotated[
    str,
    Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9._-]+$", examples=["jane.doe"]),
]
PasswordStr = Annotated[str, Field(min_length=8, max_length=128)]


class EmployeeLink(ORMModel):
    id: int
    employee_id: str
    full_name: str


class UserResponse(ORMModel):
    """Never contains password_hash, token_version or lockout internals."""

    id: int
    user_id: str
    role: RoleName = Field(validation_alias=AliasChoices("role_name", "role"))
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    employee: EmployeeLink | None = None


class UserCreate(StrictInput):
    user_id: UserIdStr
    password: PasswordStr
    role: RoleName = RoleName.EMPLOYEE
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserUpdate(StrictInput):
    user_id: UserIdStr


class UserRoleUpdate(StrictInput):
    role: RoleName


class UserStatusUpdate(StrictInput):
    is_active: bool


class PasswordReset(StrictInput):
    new_password: PasswordStr

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)
