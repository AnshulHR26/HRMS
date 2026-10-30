from fastapi import APIRouter

from app.dependencies.authorization import AdminUser, HRorAdminUser, OwnEmployee
from app.dependencies.database import DbSession
from app.schemas.common import ERROR_RESPONSES
from app.schemas.dashboard import AdminDashboard, EmployeeDashboard, HRDashboard
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboards"], responses=ERROR_RESPONSES)


@router.get("/admin", response_model=AdminDashboard)
def admin_dashboard(_: AdminUser, db: DbSession) -> AdminDashboard:
    return AdminDashboard.model_validate(dashboard_service.admin_dashboard(db), from_attributes=True)


@router.get("/hr", response_model=HRDashboard)
def hr_dashboard(_: HRorAdminUser, db: DbSession) -> HRDashboard:
    return HRDashboard.model_validate(dashboard_service.hr_dashboard(db), from_attributes=True)


@router.get("/me", response_model=EmployeeDashboard)
def employee_dashboard(employee: OwnEmployee) -> EmployeeDashboard:
    return EmployeeDashboard.model_validate(dashboard_service.employee_dashboard(employee))
