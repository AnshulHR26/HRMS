"""Designation management, including the reassign-then-delete workflow."""

from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.roles import RecordStatus
from app.models import Department, Designation, Employee
from app.schemas.designation import DesignationCreate, DesignationUpdate
from app.utils.pagination import like_pattern


def _employee_count(db: Session, designation_id: int) -> int:
    return db.scalar(select(func.count(Employee.id)).where(Employee.designation_id == designation_id)) or 0


def _with_counts(db: Session, designations: list[Designation]) -> list[dict[str, Any]]:
    ids = [d.id for d in designations]
    if not ids:
        return []
    counts = dict(
        db.execute(
            select(Employee.designation_id, func.count(Employee.id))
            .where(Employee.designation_id.in_(ids))
            .group_by(Employee.designation_id)
        ).all()
    )
    return [
        {
            "id": d.id,
            "name": d.name,
            "code": d.code,
            "description": d.description,
            "department_id": d.department_id,
            "department": d.department,
            "status": d.status,
            "created_at": d.created_at,
            "updated_at": d.updated_at,
            "employee_count": counts.get(d.id, 0),
        }
        for d in designations
    ]


def to_response(db: Session, designation: Designation) -> dict[str, Any]:
    return _with_counts(db, [designation])[0]


def list_designations(
    db: Session,
    *,
    department_id: int | None = None,
    status: RecordStatus | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    stmt = select(Designation).join(Department).order_by(Department.name, Designation.name)
    if department_id is not None:
        stmt = stmt.where(Designation.department_id == department_id)
    if status is not None:
        stmt = stmt.where(Designation.status == status)
    if search:
        term = like_pattern(search.strip())
        stmt = stmt.where(or_(Designation.name.ilike(term, escape="\\"), Designation.code.ilike(term, escape="\\")))
    return _with_counts(db, list(db.scalars(stmt).unique().all()))


def get_designation(db: Session, designation_id: int) -> Designation:
    designation = db.get(Designation, designation_id)
    if designation is None:
        raise NotFoundError("Designation not found")
    return designation


def _validate(db: Session, data: DesignationCreate | DesignationUpdate, exclude_id: int | None = None) -> None:
    department = db.get(Department, data.department_id)
    if department is None:
        raise BadRequestError("Department does not exist")

    code_stmt = select(Designation.id).where(Designation.code == data.code)
    name_stmt = select(Designation.id).where(
        Designation.department_id == data.department_id,
        func.lower(Designation.name) == data.name.lower(),
    )
    if exclude_id is not None:
        code_stmt = code_stmt.where(Designation.id != exclude_id)
        name_stmt = name_stmt.where(Designation.id != exclude_id)
    if db.scalar(code_stmt) is not None:
        raise ConflictError("A designation with this code already exists")
    if db.scalar(name_stmt) is not None:
        raise ConflictError("This department already has a designation with this name")


def create_designation(db: Session, data: DesignationCreate) -> Designation:
    _validate(db, data)
    department = db.get(Department, data.department_id)
    if department is not None and department.status != RecordStatus.ACTIVE:
        raise BadRequestError("Cannot add a designation to an inactive department")
    designation = Designation(**data.model_dump())
    db.add(designation)
    db.commit()
    db.refresh(designation)
    return designation


def update_designation(db: Session, designation_id: int, data: DesignationUpdate) -> Designation:
    designation = get_designation(db, designation_id)
    _validate(db, data, exclude_id=designation.id)
    if data.department_id != designation.department_id and _employee_count(db, designation.id):
        raise ConflictError("Employees hold this designation. Reassign them before moving it to another department.")
    for field, value in data.model_dump().items():
        setattr(designation, field, value)
    db.commit()
    db.refresh(designation)
    return designation


def reassign_employees(db: Session, designation_id: int, target_designation_id: int) -> int:
    source = get_designation(db, designation_id)
    if target_designation_id == source.id:
        raise BadRequestError("Target designation must be different from the source designation")
    target = db.get(Designation, target_designation_id)
    if target is None:
        raise BadRequestError("Target designation does not exist")
    if target.status != RecordStatus.ACTIVE or target.department.status != RecordStatus.ACTIVE:
        raise BadRequestError("Target designation (or its department) is inactive")

    result = db.execute(
        update(Employee)
        .where(Employee.designation_id == source.id)
        .values(designation_id=target.id, department_id=target.department_id)
        .execution_options(synchronize_session="fetch")
    )
    db.commit()
    return result.rowcount or 0


def delete_designation(db: Session, designation_id: int) -> None:
    designation = get_designation(db, designation_id)
    assigned = _employee_count(db, designation.id)
    if assigned:
        raise ConflictError(
            f"{assigned} employee(s) hold this designation. Reassign them before deleting it.",
            details={"assigned_employees": assigned},
        )
    db.delete(designation)
    db.commit()
