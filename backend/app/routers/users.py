from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.roles import RoleName
from app.dependencies.authorization import AdminUser, HRorAdminUser
from app.dependencies.database import DbSession
from app.schemas.common import ERROR_RESPONSES, ErrorResponse, Page
from app.schemas.user import (
    PasswordReset,
    UserCreate,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["User Management"], responses=ERROR_RESPONSES)


@router.get("", response_model=Page[UserResponse], summary="List user accounts")
def list_users(
    actor: HRorAdminUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
    role: RoleName | None = None,
    is_active: bool | None = None,
) -> Page[UserResponse]:
    result = user_service.list_users(
        db, actor, page=page, page_size=page_size, search=search, role=role, is_active=is_active
    )
    return Page[UserResponse].model_validate(result, from_attributes=True)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def create_user(payload: UserCreate, actor: HRorAdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(user_service.create_user(db, actor, payload))


@router.get("/{user_pk}", response_model=UserResponse, responses={404: {"model": ErrorResponse}})
def get_user(user_pk: int, actor: HRorAdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(user_service.get_user(db, actor, user_pk))


@router.patch("/{user_pk}", response_model=UserResponse, summary="Change the login User ID")
def update_user(user_pk: int, payload: UserUpdate, actor: HRorAdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(user_service.rename_user(db, actor, user_pk, payload.user_id))


@router.patch("/{user_pk}/role", response_model=UserResponse, summary="Assign a role (Admin only)")
def change_role(user_pk: int, payload: UserRoleUpdate, actor: AdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(user_service.change_role(db, actor, user_pk, payload.role))


@router.patch("/{user_pk}/status", response_model=UserResponse, summary="Activate / deactivate")
def change_status(user_pk: int, payload: UserStatusUpdate, actor: HRorAdminUser, db: DbSession) -> UserResponse:
    return UserResponse.model_validate(user_service.set_active(db, actor, user_pk, payload.is_active))


@router.post(
    "/{user_pk}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a new password and sign the user out everywhere",
)
def reset_password(user_pk: int, payload: PasswordReset, actor: HRorAdminUser, db: DbSession) -> None:
    user_service.reset_password(db, actor, user_pk, payload.new_password)
