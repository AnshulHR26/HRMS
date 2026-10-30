from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from app.core.roles import RecordStatus
from app.schemas.common import ORMModel, StrictInput

CodeStr = Annotated[
    str,
    Field(min_length=2, max_length=20, pattern=r"^[A-Za-z0-9_-]+$", examples=["ENG"]),
]


def _upper(value: str) -> str:
    return value.upper()


class DepartmentBase(StrictInput):
    name: str = Field(min_length=2, max_length=100, examples=["Engineering"])
    code: CodeStr
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("code")
    @classmethod
    def upper_code(cls, value: str) -> str:
        return _upper(value)


class DepartmentCreate(DepartmentBase):
    status: RecordStatus = RecordStatus.ACTIVE


class DepartmentUpdate(DepartmentBase):
    status: RecordStatus


class DepartmentSummary(ORMModel):
    id: int
    name: str
    code: str


class DepartmentResponse(ORMModel):
    id: int
    name: str
    code: str
    description: str | None
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    employee_count: int = 0
    designation_count: int = 0


class ReassignDepartmentEmployees(StrictInput):
    target_department_id: int = Field(gt=0)
    target_designation_id: int | None = Field(
        default=None, gt=0, description="Optional designation in the target department"
    )


class ReassignmentResult(ORMModel):
    moved_employees: int
