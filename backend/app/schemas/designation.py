from datetime import datetime

from pydantic import Field, field_validator

from app.core.roles import RecordStatus
from app.schemas.common import ORMModel, StrictInput
from app.schemas.department import CodeStr, DepartmentSummary


class DesignationBase(StrictInput):
    name: str = Field(min_length=2, max_length=100, examples=["Senior Software Engineer"])
    code: CodeStr
    description: str | None = Field(default=None, max_length=1000)
    department_id: int = Field(gt=0)

    @field_validator("code")
    @classmethod
    def upper_code(cls, value: str) -> str:
        return value.upper()


class DesignationCreate(DesignationBase):
    status: RecordStatus = RecordStatus.ACTIVE


class DesignationUpdate(DesignationBase):
    status: RecordStatus


class DesignationSummary(ORMModel):
    id: int
    name: str
    code: str


class DesignationResponse(ORMModel):
    id: int
    name: str
    code: str
    description: str | None
    department_id: int
    department: DepartmentSummary
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    employee_count: int = 0


class ReassignDesignationEmployees(StrictInput):
    target_designation_id: int = Field(gt=0)
