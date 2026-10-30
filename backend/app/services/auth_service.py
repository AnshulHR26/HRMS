"""Authentication business logic: credential checks, lockout, logout, password change."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    BadRequestError,
    UnauthorizedError,
)
from app.core.security import (
    IssuedToken,
    TokenPayload,
    create_access_token,
    hash_password,
    password_needs_rehash,
    verify_password,
)
from app.models import RevokedToken, User

INVALID_CREDENTIALS = "Invalid User ID or password"


def normalise_user_id(user_id: str) -> str:
    return user_id.strip().lower()


def get_user_by_login(db: Session, user_id: str) -> User | None:
    return db.scalar(select(User).where(User.user_id == normalise_user_id(user_id)))


def is_account_usable(user: User) -> bool:
    if not user.is_active:
        return False
    if user.employee is not None and not user.employee.employment_status.is_working:
        return False
    return True


def authenticate(db: Session, user_id: str, password: str) -> User:
    now = datetime.now(UTC)
    user = get_user_by_login(db, user_id)

    if user is None:
        verify_password(password, None)  # equalise timing with the known-user path
        raise UnauthorizedError(INVALID_CREDENTIALS)

    if user.locked_until is not None and user.locked_until > now:
        raise AccountLockedError()

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
            user.locked_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        raise UnauthorizedError(INVALID_CREDENTIALS)

    # Only revealed after a correct password, so it cannot be used to probe accounts.
    if not is_account_usable(user):
        raise AccountInactiveError()

    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


def issue_token(user: User) -> IssuedToken:
    return create_access_token(user_id=user.id, role=user.role.name, token_version=user.token_version)


def logout(db: Session, payload: TokenPayload) -> None:
    """Deny-list the token's jti and purge entries that have expired anyway."""
    now = datetime.now(UTC)
    db.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    if db.get(RevokedToken, payload.jti) is None:
        db.add(RevokedToken(jti=payload.jti, user_id=payload.sub, expires_at=payload.exp))
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise BadRequestError("Current password is incorrect")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    user.token_version += 1  # revokes every session, including the current one
    db.commit()
