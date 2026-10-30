from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import EmailStr, Field, field_validator, model_validator

from app.core.roles import EmploymentStatus, EmploymentType, Gender, RoleName
from app.core.security import validate_password_strength
from app.schemas.common import ORMModel, StrictInput
from app.schemas.department import DepartmentSummary
from app.schemas.designation import DesignationSummary
from app.schemas.user import PasswordStr, UserIdStr

if TYPE_CHECKING:
    from app.models.employee import Employee

PhoneStr = Annotated[
    str,
    Field(min_length=7, max_length=20, pattern=r"^\+?[0-9][0-9\s\-()]{5,18}$", examples=["+91 98765 43210"]),
]


class EmployeeProfileFields(StrictInput):
    """Fields HR/Admin manage. Never contains employee_id, user_id, role or status."""

    full_name: str = Field(min_length=2, max_length=150, examples=["Priya Sharma"])
    email: EmailStr
    phone_number: PhoneStr | None = None
    gender: Gender | None = None
    date_of_birth: date | None = None
    address: str | None = Field(default=None, max_length=1000)
    department_id: int | None = Field(default=None, gt=0)
    designation_id: int | None = Field(default=None, gt=0)
    joining_date: date
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    reporting_manager_id: int | None = Field(
        default=None, gt=0, description="Internal id of the manager's employee record"
    )

    @field_validator("email")
    @classmethod
    def lower_email(cls, value: str) -> str:
        return value.lower()

    @model_validator(mode="after")
    def check_dates(self) -> "EmployeeProfileFields":
        today = date.today()
        if self.date_of_birth is not None:
            if self.date_of_birth >= today:
                raise ValueError("date_of_birth must be in the past")
            age_at_joining = (self.joining_date - self.date_of_birth).days / 365.25
            if age_at_joining < 16:
                raise ValueError("Employee must be at least 16 years old on the joining date")
        if self.joining_date > today + timedelta(days=365):
            raise ValueError("joining_date cannot be more than one year in the future")
        if self.designation_id is not None and self.department_id is None:
            raise ValueError("department_id is required when designation_id is provided")
        return self


class EmployeeAccount(StrictInput):
    user_id: UserIdStr
    password: PasswordStr
    role: RoleName = Field(
        default=RoleName.EMPLOYEE,
        description="HR may only create EMPLOYEE accounts; Admin may choose any role",
    )

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class EmployeeCreate(EmployeeProfileFields):
    account: EmployeeAccount
    employment_status: Literal[EmploymentStatus.ACTIVE, EmploymentStatus.PROBATION] = EmploymentStatus.ACTIVE


class EmployeeUpdate(EmployeeProfileFields):
    """PUT — full replacement of the managed profile fields."""


class EmployeeStatusUpdate(StrictInput):
    employment_status: EmploymentStatus


class EmployeeSelfUpdate(StrictInput):
    """The only fields an employee can change on their own profile."""

    phone_number: PhoneStr | None = None
    address: str | None = Field(default=None, max_length=1000)


class ManagerSummary(ORMModel):
    id: int
    employee_id: str
    full_name: str


class EmployeeResponse(ORMModel):
    id: int
    employee_id: str
    user_id: str = Field(description="Login User ID of the linked account")
    role: RoleName
    account_active: bool
    full_name: str
    email: str
    phone_number: str | None
    gender: Gender | None
    date_of_birth: date | None
    address: str | None
    department: DepartmentSummary | None
    designation: DesignationSummary | None
    joining_date: date
    employment_type: EmploymentType
    employment_status: EmploymentStatus
    reporting_manager: ManagerSummary | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_employee(cls, employee: "Employee") -> "EmployeeResponse":
        return cls.model_validate(
            {
                **{name: getattr(employee, name) for name in _DIRECT_FIELDS},
                "user_id": employee.user.user_id,
                "role": employee.user.role.name,
                "account_active": employee.user.is_active,
                "department": employee.department,
                "designation": employee.designation,
                "reporting_manager": employee.reporting_manager,
            },
            from_attributes=True,
        )


_DIRECT_FIELDS = (
    "id",
    "employee_id",
    "full_name",
    "email",
    "phone_number",
    "gender",
    "date_of_birth",
    "address",
    "joining_date",
    "employment_type",
    "employment_status",
    "created_at",
    "updated_at",
)


class EmployeeListItem(ORMModel):
    id: int
    employee_id: str
    full_name: str
    email: str
    phone_number: str | None
    department: DepartmentSummary | None
    designation: DesignationSummary | None
    joining_date: date
    employment_type: EmploymentType
    employment_status: EmploymentStatus
    created_at: datetime


EmployeeSortField = Literal["employee_id", "full_name", "email", "joining_date", "created_at", "employment_status"]
