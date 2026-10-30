from datetime import date

from pydantic import BaseModel

from app.core.roles import EmploymentStatus
from app.schemas.employee import EmployeeListItem


class EmployeeCounts(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int


class DepartmentHeadcount(BaseModel):
    department_id: int | None
    department_name: str
    employee_count: int
    active_count: int


class AdminDashboard(EmployeeCounts):
    total_hr_users: int
    department_count: int
    designation_count: int
    total_users: int
    recent_employees: list[EmployeeListItem]


class HRDashboard(EmployeeCounts):
    department_headcount: list[DepartmentHeadcount]
    recent_employees: list[EmployeeListItem]


class EmployeeDashboard(BaseModel):
    welcome_message: str
    employee_name: str
    employee_id: str
    department: str | None
    designation: str | None
    joining_date: date
    employment_status: EmploymentStatus
    reporting_manager: str | None
