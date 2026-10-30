"""Employee management business rules."""

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.roles import EmploymentStatus, EmploymentType, RecordStatus, RoleName
from app.core.security import hash_password
from app.models import Department, Designation, Employee, User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeProfileFields,
    EmployeeSelfUpdate,
    EmployeeSortField,
)
from app.services.auth_service import normalise_user_id
from app.services.user_service import (
    ensure_can_assign_role,
    ensure_not_last_admin,
    ensure_user_id_available,
    get_role,
    is_admin,
)
from app.utils.employee_id import next_employee_id
from app.utils.pagination import like_pattern, paginate

_SORT_COLUMNS = {
    "employee_id": Employee.employee_id,
    "full_name": Employee.full_name,
    "email": Employee.email,
    "joining_date": Employee.joining_date,
    "created_at": Employee.created_at,
    "employment_status": Employee.employment_status,
}


# --------------------------------------------------------------------------- lookups
def get_by_code(db: Session, employee_code: str) -> Employee:
    employee = db.scalar(select(Employee).where(Employee.employee_id == employee_code.upper()))
    if employee is None:
        raise NotFoundError("Employee not found")
    return employee


def get_for_actor(db: Session, actor: User, employee_code: str) -> Employee:
    """Employees may only read their own record; ownership comes from the JWT identity."""
    if actor.role.name == RoleName.EMPLOYEE:
        own = actor.employee
        if own is None or own.employee_id != employee_code.upper():
            raise ForbiddenError("Employees can only view their own profile")
        return own
    return get_by_code(db, employee_code)


# --------------------------------------------------------------------------- validation
def _ensure_email_available(db: Session, email: str, *, exclude_id: int | None = None) -> None:
    stmt = select(Employee.id).where(Employee.email == email.lower())
    if exclude_id is not None:
        stmt = stmt.where(Employee.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise ConflictError(f"An employee with email '{email}' already exists")


def _validate_org_assignment(
    db: Session,
    department_id: int | None,
    designation_id: int | None,
    *,
    current: Employee | None = None,
) -> None:
    if department_id is not None:
        department = db.get(Department, department_id)
        if department is None:
            raise BadRequestError("Department does not exist")
        changed = current is None or current.department_id != department_id
        if changed and department.status != RecordStatus.ACTIVE:
            raise BadRequestError("Cannot assign an inactive department")
    if designation_id is not None:
        designation = db.get(Designation, designation_id)
        if designation is None:
            raise BadRequestError("Designation does not exist")
        if designation.department_id != department_id:
            raise BadRequestError("Designation does not belong to the selected department")
        changed = current is None or current.designation_id != designation_id
        if changed and designation.status != RecordStatus.ACTIVE:
            raise BadRequestError("Cannot assign an inactive designation")


def _validate_manager(db: Session, manager_id: int | None, *, employee: Employee | None) -> None:
    if manager_id is None:
        return
    manager = db.get(Employee, manager_id)
    if manager is None:
        raise BadRequestError("Reporting manager does not exist")
    if employee is not None:
        if manager.id == employee.id:
            raise BadRequestError("An employee cannot report to themselves")
        # Walk up the chain to make sure we are not creating a cycle.
        seen: set[int] = set()
        cursor: Employee | None = manager
        while cursor is not None and cursor.id not in seen:
            if cursor.reporting_manager_id == employee.id:
                raise BadRequestError("This reporting line would create a management cycle")
            seen.add(cursor.id)
            cursor = cursor.reporting_manager
    if (employee is None or employee.reporting_manager_id != manager_id) and (not manager.employment_status.is_working):
        raise BadRequestError("Reporting manager must be an active employee")


def _ensure_can_edit(actor: User, employee: Employee) -> None:
    if not is_admin(actor) and employee.user.role.name == RoleName.ADMIN:
        raise ForbiddenError("HR users cannot modify ADMIN employee records")


# --------------------------------------------------------------------------- queries
def list_employees(
    db: Session,
    *,
    page: int,
    page_size: int,
    search: str | None = None,
    department_id: int | None = None,
    designation_id: int | None = None,
    employment_status: EmploymentStatus | None = None,
    employment_type: EmploymentType | None = None,
    sort_by: EmployeeSortField = "created_at",
    sort_order: str = "desc",
) -> dict[str, Any]:
    stmt = select(Employee)
    if search:
        pattern = like_pattern(search.strip())
        stmt = stmt.where(
            or_(
                Employee.full_name.ilike(pattern, escape="\\"),
                Employee.email.ilike(pattern, escape="\\"),
                Employee.employee_id.ilike(pattern, escape="\\"),
                Employee.phone_number.ilike(pattern, escape="\\"),
            )
        )
    if department_id is not None:
        stmt = stmt.where(Employee.department_id == department_id)
    if designation_id is not None:
        stmt = stmt.where(Employee.designation_id == designation_id)
    if employment_status is not None:
        stmt = stmt.where(Employee.employment_status == employment_status)
    if employment_type is not None:
        stmt = stmt.where(Employee.employment_type == employment_type)

    column = _SORT_COLUMNS[sort_by]
    ordering = column.asc() if sort_order == "asc" else column.desc()
    stmt = stmt.order_by(ordering, Employee.id.asc())
    return paginate(db, stmt, page, page_size)


# --------------------------------------------------------------------------- commands
def create_employee(db: Session, actor: User, data: EmployeeCreate) -> Employee:
    """Create the login account and the employee profile in a single transaction."""
    ensure_can_assign_role(actor, data.account.role)
    login = normalise_user_id(data.account.user_id)
    ensure_user_id_available(db, login)
    _ensure_email_available(db, data.email)
    _validate_org_assignment(db, data.department_id, data.designation_id)
    _validate_manager(db, data.reporting_manager_id, employee=None)

    try:
        user = User(
            user_id=login,
            password_hash=hash_password(data.account.password),
            role=get_role(db, data.account.role),
            is_active=True,
        )
        db.add(user)
        db.flush()  # assigns users.id inside the open transaction

        employee = Employee(
            employee_id=next_employee_id(db),
            user_id=user.id,
            employment_status=data.employment_status,
            **data.model_dump(exclude={"account", "employment_status"}),
        )
        db.add(employee)
        db.commit()
    except IntegrityError as exc:
        db.rollback()  # neither the user nor the employee row is persisted
        raise ConflictError("Employee could not be created because of conflicting data") from exc
    db.refresh(employee)
    return employee


def update_employee(db: Session, actor: User, employee_code: str, data: EmployeeProfileFields) -> Employee:
    employee = get_by_code(db, employee_code)
    _ensure_can_edit(actor, employee)
    _ensure_email_available(db, data.email, exclude_id=employee.id)
    _validate_org_assignment(db, data.department_id, data.designation_id, current=employee)
    _validate_manager(db, data.reporting_manager_id, employee=employee)

    for field, value in data.model_dump().items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


def set_status(db: Session, actor: User, employee_code: str, status: EmploymentStatus) -> Employee:
    """Soft (de)activation. Keeps the linked account's ability to sign in in sync."""
    employee = get_by_code(db, employee_code)
    if employee.user_id == actor.id:
        raise ForbiddenError("You cannot change your own employment status")
    _ensure_can_edit(actor, employee)

    if employee.employment_status == status:
        return employee

    user = employee.user
    if status.is_working:
        user.is_active = True
    else:
        ensure_not_last_admin(db, user)
        user.is_active = False
        user.token_version += 1  # end every active session immediately
    employee.employment_status = status
    db.commit()
    db.refresh(employee)
    return employee


def update_self(db: Session, employee: Employee, data: EmployeeSelfUpdate) -> Employee:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee
