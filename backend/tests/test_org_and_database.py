"""Phase 4 — departments & designations, dashboards, and database cases 24–26."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.roles import EmploymentStatus, RoleName
from app.models import Department, Designation, Employee, User
from app.services import employee_service
from tests.conftest import API, employee_payload, login


# --------------------------------------------------------------------------- departments
def test_admin_department_crud(client: TestClient, admin_headers) -> None:
    created = client.post(
        f"{API}/departments", headers=admin_headers, json={"name": "Legal", "code": "leg", "description": "Contracts"}
    )
    assert created.status_code == 201
    dept = created.json()
    assert dept["code"] == "LEG" and dept["status"] == "ACTIVE" and dept["employee_count"] == 0

    updated = client.put(
        f"{API}/departments/{dept['id']}",
        headers=admin_headers,
        json={"name": "Legal & Compliance", "code": "LEG", "description": None, "status": "INACTIVE"},
    )
    assert updated.status_code == 200 and updated.json()["status"] == "INACTIVE"

    listed = client.get(f"{API}/departments?status=INACTIVE", headers=admin_headers).json()
    assert [d["name"] for d in listed] == ["Legal & Compliance"]

    dup = client.post(f"{API}/departments", headers=admin_headers, json={"name": "legal & compliance", "code": "X1"})
    assert dup.status_code == 409


def test_admin_designation_crud(client: TestClient, admin_headers, org) -> None:
    created = client.post(
        f"{API}/designations",
        headers=admin_headers,
        json={"name": "Staff Engineer", "code": "eng-stf", "department_id": org["eng"]},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["code"] == "ENG-STF" and body["department"]["code"] == "ENG"

    same_name = client.post(
        f"{API}/designations",
        headers=admin_headers,
        json={"name": "Staff Engineer", "code": "ENG-STF2", "department_id": org["eng"]},
    )
    assert same_name.status_code == 409
    other_dept = client.post(
        f"{API}/designations",
        headers=admin_headers,
        json={"name": "Staff Engineer", "code": "FIN-STF", "department_id": org["fin"]},
    )
    assert other_dept.status_code == 201  # same title allowed in another department

    filtered = client.get(f"{API}/designations?department_id={org['fin']}", headers=admin_headers).json()
    assert {d["code"] for d in filtered} == {"FIN-ACC", "FIN-STF"}

    bad_dept = client.post(
        f"{API}/designations", headers=admin_headers, json={"name": "Ghost", "code": "GH", "department_id": 99999}
    )
    assert bad_dept.status_code == 400


def test_department_with_employees_cannot_be_deleted_until_reassigned(
    client: TestClient, admin_headers, org, make_employee
) -> None:
    make_employee("e1", department_id=org["eng"], designation_id=org["se"])
    make_employee("e2", department_id=org["eng"], designation_id=org["em"])

    blocked = client.delete(f"{API}/departments/{org['eng']}", headers=admin_headers)
    assert blocked.status_code == 409
    assert blocked.json()["error"]["details"]["assigned_employees"] == 2

    invalid = client.post(
        f"{API}/departments/{org['eng']}/reassign-employees",
        headers=admin_headers,
        json={"target_department_id": org["fin"], "target_designation_id": org["se"]},
    )
    assert invalid.status_code == 400  # designation must belong to target department

    moved = client.post(
        f"{API}/departments/{org['eng']}/reassign-employees",
        headers=admin_headers,
        json={"target_department_id": org["fin"], "target_designation_id": org["acc"]},
    )
    assert moved.status_code == 200 and moved.json()["moved_employees"] == 2

    assert client.delete(f"{API}/departments/{org['eng']}", headers=admin_headers).status_code == 204
    assert client.get(f"{API}/departments/{org['eng']}", headers=admin_headers).status_code == 404
    # its designations were removed with it
    assert client.get(f"{API}/designations/{org['se']}", headers=admin_headers).status_code == 404


def test_designation_with_employees_cannot_be_deleted_until_reassigned(
    client: TestClient, admin_headers, org, make_employee
) -> None:
    emp = make_employee("e1", department_id=org["eng"], designation_id=org["se"])
    assert client.delete(f"{API}/designations/{org['se']}", headers=admin_headers).status_code == 409

    moved = client.post(
        f"{API}/designations/{org['se']}/reassign-employees",
        headers=admin_headers,
        json={"target_designation_id": org["acc"]},
    )
    assert moved.json()["moved_employees"] == 1
    profile = client.get(f"{API}/employees/{emp.employee_id}", headers=admin_headers).json()
    assert profile["designation"]["code"] == "FIN-ACC"
    assert profile["department"]["code"] == "FIN"  # department follows the designation

    assert client.delete(f"{API}/designations/{org['se']}", headers=admin_headers).status_code == 204


def test_database_restricts_deleting_assigned_department(db: Session, org, make_employee) -> None:
    make_employee("e1", department_id=org["fin"])
    with pytest.raises(IntegrityError):
        db.delete(db.get(Department, org["fin"]))
        db.commit()
    db.rollback()


def test_inactive_department_cannot_be_assigned(client: TestClient, admin_headers, org) -> None:
    client.put(
        f"{API}/departments/{org['fin']}",
        headers=admin_headers,
        json={"name": "Finance", "code": "FIN", "status": "INACTIVE"},
    )
    response = client.post(f"{API}/employees", headers=admin_headers, json=employee_payload(department_id=org["fin"]))
    assert response.status_code == 400


# --------------------------------------------------------------------------- 24
def test_user_and_employee_relationship(db: Session, make_employee) -> None:
    employee = make_employee("linked", RoleName.HR)
    db.expire_all()
    user = db.scalar(select(User).where(User.user_id == "linked"))
    assert user.employee is not None
    assert user.employee.employee_id == employee.employee_id
    assert user.employee.user is user
    assert user.role.name == "HR"
    # one-to-one: a second profile for the same user is rejected by the database
    db.add(
        Employee(
            employee_id="EMP-90000",
            user_id=user.id,
            full_name="Dup",
            email="dup2@example.com",
            joining_date=employee.joining_date,
        )
    )
    with pytest.raises(IntegrityError, match="uq_employees_user_id"):
        db.commit()
    db.rollback()


# --------------------------------------------------------------------------- 25
def test_department_and_designation_relationships(db: Session, org, make_employee) -> None:
    make_employee("e1", department_id=org["eng"], designation_id=org["se"])
    make_employee("e2", department_id=org["eng"], designation_id=org["se"])
    db.expire_all()
    eng = db.get(Department, org["eng"])
    se = db.get(Designation, org["se"])
    assert {d.code for d in eng.designations} == {"ENG-SE", "ENG-EM"}
    assert len(eng.employees) == 2
    assert se.department is eng
    assert len(se.employees) == 2 and all(e.designation is se for e in se.employees)


def test_reporting_manager_relationship(client: TestClient, admin_headers, db: Session, make_employee) -> None:
    manager = make_employee("boss")
    report = make_employee("report")
    client.put(
        f"{API}/employees/{report.employee_id}",
        headers=admin_headers,
        json={
            "full_name": "Report",
            "email": "report@example.com",
            "joining_date": "2024-01-01",
            "reporting_manager_id": manager.id,
        },
    )
    db.expire_all()
    boss = db.get(Employee, manager.id)
    assert [e.employee_id for e in boss.direct_reports] == [report.employee_id]


# --------------------------------------------------------------------------- 26
def test_failed_employee_creation_rolls_back_user_account(
    client: TestClient, admin_headers, db: Session, make_employee, monkeypatch
) -> None:
    existing = make_employee("taken")
    # Force the employee INSERT to fail *after* the user row has been flushed.
    monkeypatch.setattr(employee_service, "next_employee_id", lambda _db: existing.employee_id)
    response = client.post(f"{API}/employees", headers=admin_headers, json=employee_payload())
    assert response.status_code == 409
    db.expire_all()
    assert db.scalar(select(User).where(User.user_id == "nisha.rao")) is None  # no orphan account
    assert db.scalar(select(Employee).where(Employee.email == "nisha.rao@example.com")) is None

    monkeypatch.undo()
    assert client.post(f"{API}/employees", headers=admin_headers, json=employee_payload()).status_code == 201


def test_session_is_usable_after_failed_transaction(db: Session, make_employee) -> None:
    existing = make_employee("first")
    db.add(
        Employee(
            employee_id=existing.employee_id,
            user_id=existing.user_id,
            full_name="X",
            email="x@example.com",
            joining_date=existing.joining_date,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    assert db.scalar(select(Employee).where(Employee.id == existing.id)) is not None


# --------------------------------------------------------------------------- dashboards
def test_dashboards_use_real_counts(client: TestClient, admin_headers, org, make_employee, make_user) -> None:
    make_employee("hr1", RoleName.HR, department_id=org["eng"])
    make_employee("e1", department_id=org["eng"])
    make_employee("e2", department_id=org["fin"], status=EmploymentStatus.INACTIVE)
    make_employee("e3")
    make_user("hr.noprofile", RoleName.HR)

    admin = client.get(f"{API}/dashboard/admin", headers=admin_headers).json()
    assert admin["total_employees"] == 4
    assert admin["active_employees"] == 3
    assert admin["inactive_employees"] == 1
    assert admin["total_hr_users"] == 2
    assert admin["department_count"] == 2
    assert len(admin["recent_employees"]) == 4

    hr = client.get(f"{API}/dashboard/hr", headers=login(client, "hr1")).json()
    headcount = {row["department_name"]: row["employee_count"] for row in hr["department_headcount"]}
    assert headcount == {"Engineering": 2, "Finance": 1, "Unassigned": 1}


def test_employee_dashboard(client: TestClient, org, make_employee) -> None:
    make_employee("e1", department_id=org["eng"], designation_id=org["se"])
    body = client.get(f"{API}/dashboard/me", headers=login(client, "e1")).json()
    assert body["employee_id"] == "EMP-00001"
    assert body["department"] == "Engineering"
    assert body["designation"] == "Software Engineer"
    assert body["employment_status"] == "ACTIVE"
    assert body["welcome_message"].startswith("Welcome back")


def test_health_and_openapi(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}
    schema = client.get(f"{API}/openapi.json").json()
    assert "/api/v1/auth/login" in schema["paths"]
    assert "BearerAuth" in schema["components"]["securitySchemes"]


def test_error_envelope_for_unknown_route(client: TestClient) -> None:
    response = client.get(f"{API}/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_hr_user_management_scope(client: TestClient, hr_headers, make_employee) -> None:
    target = make_employee("e1")
    deactivated = client.patch(f"{API}/users/{target.user_id}/status", headers=hr_headers, json={"is_active": False})
    assert deactivated.status_code == 200 and deactivated.json()["is_active"] is False
    reset = client.post(
        f"{API}/users/{target.user_id}/reset-password", headers=hr_headers, json={"new_password": "NewSecret99"}
    )
    assert reset.status_code == 204
    # disabled account: correct new password is still refused
    refused = client.post(f"{API}/auth/login", json={"user_id": "e1", "password": "NewSecret99"})
    assert refused.status_code == 403
    client.patch(f"{API}/users/{target.user_id}/status", headers=hr_headers, json={"is_active": True})
    login(client, "e1", "NewSecret99")
