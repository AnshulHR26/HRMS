"""Authentication dependencies.

Token sources, in order:
1. ``Authorization: Bearer <jwt>`` — Swagger UI and API clients.
2. ``hrms_access_token`` httpOnly cookie — the React SPA.

Cookie-authenticated requests with an unsafe method must also send the CSRF
double-submit header (``X-CSRF-Token`` equal to the ``hrms_csrf`` cookie).
"""

import hmac
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import AccountInactiveError, ForbiddenError, UnauthorizedError
from app.core.security import TokenError, TokenPayload, decode_access_token
from app.dependencies.database import DbSession
from app.models import RevokedToken, User

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Paste the access_token returned by POST /api/v1/auth/login",
)

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    token: TokenPayload


def get_token_payload(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> TokenPayload:
    raw_token: str | None = None
    from_cookie = False
    if credentials is not None and credentials.scheme.lower() == "bearer":
        raw_token = credentials.credentials
    else:
        raw_token = request.cookies.get(settings.COOKIE_NAME)
        from_cookie = raw_token is not None

    if not raw_token:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_access_token(raw_token)
    except TokenError as exc:
        raise UnauthorizedError(str(exc)) from exc

    if from_cookie and request.method not in _SAFE_METHODS:
        cookie_csrf = request.cookies.get(settings.CSRF_COOKIE_NAME, "")
        header_csrf = request.headers.get(settings.CSRF_HEADER_NAME, "")
        if not cookie_csrf or not hmac.compare_digest(cookie_csrf, header_csrf):
            raise ForbiddenError("CSRF token missing or invalid")

    return payload


def get_auth_context(
    db: DbSession,
    payload: Annotated[TokenPayload, Depends(get_token_payload)],
) -> AuthContext:
    if db.get(RevokedToken, payload.jti) is not None:
        raise UnauthorizedError("Token has been revoked")

    user = db.get(User, payload.sub)
    if user is None:
        raise UnauthorizedError("Invalid token")
    if user.token_version != payload.ver:
        raise UnauthorizedError("Token is no longer valid. Please sign in again.")
    if not user.is_active:
        raise AccountInactiveError()
    # Note: login lockout (failed attempts) intentionally does not end existing sessions —
    # otherwise anyone could log a user out by mistyping their password five times.
    return AuthContext(user=user, token=payload)


def get_current_user(auth: Annotated[AuthContext, Depends(get_auth_context)]) -> User:
    return auth.user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAuth = Annotated[AuthContext, Depends(get_auth_context)]
