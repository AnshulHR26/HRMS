"""Dashboard statistics — every number comes from a live database query."""

from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.roles import WORKING_STATUSES, RoleName
from app.models import Department, Designation, Employee, Role, User

_RECENT_LIMIT = 5


def employee_counts(db: Session) -> dict[str, int]:
    working = [status.value for status in WORKING_STATUSES]
    total, active = db.execute(
        select(
            func.count(Employee.id),
            func.count(case((Employee.employment_status.in_(working), Employee.id))),
        )
    ).one()
    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": total - active,
    }


def recent_employees(db: Session, limit: int = _RECENT_LIMIT) -> list[Employee]:
    return list(
        db.scalars(select(Employee).order_by(Employee.created_at.desc(), Employee.id.desc()).limit(limit)).unique()
    )


def department_headcount(db: Session) -> list[dict[str, Any]]:
    working = [status.value for status in WORKING_STATUSES]
    rows = db.execute(
        select(
            Department.id,
            Department.name,
            func.count(Employee.id),
            func.count(case((Employee.employment_status.in_(working), Employee.id))),
        )
        .outerjoin(Employee, Employee.department_id == Department.id)
        .group_by(Department.id, Department.name)
        .order_by(func.count(Employee.id).desc(), Department.name)
    ).all()
    result = [
        {"department_id": dep_id, "department_name": name, "employee_count": total, "active_count": active}
        for dep_id, name, total, active in rows
    ]
    unassigned_total, unassigned_active = db.execute(
        select(
            func.count(Employee.id),
            func.count(case((Employee.employment_status.in_(working), Employee.id))),
        ).where(Employee.department_id.is_(None))
    ).one()
    if unassigned_total:
        result.append(
            {
                "department_id": None,
                "department_name": "Unassigned",
                "employee_count": unassigned_total,
                "active_count": unassigned_active,
            }
        )
    return result


def admin_dashboard(db: Session) -> dict[str, Any]:
    hr_users = db.scalar(select(func.count(User.id)).join(Role).where(Role.name == RoleName.HR.value))
    return {
        **employee_counts(db),
        "total_hr_users": hr_users or 0,
        "department_count": db.scalar(select(func.count(Department.id))) or 0,
        "designation_count": db.scalar(select(func.count(Designation.id))) or 0,
        "total_users": db.scalar(select(func.count(User.id))) or 0,
        "recent_employees": recent_employees(db),
    }


def hr_dashboard(db: Session) -> dict[str, Any]:
    return {
        **employee_counts(db),
        "department_headcount": department_headcount(db),
        "recent_employees": recent_employees(db),
    }


def employee_dashboard(employee: Employee) -> dict[str, Any]:
    first_name = employee.full_name.split()[0]
    return {
        "welcome_message": f"Welcome back, {first_name}!",
        "employee_name": employee.full_name,
        "employee_id": employee.employee_id,
        "department": employee.department.name if employee.department else None,
        "designation": employee.designation.name if employee.designation else None,
        "joining_date": employee.joining_date,
        "employment_status": employee.employment_status,
        "reporting_manager": employee.reporting_manager.full_name if employee.reporting_manager else None,
    }
