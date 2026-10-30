from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.roles import RecordStatus
from app.dependencies.authorization import AdminUser, HRorAdminUser
from app.dependencies.database import DbSession
from app.schemas.common import ERROR_RESPONSES, ErrorResponse
from app.schemas.department import ReassignmentResult
from app.schemas.designation import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
    ReassignDesignationEmployees,
)
from app.services import designation_service

router = APIRouter(prefix="/designations", tags=["Designations"], responses=ERROR_RESPONSES)
_CONFLICT = {409: {"model": ErrorResponse}}
_NOT_FOUND = {404: {"model": ErrorResponse}}


@router.get("", response_model=list[DesignationResponse])
def list_designations(
    _: HRorAdminUser,
    db: DbSession,
    department_id: Annotated[int | None, Query(gt=0)] = None,
    status_filter: Annotated[RecordStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> list[DesignationResponse]:
    rows = designation_service.list_designations(db, department_id=department_id, status=status_filter, search=search)
    return [DesignationResponse.model_validate(row, from_attributes=True) for row in rows]


@router.post("", response_model=DesignationResponse, status_code=status.HTTP_201_CREATED, responses=_CONFLICT)
def create_designation(payload: DesignationCreate, _: AdminUser, db: DbSession) -> DesignationResponse:
    designation = designation_service.create_designation(db, payload)
    return DesignationResponse.model_validate(designation_service.to_response(db, designation), from_attributes=True)


@router.get("/{designation_id}", response_model=DesignationResponse, responses=_NOT_FOUND)
def get_designation(designation_id: int, _: HRorAdminUser, db: DbSession) -> DesignationResponse:
    designation = designation_service.get_designation(db, designation_id)
    return DesignationResponse.model_validate(designation_service.to_response(db, designation), from_attributes=True)


@router.put("/{designation_id}", response_model=DesignationResponse, responses={**_CONFLICT, **_NOT_FOUND})
def update_designation(
    designation_id: int, payload: DesignationUpdate, _: AdminUser, db: DbSession
) -> DesignationResponse:
    designation = designation_service.update_designation(db, designation_id, payload)
    return DesignationResponse.model_validate(designation_service.to_response(db, designation), from_attributes=True)


@router.post(
    "/{designation_id}/reassign-employees",
    response_model=ReassignmentResult,
    summary="Move every holder of this designation to another designation",
)
def reassign_designation_employees(
    designation_id: int, payload: ReassignDesignationEmployees, _: AdminUser, db: DbSession
) -> ReassignmentResult:
    moved = designation_service.reassign_employees(db, designation_id, payload.target_designation_id)
    return ReassignmentResult(moved_employees=moved)


@router.delete(
    "/{designation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a designation that no employee holds",
    responses={**_CONFLICT, **_NOT_FOUND},
)
def delete_designation(designation_id: int, _: AdminUser, db: DbSession) -> None:
    designation_service.delete_designation(db, designation_id)
