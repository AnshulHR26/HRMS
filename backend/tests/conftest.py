"""Pytest fixtures — tests run against a real, disposable PostgreSQL database.

The schema is built by running the Alembic migrations (so migrations are
tested too); each test starts from empty tables with only the seeded roles.
"""

import os
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

# --- configure the app for tests BEFORE importing it --------------------------------------
_TEST_DB = os.environ.get("TEST_DATABASE_URL", "postgresql+psycopg://hrms:hrms_dev_password@localhost:5432/hrms_test")
os.environ["DATABASE_URL"] = _TEST_DB
os.environ["ENVIRONMENT"] = "test"
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-hs256-0123456789")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("LOGIN_MAX_FAILED_ATTEMPTS", "5")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.roles import EmploymentStatus, RoleName  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Department, Designation, Employee, Role, User  # noqa: E402
from app.utils.employee_id import next_employee_id  # noqa: E402

PASSWORD = "Passw0rd!23"
API = "/api/v1"
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> Iterator[None]:
    cfg = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    cfg.attributes["database_url"] = _TEST_DB
    cfg.attributes["configure_logger"] = False
    with engine.begin() as conn:  # start from a clean schema every run
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    command.upgrade(cfg, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables() -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE revoked_tokens, employees, designations, departments, users RESTART IDENTITY CASCADE")
        )
        conn.execute(text("ALTER SEQUENCE employee_code_seq RESTART WITH 1"))


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


# --- factories ---------------------------------------------------------------------------
@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def factory(user_id: str, role: RoleName = RoleName.EMPLOYEE, *, is_active: bool = True) -> User:
        role_obj = db.scalar(select(Role).where(Role.name == role.value))
        user = User(
            user_id=user_id,
            password_hash=hash_password(PASSWORD),
            role=role_obj,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return factory


@pytest.fixture
def org(db: Session) -> dict[str, Any]:
    eng = Department(name="Engineering", code="ENG")
    fin = Department(name="Finance", code="FIN")
    db.add_all([eng, fin])
    db.flush()
    se = Designation(name="Software Engineer", code="ENG-SE", department_id=eng.id)
    em = Designation(name="Engineering Manager", code="ENG-EM", department_id=eng.id)
    acc = Designation(name="Accountant", code="FIN-ACC", department_id=fin.id)
    db.add_all([se, em, acc])
    db.commit()
    return {"eng": eng.id, "fin": fin.id, "se": se.id, "em": em.id, "acc": acc.id}


@pytest.fixture
def make_employee(db: Session, make_user: Callable[..., User]) -> Callable[..., Employee]:
    counter = {"n": 0}

    def factory(
        user_id: str,
        role: RoleName = RoleName.EMPLOYEE,
        *,
        department_id: int | None = None,
        designation_id: int | None = None,
        status: EmploymentStatus = EmploymentStatus.ACTIVE,
    ) -> Employee:
        counter["n"] += 1
        user = make_user(user_id, role, is_active=status.is_working)
        employee = Employee(
            employee_id=next_employee_id(db),
            user_id=user.id,
            full_name=f"Test Person {counter['n']}",
            email=f"{user_id}@example.com",
            joining_date=date(2024, 1, 15),
            department_id=department_id,
            designation_id=designation_id,
            employment_status=status,
        )
        db.add(employee)
        db.commit()
        db.refresh(employee)
        return employee

    return factory


# --- auth helpers ------------------------------------------------------------------------
def login(client: TestClient, user_id: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(f"{API}/auth/login", json={"user_id": user_id, "password": password})
    assert response.status_code == 200, response.text
    client.cookies.clear()  # tests use explicit Bearer headers unless testing cookies
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin_headers(client: TestClient, make_user: Callable[..., User]) -> dict[str, str]:
    make_user("admin", RoleName.ADMIN)
    return login(client, "admin")


@pytest.fixture
def hr_headers(client: TestClient, make_employee: Callable[..., Employee]) -> dict[str, str]:
    make_employee("hr.user", RoleName.HR)
    return login(client, "hr.user")


@pytest.fixture
def employee_headers(client: TestClient, make_employee: Callable[..., Employee]) -> dict[str, str]:
    make_employee("emp.user", RoleName.EMPLOYEE)
    return login(client, "emp.user")


def employee_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "full_name": "Nisha Rao",
        "email": "nisha.rao@example.com",
        "phone_number": "+91 98765 43210",
        "gender": "FEMALE",
        "date_of_birth": "1995-05-20",
        "address": "Pune",
        "joining_date": "2025-02-01",
        "employment_type": "FULL_TIME",
        "account": {"user_id": "nisha.rao", "password": PASSWORD},
    }
    payload.update(overrides)
    return payload
