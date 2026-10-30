from fastapi import APIRouter
from sqlalchemy import select

from app.dependencies.authorization import HRorAdminUser
from app.dependencies.database import DbSession
from app.models import Role
from app.schemas.common import ERROR_RESPONSES
from app.schemas.role import RoleResponse

router = APIRouter(prefix="/roles", tags=["User Management"], responses=ERROR_RESPONSES)


@router.get("", response_model=list[RoleResponse], summary="List application roles")
def list_roles(_: HRorAdminUser, db: DbSession) -> list[RoleResponse]:
    roles = db.scalars(select(Role).order_by(Role.id)).all()
    return [RoleResponse.model_validate(role) for role in roles]
