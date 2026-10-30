"""Phase 1 — authentication & JWT (mandatory cases 1–7 plus hardening)."""

from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import EmploymentStatus, RoleName
from app.core.security import create_access_token
from app.models import User
from tests.conftest import API, PASSWORD, login

ME = f"{API}/auth/me"


# 1
def test_valid_login_succeeds(client: TestClient, make_user) -> None:
    make_user("alice", RoleName.HR)
    response = client.post(f"{API}/auth/login", json={"user_id": "alice", "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert body["user"]["user_id"] == "alice"
    assert body["user"]["role"] == "HR"
    assert "password" not in str(body["user"]).lower()
    # httpOnly cookie + readable CSRF cookie are set for the browser
    set_cookie = ";".join(response.headers.get_list("set-cookie"))
    assert f"{settings.COOKIE_NAME}=" in set_cookie and "HttpOnly" in set_cookie
    assert f"{settings.CSRF_COOKIE_NAME}=" in set_cookie

    claims = jwt.decode(body["access_token"], settings.JWT_SECRET_KEY, algorithms=["HS256"])
    assert claims["role"] == "HR" and claims["jti"] and claims["exp"] > claims["iat"]


def test_login_user_id_is_case_insensitive(client: TestClient, make_user) -> None:
    make_user("alice")
    response = client.post(f"{API}/auth/login", json={"user_id": "  ALICE ", "password": PASSWORD})
    assert response.status_code == 200


# 2
def test_invalid_password_rejected(client: TestClient, make_user) -> None:
    make_user("alice")
    response = client.post(f"{API}/auth/login", json={"user_id": "alice", "password": "wrong-pass1"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid User ID or password"


# 3
def test_invalid_user_id_rejected(client: TestClient) -> None:
    response = client.post(f"{API}/auth/login", json={"user_id": "nobody", "password": PASSWORD})
    assert response.status_code == 401
    # Same message as a wrong password: no user enumeration
    assert response.json()["error"]["message"] == "Invalid User ID or password"


# 4
def test_expired_jwt_rejected(client: TestClient, make_user) -> None:
    user = make_user("alice")
    issued = create_access_token(user_id=user.id, role="EMPLOYEE", token_version=0, expires_delta=timedelta(seconds=-5))
    response = client.get(ME, headers={"Authorization": f"Bearer {issued.token}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token has expired"
    assert response.headers["www-authenticate"] == "Bearer"


# 5
def test_invalid_jwt_rejected(client: TestClient, make_user) -> None:
    user = make_user("alice")
    garbage = client.get(ME, headers={"Authorization": "Bearer not-a-jwt"})
    assert garbage.status_code == 401

    forged = jwt.encode(
        {"sub": str(user.id), "role": "ADMIN", "jti": "x", "ver": 0, "type": "access", "iat": 1, "exp": 9999999999},
        "a-completely-different-secret-key-0123456789",
        algorithm="HS256",
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    unsigned = jwt.encode(
        {"sub": str(user.id), "role": "ADMIN", "jti": "x", "ver": 0, "type": "access", "iat": 1, "exp": 9999999999},
        key=None,
        algorithm="none",
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401


# 6
def test_inactive_user_cannot_login(client: TestClient, make_user) -> None:
    make_user("alice", is_active=False)
    response = client.post(f"{API}/auth/login", json={"user_id": "alice", "password": PASSWORD})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_inactive_user_with_wrong_password_gets_generic_error(client: TestClient, make_user) -> None:
    make_user("alice", is_active=False)
    response = client.post(f"{API}/auth/login", json={"user_id": "alice", "password": "Wrong1234"})
    assert response.status_code == 401


def test_token_rejected_after_user_deactivated(client: TestClient, make_user, db: Session) -> None:
    user = make_user("alice")
    headers = login(client, "alice")
    user.is_active = False
    db.commit()
    assert client.get(ME, headers=headers).status_code in (401, 403)


# 7
def test_missing_token_cannot_access_protected_apis(client: TestClient) -> None:
    for method, path in [
        ("get", ME),
        ("get", f"{API}/employees"),
        ("get", f"{API}/employees/me"),
        ("get", f"{API}/users"),
        ("get", f"{API}/departments"),
        ("get", f"{API}/dashboard/admin"),
        ("post", f"{API}/auth/logout"),
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_returns_current_user_without_secrets(client: TestClient, make_employee) -> None:
    make_employee("alice")
    headers = login(client, "alice")
    body = client.get(ME, headers=headers).json()
    assert body["user_id"] == "alice"
    assert body["employee"]["employee_id"] == "EMP-00001"
    for secret in ("password_hash", "token_version", "failed_login_attempts"):
        assert secret not in body


def test_logout_revokes_token(client: TestClient, make_user) -> None:
    make_user("alice")
    headers = login(client, "alice")
    assert client.post(f"{API}/auth/logout", headers=headers).status_code == 204
    response = client.get(ME, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Token has been revoked"


def test_cookie_auth_and_csrf_protection(client: TestClient, make_user) -> None:
    make_user("alice")
    assert client.post(f"{API}/auth/login", json={"user_id": "alice", "password": PASSWORD}).status_code == 200

    # Cookie alone is enough for safe methods
    assert client.get(ME).status_code == 200
    # ...but unsafe methods need the double-submit CSRF header
    assert client.post(f"{API}/auth/logout").status_code == 403
    csrf = client.cookies.get(settings.CSRF_COOKIE_NAME)
    response = client.post(f"{API}/auth/logout", headers={settings.CSRF_HEADER_NAME: csrf})
    assert response.status_code == 204
    client.cookies.clear()
    assert client.get(ME).status_code == 401


def test_account_lockout_after_repeated_failures(client: TestClient, make_user) -> None:
    make_user("alice")
    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        client.post(f"{API}/auth/login", json={"user_id": "alice", "password": "Wrong1234"})
    response = client.post(f"{API}/auth/login", json={"user_id": "alice", "password": PASSWORD})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"


def test_change_password_invalidates_existing_tokens(client: TestClient, make_user) -> None:
    make_user("alice")
    headers = login(client, "alice")
    response = client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "BrandNew9pass"},
    )
    assert response.status_code == 204
    assert client.get(ME, headers=headers).status_code == 401
    assert client.post(f"{API}/auth/login", json={"user_id": "alice", "password": PASSWORD}).status_code == 401
    login(client, "alice", "BrandNew9pass")


def test_change_password_requires_correct_current_and_strong_new(client: TestClient, make_user) -> None:
    make_user("alice")
    headers = login(client, "alice")
    wrong = client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": "nope12345", "new_password": "BrandNew9pass"},
    )
    assert wrong.status_code == 400
    weak = client.post(
        f"{API}/auth/change-password",
        headers=headers,
        json={"current_password": PASSWORD, "new_password": "short"},
    )
    assert weak.status_code == 422


def test_passwords_are_hashed_with_argon2(make_user, db: Session) -> None:
    user: User = make_user("alice")
    assert user.password_hash.startswith("$argon2id$")
    assert PASSWORD not in user.password_hash


def test_terminated_employee_cannot_login(client: TestClient, make_employee) -> None:
    make_employee("bob", status=EmploymentStatus.TERMINATED)
    response = client.post(f"{API}/auth/login", json={"user_id": "bob", "password": PASSWORD})
    assert response.status_code == 403
