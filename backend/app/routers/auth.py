from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.core.security import generate_csrf_token
from app.dependencies.authentication import CurrentAuth, CurrentUser
from app.dependencies.database import DbSession
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenResponse
from app.schemas.common import ERROR_RESPONSES, ErrorResponse
from app.schemas.user import UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _set_auth_cookies(response: Response, token: str, max_age: int) -> None:
    common = {
        "max_age": max_age,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    # httpOnly: JavaScript (and therefore XSS payloads) cannot read the JWT.
    response.set_cookie(settings.COOKIE_NAME, token, httponly=True, **common)
    # Readable by the SPA so it can echo it in the X-CSRF-Token header (double submit).
    response.set_cookie(settings.CSRF_COOKIE_NAME, generate_csrf_token(), httponly=False, **common)


def _clear_auth_cookies(response: Response) -> None:
    for name in (settings.COOKIE_NAME, settings.CSRF_COOKIE_NAME):
        response.delete_cookie(name, path="/", secure=settings.COOKIE_SECURE, samesite=settings.COOKIE_SAMESITE)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Sign in with User ID and password",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid User ID or password"},
        403: {"model": ErrorResponse, "description": "Account inactive or temporarily locked"},
        422: ERROR_RESPONSES[422],
    },
)
def login(payload: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    user = auth_service.authenticate(db, payload.user_id, payload.password)
    issued = auth_service.issue_token(user)
    _set_auth_cookies(response, issued.token, issued.expires_in)
    return TokenResponse(
        access_token=issued.token,
        expires_in=issued.expires_in,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse, responses={401: ERROR_RESPONSES[401]})
def me(user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current token and clear cookies",
    responses={401: ERROR_RESPONSES[401]},
)
def logout(auth: CurrentAuth, response: Response, db: DbSession) -> None:
    auth_service.logout(db, auth.token)
    _clear_auth_cookies(response)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change own password (signs out every session)",
    responses={400: {"model": ErrorResponse}, **ERROR_RESPONSES},
)
def change_password(payload: ChangePasswordRequest, user: CurrentUser, response: Response, db: DbSession) -> None:
    auth_service.change_password(db, user, payload.current_password, payload.new_password)
    _clear_auth_cookies(response)
