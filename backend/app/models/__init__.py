"""Import every model here so Alembic autogenerate and relationship resolution see them.

Future modules (attendance, leave, payroll, performance) are added to this list.
"""

from app.models.department import Department
from app.models.designation import Designation
from app.models.employee import Employee, employee_code_seq
from app.models.role import Role
from app.models.token import RevokedToken
from app.models.user import User

__all__ = [
    "Department",
    "Designation",
    "Employee",
    "RevokedToken",
    "Role",
    "User",
    "employee_code_seq",
]
