from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.roles import RecordStatus
from app.dependencies.authorization import AdminUser, HRorAdminUser
from app.dependencies.database import DbSession
from app.schemas.common import ERROR_RESPONSES, ErrorResponse
from app.schemas.department import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    ReassignDepartmentEmployees,
    ReassignmentResult,
)
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["Departments"], responses=ERROR_RESPONSES)
_CONFLICT = {409: {"model": ErrorResponse}}
_NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    _: HRorAdminUser,
    db: DbSession,
    status_filter: Annotated[RecordStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> list[DepartmentResponse]:
    rows = department_service.list_departments(db, status=status_filter, search=search)
    return [DepartmentResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED, responses=_CONFLICT)
def create_department(payload: DepartmentCreate, _: AdminUser, db: DbSession) -> DepartmentResponse:
    department = department_service.create_department(db, payload)
    return DepartmentResponse.model_validate(department_service.to_response(db, department), from_attributes=True)


@router.get("/{department_id}", response_model=DepartmentResponse, responses=_NOT_FOUND)
def get_department(department_id: int, _: HRorAdminUser, db: DbSession) -> DepartmentResponse:
    department = department_service.get_department(db, department_id)
    return DepartmentResponse.model_validate(department_service.to_response(db, department), from_attributes=True)


@router.put("/{department_id}", response_model=DepartmentResponse, responses={**_CONFLICT, **_NOT_FOUND})
def update_department(department_id: int, payload: DepartmentUpdate, _: AdminUser, db: DbSession) -> DepartmentResponse:
    department = department_service.update_department(db, department_id, payload)
    return DepartmentResponse.model_validate(department_service.to_response(db, department), from_attributes=True)


@router.post(
    "/{department_id}/reassign-employees",
    response_model=ReassignmentResult,
    summary="Move every employee of this department to another department",
)
def reassign_department_employees(
    department_id: int, payload: ReassignDepartmentEmployees, _: AdminUser, db: DbSession
) -> ReassignmentResult:
    moved = department_service.reassign_employees(
        db, department_id, payload.target_department_id, payload.target_designation_id
    )
    return ReassignmentResult(moved_employees=moved)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department that has no employees",
    responses={**_CONFLICT, **_NOT_FOUND},
)
def delete_department(department_id: int, _: AdminUser, db: DbSession) -> None:
    department_service.delete_department(db, department_id)
