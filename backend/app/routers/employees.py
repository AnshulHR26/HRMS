from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, status

from app.core.roles import EmploymentStatus, EmploymentType
from app.dependencies.authentication import CurrentUser
from app.dependencies.authorization import HRorAdminUser, OwnEmployee
from app.dependencies.database import DbSession
from app.schemas.common import ERROR_RESPONSES, ErrorResponse, Page
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListItem,
    EmployeeResponse,
    EmployeeSelfUpdate,
    EmployeeSortField,
    EmployeeStatusUpdate,
    EmployeeUpdate,
)
from app.services import employee_service

router = APIRouter(prefix="/employees", tags=["Employees"], responses=ERROR_RESPONSES)

EmployeeCode = Annotated[str, Path(pattern=r"^[A-Za-z]{3}-\d{5,}$", examples=["EMP-00001"], description="Employee ID")]


@router.get("", response_model=Page[EmployeeListItem], summary="Employee directory (HR/Admin)")
def list_employees(
    _: HRorAdminUser,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100, description="Name, email, ID or phone")] = None,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    designation_id: Annotated[int | None, Query(gt=0)] = None,
    employment_status: EmploymentStatus | None = None,
    employment_type: EmploymentType | None = None,
    sort_by: EmployeeSortField = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
) -> Page[EmployeeListItem]:
    result = employee_service.list_employees(
        db,
        page=page,
        page_size=page_size,
        search=search,
        department_id=department_id,
        designation_id=designation_id,
        employment_status=employment_status,
        employment_type=employment_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return Page[EmployeeListItem].model_validate(result, from_attributes=True)


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee and its login account",
    responses={400: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def create_employee(payload: EmployeeCreate, actor: HRorAdminUser, db: DbSession) -> EmployeeResponse:
    return EmployeeResponse.from_employee(employee_service.create_employee(db, actor, payload))


# /me must be declared before /{employee_id}
@router.get("/me", response_model=EmployeeResponse, summary="My employee profile")
def get_my_profile(employee: OwnEmployee) -> EmployeeResponse:
    return EmployeeResponse.from_employee(employee)


@router.patch(
    "/me",
    response_model=EmployeeResponse,
    summary="Update my contact details (phone number, address only)",
)
def update_my_profile(payload: EmployeeSelfUpdate, employee: OwnEmployee, db: DbSession) -> EmployeeResponse:
    return EmployeeResponse.from_employee(employee_service.update_self(db, employee, payload))


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Employee profile (HR/Admin, or the employee themself)",
    responses={404: {"model": ErrorResponse}},
)
def get_employee(employee_id: EmployeeCode, actor: CurrentUser, db: DbSession) -> EmployeeResponse:
    return EmployeeResponse.from_employee(employee_service.get_for_actor(db, actor, employee_id))


@router.put(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Replace an employee's profile fields",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_employee(
    employee_id: EmployeeCode, payload: EmployeeUpdate, actor: HRorAdminUser, db: DbSession
) -> EmployeeResponse:
    return EmployeeResponse.from_employee(employee_service.update_employee(db, actor, employee_id, payload))


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeResponse,
    summary="Change employment status (soft deactivation)",
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}},
)
def update_employee_status(
    employee_id: EmployeeCode, payload: EmployeeStatusUpdate, actor: HRorAdminUser, db: DbSession
) -> EmployeeResponse:
    return EmployeeResponse.from_employee(
        employee_service.set_status(db, actor, employee_id, payload.employment_status)
    )
