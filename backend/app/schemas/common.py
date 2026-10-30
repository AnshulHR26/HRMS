from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models built from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class StrictInput(BaseModel):
    """Base for request bodies: unknown fields are rejected (blocks mass assignment)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(ge=0)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class MessageResponse(BaseModel):
    message: str


# Documented in OpenAPI for every router.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Missing, invalid, expired or revoked token"},
    403: {"model": ErrorResponse, "description": "Authenticated but not permitted"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}
