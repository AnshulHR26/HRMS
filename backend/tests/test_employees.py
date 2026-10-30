"""Phase 3 — employee management (mandatory cases 17–23 plus listing behaviour)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.roles import EmploymentStatus, RoleName
from app.models import Employee
from tests.conftest import API, PASSWORD, employee_payload, login


# 17
def test_admin_can_create_employee(client: TestClient, admin_headers, org) -> None:
    response = client.post(
        f"{API}/employees",
        headers=admin_headers,
        json=employee_payload(department_id=org["eng"], designation_id=org["se"]),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["employee_id"] == "EMP-00001"
    assert body["user_id"] == "nisha.rao"
    assert body["role"] == "EMPLOYEE"
    assert body["department"]["code"] == "ENG"
    assert body["designation"]["code"] == "ENG-SE"
    assert body["employment_status"] == "ACTIVE"
    # the new employee can sign in with the initial password
    login(client, "nisha.rao")


def test_admin_can_create_hr_employee(client: TestClient, admin_headers) -> None:
    response = client.post(
        f"{API}/employees",
        headers=admin_headers,
        json=employee_payload(account={"user_id": "new.hr", "password": PASSWORD, "role": "HR"}),
    )
    assert response.status_code == 201
    assert response.json()["role"] == "HR"


# 18
def test_hr_can_create_employee(client: TestClient, hr_headers, org) -> None:
    response = client.post(f"{API}/employees", headers=hr_headers, json=employee_payload(department_id=org["fin"]))
    assert response.status_code == 201
    assert response.json()["employee_id"] == "EMP-00002"  # HR fixture already holds EMP-00001


# 19
def test_employee_cannot_create_employee(client: TestClient, employee_headers) -> None:
    response = client.post(f"{API}/employees", headers=employee_headers, json=employee_payload())
    assert response.status_code == 403


# 20
def test_duplicate_employee_ids_are_rejected(
    client: TestClient, admin_headers, db: Session, make_employee, make_user
) -> None:
    existing = make_employee("e1")
    # 1) clients cannot choose an Employee ID at all
    response = client.post(
        f"{API}/employees", headers=admin_headers, json=employee_payload(employee_id=existing.employee_id)
    )
    assert response.status_code == 422
    # 2) the generator never repeats
    ids = {
        client.post(
            f"{API}/employees",
            headers=admin_headers,
            json=employee_payload(
                email=f"person{i}@example.com", account={"user_id": f"person{i}", "password": PASSWORD}
            ),
        ).json()["employee_id"]
        for i in range(5)
    }
    assert len(ids) == 5 and existing.employee_id not in ids
    # 3) the database rejects a duplicate even if something bypassed the generator
    spare = make_user("no.profile")
    db.add(
        Employee(
            employee_id=existing.employee_id,
            user_id=spare.id,
            full_name="X",
            email="dup@example.com",
            joining_date=existing.joining_date,
        )
    )
    with pytest.raises(IntegrityError, match="ix_employees_employee_id"):
        db.commit()
    db.rollback()


def test_duplicate_user_id_and_email_conflict(client: TestClient, admin_headers) -> None:
    assert client.post(f"{API}/employees", headers=admin_headers, json=employee_payload()).status_code == 201
    same_login = client.post(
        f"{API}/employees", headers=admin_headers, json=employee_payload(email="other@example.com")
    )
    assert same_login.status_code == 409
    same_email = client.post(
        f"{API}/employees",
        headers=admin_headers,
        json=employee_payload(account={"user_id": "someone.else", "password": PASSWORD}),
    )
    assert same_email.status_code == 409
    assert same_email.json()["error"]["code"] == "CONFLICT"


# 21
def test_invalid_employee_data_is_rejected(client: TestClient, admin_headers, org) -> None:
    cases = [
        employee_payload(email="not-an-email"),
        employee_payload(full_name="A"),
        employee_payload(phone_number="abc"),
        employee_payload(date_of_birth="2099-01-01"),
        employee_payload(date_of_birth="2015-01-01"),  # under 16 on joining date
        employee_payload(gender="UNKNOWN"),
        employee_payload(account={"user_id": "weak.pass", "password": "password"}),
        employee_payload(account={"user_id": "bad user!", "password": PASSWORD}),
        {k: v for k, v in employee_payload().items() if k != "joining_date"},
        employee_payload(is_admin=True),  # unknown fields are forbidden
    ]
    for payload in cases:
        response = client.post(f"{API}/employees", headers=admin_headers, json=payload)
        assert response.status_code == 422, payload
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    # business-rule violations → 400
    wrong_dept = client.post(
        f"{API}/employees",
        headers=admin_headers,
        json=employee_payload(department_id=org["fin"], designation_id=org["se"]),
    )
    assert wrong_dept.status_code == 400
    missing_dept = client.post(f"{API}/employees", headers=admin_headers, json=employee_payload(department_id=99999))
    assert missing_dept.status_code == 400


# 22
def test_authorized_users_can_update_employee(
    client: TestClient, admin_headers, hr_headers, make_employee, org
) -> None:
    target = make_employee("e1")
    manager = make_employee("mgr1")
    update = {
        "full_name": "Updated Name",
        "email": "updated@example.com",
        "phone_number": "+91 99999 00000",
        "gender": "MALE",
        "date_of_birth": "1990-01-01",
        "address": "Mumbai",
        "department_id": org["eng"],
        "designation_id": org["em"],
        "joining_date": "2023-03-01",
        "employment_type": "CONTRACT",
        "reporting_manager_id": manager.id,
    }
    for headers in (admin_headers, hr_headers):
        response = client.put(f"{API}/employees/{target.employee_id}", headers=headers, json=update)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["full_name"] == "Updated Name"
        assert body["designation"]["code"] == "ENG-EM"
        assert body["reporting_manager"]["employee_id"] == manager.employee_id
        assert body["employee_id"] == target.employee_id  # immutable

    # PUT cannot touch protected fields
    sneaky = client.put(
        f"{API}/employees/{target.employee_id}",
        headers=admin_headers,
        json={**update, "employee_id": "EMP-00999"},
    )
    assert sneaky.status_code == 422


def test_reporting_manager_rules(client: TestClient, admin_headers, make_employee) -> None:
    a = make_employee("a")
    b = make_employee("b")
    base = {"full_name": "Person", "joining_date": "2024-01-01"}
    self_ref = client.put(
        f"{API}/employees/{a.employee_id}",
        headers=admin_headers,
        json={**base, "email": "a@example.com", "reporting_manager_id": a.id},
    )
    assert self_ref.status_code == 400
    ok = client.put(
        f"{API}/employees/{b.employee_id}",
        headers=admin_headers,
        json={**base, "email": "b@example.com", "reporting_manager_id": a.id},
    )
    assert ok.status_code == 200
    cycle = client.put(
        f"{API}/employees/{a.employee_id}",
        headers=admin_headers,
        json={**base, "email": "a@example.com", "reporting_manager_id": b.id},
    )
    assert cycle.status_code == 400
    assert "cycle" in cycle.json()["error"]["message"]


# 23
def test_deactivated_employee_cannot_authenticate(client: TestClient, admin_headers, make_employee) -> None:
    target = make_employee("leaver")
    leaver_headers = login(client, "leaver")

    response = client.patch(
        f"{API}/employees/{target.employee_id}/status",
        headers=admin_headers,
        json={"employment_status": "INACTIVE"},
    )
    assert response.status_code == 200
    assert response.json()["employment_status"] == "INACTIVE"
    assert response.json()["account_active"] is False

    # existing session is terminated and new logins are refused
    assert client.get(f"{API}/auth/me", headers=leaver_headers).status_code == 401
    relogin = client.post(f"{API}/auth/login", json={"user_id": "leaver", "password": PASSWORD})
    assert relogin.status_code == 403
    # soft deactivation: the record still exists
    assert client.get(f"{API}/employees/{target.employee_id}", headers=admin_headers).status_code == 200

    # reactivation restores access
    client.patch(
        f"{API}/employees/{target.employee_id}/status", headers=admin_headers, json={"employment_status": "ACTIVE"}
    )
    login(client, "leaver")


def test_cannot_change_own_employment_status(client: TestClient, make_employee) -> None:
    hr = make_employee("hr.self", RoleName.HR)
    headers = login(client, "hr.self")
    response = client.patch(
        f"{API}/employees/{hr.employee_id}/status", headers=headers, json={"employment_status": "INACTIVE"}
    )
    assert response.status_code == 403


def test_employee_directory_pagination_search_filter_sort(
    client: TestClient, admin_headers, org, make_employee
) -> None:
    for i in range(12):
        make_employee(f"user{i:02d}", department_id=org["eng"] if i % 2 else org["fin"])
    make_employee("gone", status=EmploymentStatus.INACTIVE)

    page1 = client.get(f"{API}/employees?page=1&page_size=5", headers=admin_headers).json()
    assert page1["total"] == 13 and page1["pages"] == 3 and len(page1["items"]) == 5
    page3 = client.get(f"{API}/employees?page=3&page_size=5", headers=admin_headers).json()
    assert len(page3["items"]) == 3

    eng = client.get(f"{API}/employees?department_id={org['eng']}&page_size=100", headers=admin_headers).json()
    assert eng["total"] == 6
    inactive = client.get(f"{API}/employees?employment_status=INACTIVE", headers=admin_headers).json()
    assert [e["email"] for e in inactive["items"]] == ["gone@example.com"]

    search = client.get(f"{API}/employees?search=user07", headers=admin_headers).json()
    assert search["total"] == 1 and search["items"][0]["email"] == "user07@example.com"
    wildcard = client.get(f"{API}/employees?search=%25", headers=admin_headers).json()
    assert wildcard["total"] == 0  # LIKE wildcards are escaped

    asc = client.get(f"{API}/employees?sort_by=employee_id&sort_order=asc&page_size=100", headers=admin_headers).json()
    codes = [e["employee_id"] for e in asc["items"]]
    assert codes == sorted(codes)
    assert client.get(f"{API}/employees?sort_by=password_hash", headers=admin_headers).status_code == 422
    assert client.get(f"{API}/employees?page_size=1000", headers=admin_headers).status_code == 422


def test_get_unknown_employee_returns_404(client: TestClient, admin_headers) -> None:
    response = client.get(f"{API}/employees/EMP-99999", headers=admin_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_admin_without_profile_gets_404_on_me(client: TestClient, admin_headers) -> None:
    assert client.get(f"{API}/employees/me", headers=admin_headers).status_code == 404
