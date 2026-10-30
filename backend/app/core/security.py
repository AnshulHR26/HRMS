"""Password hashing (Argon2id) and JWT (HS256) helpers.

These helpers are pure: they never touch the database. Revocation and
account checks live in ``app.dependencies.authentication``.
"""

import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

_password_hasher = PasswordHasher()  # Argon2id with library-recommended parameters

# Pre-computed hash used to keep login timing similar for unknown user IDs.
_DUMMY_HASH = _password_hasher.hash(secrets.token_urlsafe(16))

PASSWORD_POLICY_MESSAGE = "Password must be 8-128 characters and contain at least one letter and one digit"
_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,128}$")


def validate_password_strength(password: str) -> str:
    if not _PASSWORD_RE.match(password):
        raise ValueError(PASSWORD_POLICY_MESSAGE)
    return password


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    """Constant-ish time verification. ``password_hash=None`` burns a dummy verify."""
    try:
        return _password_hasher.verify(password_hash or _DUMMY_HASH, password) and bool(password_hash)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


@dataclass(frozen=True, slots=True)
class TokenPayload:
    sub: int
    role: str
    jti: str
    ver: int
    iat: datetime
    exp: datetime


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime
    expires_in: int


class TokenError(Exception):
    """Raised for any invalid, expired or malformed token."""


def create_access_token(
    *,
    user_id: int,
    role: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> IssuedToken:
    now = datetime.now(UTC)
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = now + delta
    jti = uuid.uuid4().hex
    claims = {
        "sub": str(user_id),
        "role": role,
        "jti": jti,
        "ver": token_version,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return IssuedToken(
        token=token,
        jti=jti,
        expires_at=expires_at,
        expires_in=int(delta.total_seconds()),
    )


def decode_access_token(token: str) -> TokenPayload:
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],  # pinned: blocks alg=none / alg confusion
            options={"require": ["sub", "jti", "exp", "iat", "ver", "role"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc

    if claims.get("type") != "access":
        raise TokenError("Invalid token type")
    try:
        return TokenPayload(
            sub=int(claims["sub"]),
            role=str(claims["role"]),
            jti=str(claims["jti"]),
            ver=int(claims["ver"]),
            iat=datetime.fromtimestamp(claims["iat"], UTC),
            exp=datetime.fromtimestamp(claims["exp"], UTC),
        )
    except (TypeError, ValueError) as exc:
        raise TokenError("Invalid token claims") from exc


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
