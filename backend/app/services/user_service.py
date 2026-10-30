"""User-account administration with privilege-escalation guards.

Policy
------
* ADMIN may manage every account and assign any role.
* HR may only see and manage accounts whose role is EMPLOYEE, may only create
  EMPLOYEE accounts and can never change roles.
* Nobody may change their own role or deactivate themselves, and the last
  active ADMIN can never be demoted or deactivated.
"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.roles import RoleName
from app.core.security import hash_password
from app.models import Role, User
from app.models.employee import Employee
from app.schemas.user import UserCreate
from app.services.auth_service import normalise_user_id
from app.utils.pagination import like_pattern, paginate

HR_SCOPE_MESSAGE = "HR users can only manage EMPLOYEE accounts"


def is_admin(user: User) -> bool:
    return user.role.name == RoleName.ADMIN


def get_role(db: Session, name: RoleName) -> Role:
    role = db.scalar(select(Role).where(Role.name == name.value))
    if role is None:  # roles are seeded by the initial migration
        raise NotFoundError(f"Role {name} is not configured")
    return role


def ensure_can_assign_role(actor: User, role: RoleName) -> None:
    if not is_admin(actor) and role != RoleName.EMPLOYEE:
        raise ForbiddenError("Only an ADMIN can create or assign HR and ADMIN accounts")


def ensure_can_manage(actor: User, target: User) -> None:
    if is_admin(actor):
        return
    if target.role.name != RoleName.EMPLOYEE:
        raise ForbiddenError(HR_SCOPE_MESSAGE)


def ensure_user_id_available(db: Session, user_id: str, *, exclude_id: int | None = None) -> None:
    stmt = select(User.id).where(User.user_id == user_id)
    if exclude_id is not None:
        stmt = stmt.where(User.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"User ID '{user_id}' is already taken")


def _active_admin_count(db: Session) -> int:
    return (
        db.scalar(
            select(func.count(User.id)).join(Role).where(Role.name == RoleName.ADMIN.value, User.is_active.is_(True))
        )
        or 0
    )


def ensure_not_last_admin(db: Session, target: User) -> None:
    if is_admin(target) and target.is_active and _active_admin_count(db) <= 1:
        raise ConflictError("The last active ADMIN account cannot be demoted or deactivated")


def list_users(
    db: Session,
    actor: User,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    role: RoleName | None = None,
    is_active: bool | None = None,
) -> dict[str, Any]:
    stmt = select(User).join(Role).outerjoin(Employee, Employee.user_id == User.id)
    if not is_admin(actor):
        stmt = stmt.where(Role.name == RoleName.EMPLOYEE.value)
    if role is not None:
        stmt = stmt.where(Role.name == role.value)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))
    if search:
        pattern = like_pattern(search.strip())
        stmt = stmt.where(
            or_(
                User.user_id.ilike(pattern, escape="\\"),
                Employee.full_name.ilike(pattern, escape="\\"),
                Employee.employee_id.ilike(pattern, escape="\\"),
            )
        )
    stmt = stmt.order_by(User.created_at.desc(), User.id.desc())
    return paginate(db, stmt, page, page_size)


def get_user(db: Session, actor: User, user_pk: int) -> User:
    user = db.get(User, user_pk)
    if user is None:
        raise NotFoundError("User not found")
    ensure_can_manage(actor, user)
    return user


def create_user(db: Session, actor: User, data: UserCreate) -> User:
    ensure_can_assign_role(actor, data.role)
    login = normalise_user_id(data.user_id)
    ensure_user_id_available(db, login)
    user = User(
        user_id=login,
        password_hash=hash_password(data.password),
        role=get_role(db, data.role),
        is_active=data.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def rename_user(db: Session, actor: User, user_pk: int, new_user_id: str) -> User:
    user = get_user(db, actor, user_pk)
    login = normalise_user_id(new_user_id)
    ensure_user_id_available(db, login, exclude_id=user.id)
    user.user_id = login
    db.commit()
    db.refresh(user)
    return user


def change_role(db: Session, actor: User, user_pk: int, role: RoleName) -> User:
    if not is_admin(actor):
        raise ForbiddenError("Only an ADMIN can change roles")
    user = get_user(db, actor, user_pk)
    if user.id == actor.id:
        raise ForbiddenError("You cannot change your own role")
    if user.role.name == role:
        return user
    if role != RoleName.ADMIN:
        ensure_not_last_admin(db, user)
    user.role = get_role(db, role)
    user.token_version += 1  # role claim in existing tokens is now stale
    db.commit()
    db.refresh(user)
    return user


def set_active(db: Session, actor: User, user_pk: int, is_active: bool) -> User:
    user = get_user(db, actor, user_pk)
    if user.id == actor.id:
        raise ForbiddenError("You cannot change the status of your own account")
    if user.is_active == is_active:
        return user
    if not is_active:
        ensure_not_last_admin(db, user)
        user.token_version += 1
    elif user.employee is not None and not user.employee.employment_status.is_working:
        raise ConflictError("The linked employee record is not active. Update the employment status instead.")
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, actor: User, user_pk: int, new_password: str) -> None:
    user = get_user(db, actor, user_pk)
    if user.id == actor.id:
        raise ForbiddenError("Use change-password to update your own password")
    user.password_hash = hash_password(new_password)
    user.token_version += 1
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
