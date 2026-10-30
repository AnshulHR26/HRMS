"""Phase 2 — RBAC (mandatory cases 8–16 plus privilege-escalation guards)."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.roles import RoleName
from app.models import User
from tests.conftest import API, PASSWORD, employee_payload, login


# 8
def test_admin_can_access_all_employee_records(client: TestClient, admin_headers, make_employee) -> None:
    a = make_employee("e1")
    b = make_employee("e2")
    listing = client.get(f"{API}/employees", headers=admin_headers)
    assert listing.status_code == 200
    assert {item["employee_id"] for item in listing.json()["items"]} == {a.employee_id, b.employee_id}
    assert client.get(f"{API}/employees/{b.employee_id}", headers=admin_headers).status_code == 200


# 9
def test_hr_can_access_all_employee_records(client: TestClient, hr_headers, make_employee) -> None:
    other = make_employee("e1")
    listing = client.get(f"{API}/employees", headers=hr_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 2  # HR's own profile + e1
    assert client.get(f"{API}/employees/{other.employee_id}", headers=hr_headers).status_code == 200


# 10
def test_employee_can_access_only_own_record(client: TestClient, make_employee) -> None:
    me = make_employee("emp.me")
    headers = login(client, "emp.me")
    own = client.get(f"{API}/employees/me", headers=headers)
    assert own.status_code == 200
    assert own.json()["employee_id"] == me.employee_id
    assert client.get(f"{API}/employees/{me.employee_id}", headers=headers).status_code == 200
    assert client.get(f"{API}/dashboard/me", headers=headers).status_code == 200


# 11
def test_employee_cannot_access_another_employees_record(client: TestClient, make_employee) -> None:
    make_employee("emp.me")
    other = make_employee("emp.other")
    headers = login(client, "emp.me")
    response = client.get(f"{API}/employees/{other.employee_id}", headers=headers)
    assert response.status_code == 403
    # Non-existent IDs also give 403 to employees (no enumeration)
    assert client.get(f"{API}/employees/EMP-99999", headers=headers).status_code == 403


# 12
def test_employee_cannot_access_admin_apis(client: TestClient, employee_headers, org) -> None:
    calls = [
        client.get(f"{API}/dashboard/admin", headers=employee_headers),
        client.get(f"{API}/users", headers=employee_headers),
        client.post(
            f"{API}/users",
            headers=employee_headers,
            json={"user_id": "x.user", "password": PASSWORD, "role": "EMPLOYEE"},
        ),
        client.post(f"{API}/departments", headers=employee_headers, json={"name": "Legal", "code": "LEG"}),
        client.delete(f"{API}/departments/{org['eng']}", headers=employee_headers),
        client.post(
            f"{API}/designations",
            headers=employee_headers,
            json={"name": "Lawyer", "code": "LEG-L", "department_id": org["eng"]},
        ),
    ]
    assert [r.status_code for r in calls] == [403] * len(calls)


# 13
def test_employee_cannot_access_hr_apis(client: TestClient, employee_headers, make_employee) -> None:
    other = make_employee("e2")
    calls = [
        client.get(f"{API}/dashboard/hr", headers=employee_headers),
        client.get(f"{API}/employees", headers=employee_headers),
        client.get(f"{API}/departments", headers=employee_headers),
        client.get(f"{API}/designations", headers=employee_headers),
        client.put(
            f"{API}/employees/{other.employee_id}",
            headers=employee_headers,
            json={"full_name": "Hacked", "email": "h@example.com", "joining_date": "2024-01-01"},
        ),
        client.patch(
            f"{API}/employees/{other.employee_id}/status",
            headers=employee_headers,
            json={"employment_status": "INACTIVE"},
        ),
    ]
    assert [r.status_code for r in calls] == [403] * len(calls)


def test_hr_cannot_access_admin_only_apis(client: TestClient, hr_headers, org) -> None:
    assert client.get(f"{API}/dashboard/admin", headers=hr_headers).status_code == 403
    assert (
        client.post(f"{API}/departments", headers=hr_headers, json={"name": "Legal", "code": "LEG"}).status_code == 403
    )
    assert client.delete(f"{API}/departments/{org['eng']}", headers=hr_headers).status_code == 403
    # but HR may read departments, designations and the HR dashboard
    assert client.get(f"{API}/departments", headers=hr_headers).status_code == 200
    assert client.get(f"{API}/designations", headers=hr_headers).status_code == 200
    assert client.get(f"{API}/dashboard/hr", headers=hr_headers).status_code == 200


# 14
def test_hr_cannot_create_admin_accounts(client: TestClient, hr_headers) -> None:
    via_users = client.post(
        f"{API}/users",
        headers=hr_headers,
        json={"user_id": "evil.admin", "password": PASSWORD, "role": "ADMIN"},
    )
    assert via_users.status_code == 403
    via_hr_role = client.post(
        f"{API}/users",
        headers=hr_headers,
        json={"user_id": "new.hr", "password": PASSWORD, "role": "HR"},
    )
    assert via_hr_role.status_code == 403
    via_employees = client.post(
        f"{API}/employees",
        headers=hr_headers,
        json=employee_payload(account={"user_id": "evil.admin", "password": PASSWORD, "role": "ADMIN"}),
    )
    assert via_employees.status_code == 403
    # HR *can* create normal employee accounts
    ok = client.post(
        f"{API}/users",
        headers=hr_headers,
        json={"user_id": "plain.emp", "password": PASSWORD, "role": "EMPLOYEE"},
    )
    assert ok.status_code == 201


# 15
def test_hr_cannot_modify_admin_permissions(client: TestClient, hr_headers, make_user, make_employee) -> None:
    admin = make_user("the.admin", RoleName.ADMIN)
    admin_profile = make_employee("admin.with.profile", RoleName.ADMIN)
    employee = make_employee("e1")

    assert (
        client.patch(f"{API}/users/{admin.id}/role", headers=hr_headers, json={"role": "EMPLOYEE"}).status_code == 403
    )
    assert (
        client.patch(f"{API}/users/{employee.user_id}/role", headers=hr_headers, json={"role": "ADMIN"}).status_code
        == 403
    )
    assert (
        client.patch(f"{API}/users/{admin.id}/status", headers=hr_headers, json={"is_active": False}).status_code == 403
    )
    assert (
        client.post(
            f"{API}/users/{admin.id}/reset-password", headers=hr_headers, json={"new_password": "Takeover123"}
        ).status_code
        == 403
    )
    assert client.get(f"{API}/users/{admin.id}", headers=hr_headers).status_code == 403
    assert (
        client.patch(
            f"{API}/employees/{admin_profile.employee_id}/status",
            headers=hr_headers,
            json={"employment_status": "INACTIVE"},
        ).status_code
        == 403
    )
    # HR's user list never contains ADMIN accounts
    listed = client.get(f"{API}/users", headers=hr_headers).json()["items"]
    assert all(item["role"] == "EMPLOYEE" for item in listed)


# 16
def test_employee_cannot_change_own_role(client: TestClient, make_employee, db: Session) -> None:
    me = make_employee("emp.me")
    headers = login(client, "emp.me")
    assert client.patch(f"{API}/users/{me.user_id}/role", headers=headers, json={"role": "ADMIN"}).status_code == 403
    # The self-service endpoint rejects any field other than phone/address (mass assignment)
    sneaky = client.patch(f"{API}/employees/me", headers=headers, json={"role": "ADMIN"})
    assert sneaky.status_code == 422
    sneaky_status = client.patch(
        f"{API}/employees/me", headers=headers, json={"employment_status": "ACTIVE", "department_id": 1}
    )
    assert sneaky_status.status_code == 422
    db.expire_all()
    assert db.get(User, me.user_id).role.name == "EMPLOYEE"


def test_employee_can_update_own_contact_details(client: TestClient, make_employee) -> None:
    make_employee("emp.me")
    headers = login(client, "emp.me")
    response = client.patch(
        f"{API}/employees/me", headers=headers, json={"phone_number": "+91 90000 11111", "address": "Chennai"}
    )
    assert response.status_code == 200
    assert response.json()["address"] == "Chennai"


def test_admin_role_change_rules(client: TestClient, admin_headers, make_employee, db: Session) -> None:
    target = make_employee("e1")
    target_headers = login(client, "e1")
    promoted = client.patch(f"{API}/users/{target.user_id}/role", headers=admin_headers, json={"role": "HR"})
    assert promoted.status_code == 200 and promoted.json()["role"] == "HR"
    # the old token carries a stale role claim and is rejected
    assert client.get(f"{API}/auth/me", headers=target_headers).status_code == 401

    admin = db.query(User).filter_by(user_id="admin").one()
    assert (
        client.patch(f"{API}/users/{admin.id}/role", headers=admin_headers, json={"role": "HR"}).status_code == 403
    )  # cannot change own role
    assert (
        client.patch(f"{API}/users/{admin.id}/status", headers=admin_headers, json={"is_active": False}).status_code
        == 403
    )  # cannot deactivate self


def test_admin_can_manage_other_admins_and_hr(client: TestClient, admin_headers, make_user) -> None:
    other_admin = make_user("admin2", RoleName.ADMIN)
    hr = make_user("hr2", RoleName.HR)
    assert (
        client.patch(f"{API}/users/{hr.id}/status", headers=admin_headers, json={"is_active": False}).status_code == 200
    )
    demoted = client.patch(f"{API}/users/{other_admin.id}/role", headers=admin_headers, json={"role": "HR"})
    assert demoted.status_code == 200 and demoted.json()["role"] == "HR"
    roles = client.get(f"{API}/roles", headers=admin_headers).json()
    assert [r["name"] for r in roles] == ["ADMIN", "HR", "EMPLOYEE"]
