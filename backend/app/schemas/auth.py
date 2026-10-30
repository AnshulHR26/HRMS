from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.security import validate_password_strength
from app.schemas.common import StrictInput
from app.schemas.user import UserResponse


class LoginRequest(StrictInput):
    user_id: str = Field(min_length=1, max_length=50, examples=["admin"])
    password: str = Field(min_length=1, max_length=128, examples=["********"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the access token expires")
    user: UserResponse


class ChangePasswordRequest(StrictInput):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @model_validator(mode="after")
    def must_differ(self) -> "ChangePasswordRequest":
        if self.current_password == self.new_password:
            raise ValueError("New password must be different from the current password")
        return self
