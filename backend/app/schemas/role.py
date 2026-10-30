from app.core.roles import RoleName
from app.schemas.common import ORMModel


class RoleResponse(ORMModel):
    id: int
    name: RoleName
    description: str | None = None
