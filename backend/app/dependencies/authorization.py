"""Role-based authorization dependencies (applied with ``Depends()`` on routes)."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.roles import RoleName
from app.dependencies.authentication import get_current_user
from app.models import Employee, User


def require_roles(*allowed: RoleName) -> Callable[[User], User]:
    allowed_names = frozenset(role.value for role in allowed)
    label = " or ".join(sorted(allowed_names))

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role.name not in allowed_names:
            raise ForbiddenError(f"This action requires the {label} role")
        return user

    dependency.__name__ = f"require_{'_or_'.join(sorted(n.lower() for n in allowed_names))}"
    return dependency


require_admin = require_roles(RoleName.ADMIN)
require_hr_or_admin = require_roles(RoleName.HR, RoleName.ADMIN)


def require_employee(user: Annotated[User, Depends(get_current_user)]) -> Employee:
    """Resolve the caller's own employee profile from the authenticated identity.

    The record is looked up through ``users.id`` from the verified JWT — never
    from a client-supplied identifier — which makes ownership checks implicit.
    """
    if user.employee is None:
        raise NotFoundError("No employee profile is linked to this account")
    return user.employee


AdminUser = Annotated[User, Depends(require_admin)]
HRorAdminUser = Annotated[User, Depends(require_hr_or_admin)]
OwnEmployee = Annotated[Employee, Depends(require_employee)]
