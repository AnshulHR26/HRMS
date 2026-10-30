"""Department management, including the reassign-then-delete workflow."""

from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.roles import RecordStatus
from app.models import Department, Designation, Employee
from app.schemas.department import DepartmentCreate, DepartmentUpdate
from app.utils.pagination import like_pattern


def _employee_count(db: Session, department_id: int) -> int:
    return db.scalar(select(func.count(Employee.id)).where(Employee.department_id == department_id)) or 0


def _with_counts(db: Session, departments: list[Department]) -> list[dict[str, Any]]:
    ids = [d.id for d in departments]
    if not ids:
        return []
    emp_counts = dict(
        db.execute(
            select(Employee.department_id, func.count(Employee.id))
            .where(Employee.department_id.in_(ids))
            .group_by(Employee.department_id)
        ).all()
    )
    des_counts = dict(
        db.execute(
            select(Designation.department_id, func.count(Designation.id))
            .where(Designation.department_id.in_(ids))
            .group_by(Designation.department_id)
        ).all()
    )
    return [
        {
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "description": d.description,
            "status": d.status,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "employee_count": emp_counts.get(d.id, 0),
            "designation_count": des_counts.get(d.id, 0),
        }
        for d in departments
    ]


def to_response(db: Session, department: Department) -> dict[str, Any]:
    return _with_counts(db, [department])[0]


def list_departments(
    db: Session, *, status: RecordStatus | None = None, search: str | None = None
) -> list[dict[str, Any]]:
    stmt = select(Department).order_by(Department.name)
    if status is not None:
        stmt = stmt.where(Department.status == status)
    if search:
        term = like_pattern(search.strip())
        stmt = stmt.where(or_(Department.name.ilike(term, escape="\\"), Department.code.ilike(term, escape="\\")))
    return _with_counts(db, list(db.scalars(stmt).all()))


def get_department(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise NotFoundError("Department not found")
    return department


def _ensure_unique(db: Session, name: str, code: str, exclude_id: int | None = None) -> None:
    stmt = select(Department).where(or_(func.lower(Department.name) == name.lower(), Department.code == code))
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    clash = db.scalars(stmt).first()
    if clash is not None:
        field = "code" if clash.code == code else "name"
        raise ConflictError(f"A department with this {field} already exists")


def create_department(db: Session, data: DepartmentCreate) -> Department:
    _ensure_unique(db, data.name, data.code)
    department = Department(**data.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def update_department(db: Session, department_id: int, data: DepartmentUpdate) -> Department:
    department = get_department(db, department_id)
    _ensure_unique(db, data.name, data.code, exclude_id=department.id)
    for field, value in data.model_dump().items():
        setattr(department, field, value)
    db.commit()
    db.refresh(department)
    return department


def reassign_employees(
    db: Session, department_id: int, target_department_id: int, target_designation_id: int | None
) -> int:
    source = get_department(db, department_id)
    if target_department_id == source.id:
        raise BadRequestError("Target department must be different from the source department")
    target = db.get(Department, target_department_id)
    if target is None:
        raise BadRequestError("Target department does not exist")
    if target.status != RecordStatus.ACTIVE:
        raise BadRequestError("Target department is inactive")
    if target_designation_id is not None:
        designation = db.get(Designation, target_designation_id)
        if designation is None or designation.department_id != target.id:
            raise BadRequestError("Target designation must belong to the target department")
        if designation.status != RecordStatus.ACTIVE:
            raise BadRequestError("Target designation is inactive")

    result = db.execute(
        update(Employee)
        .where(Employee.department_id == source.id)
        .values(department_id=target.id, designation_id=target_designation_id)
        .execution_options(synchronize_session="fetch")
    )
    db.commit()
    return result.rowcount or 0


def delete_department(db: Session, department_id: int) -> None:
    department = get_department(db, department_id)
    assigned = _employee_count(db, department.id)
    if assigned:
        raise ConflictError(
            f"{assigned} employee(s) are assigned to this department. Reassign them before deleting it.",
            details={"assigned_employees": assigned},
        )
    db.delete(department)  # its (now unused) designations are removed by cascade
    db.commit()
