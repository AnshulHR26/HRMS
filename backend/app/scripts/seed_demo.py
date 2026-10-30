"""Seed demo departments, designations, an HR user and employees (development only).

Every record is created through the real service layer, so all validations,
the Employee ID generator and the transaction handling are exercised.
Idempotent: existing departments / users are skipped.

Usage::

    DEMO_USER_PASSWORD='...' python -m app.scripts.seed_demo
"""

import sys
import zlib
from datetime import date

from sqlalchemy import select

from app.core.config import settings
from app.core.roles import EmploymentType, Gender, RoleName
from app.core.security import validate_password_strength
from app.database.session import SessionLocal
from app.models import Department, Designation, User
from app.schemas.department import DepartmentCreate
from app.schemas.designation import DesignationCreate
from app.schemas.employee import EmployeeAccount, EmployeeCreate
from app.services import department_service, designation_service, employee_service
from app.services.auth_service import get_user_by_login

DEPARTMENTS = [
    (
        "Engineering",
        "ENG",
        "Product development and platform engineering",
        [("Software Engineer", "ENG-SE"), ("Senior Software Engineer", "ENG-SSE"), ("Engineering Manager", "ENG-EM")],
    ),
    (
        "Human Resources",
        "HR",
        "People operations, hiring and employee relations",
        [("HR Executive", "HR-EXE"), ("HR Manager", "HR-MGR")],
    ),
    (
        "Finance",
        "FIN",
        "Accounting, payroll and financial planning",
        [("Accountant", "FIN-ACC"), ("Finance Manager", "FIN-MGR")],
    ),
    (
        "Sales",
        "SAL",
        "Business development and account management",
        [("Sales Executive", "SAL-EXE"), ("Sales Manager", "SAL-MGR")],
    ),
    ("Operations", "OPS", "Facilities, IT support and administration", [("Operations Executive", "OPS-EXE")]),
]

# (user_id, name, email, gender, dob, dept, designation, joining, type, role, manager_user_id)
PEOPLE = [
    (
        "hr.manager",
        "Priya Sharma",
        "priya.sharma@example.com",
        Gender.FEMALE,
        date(1988, 4, 12),
        "HR",
        "HR-MGR",
        date(2019, 6, 3),
        EmploymentType.FULL_TIME,
        RoleName.HR,
        None,
    ),
    (
        "hr.exec",
        "Rahul Verma",
        "rahul.verma@example.com",
        Gender.MALE,
        date(1994, 9, 21),
        "HR",
        "HR-EXE",
        date(2022, 1, 10),
        EmploymentType.FULL_TIME,
        RoleName.HR,
        "hr.manager",
    ),
    (
        "arjun.mehta",
        "Arjun Mehta",
        "arjun.mehta@example.com",
        Gender.MALE,
        date(1985, 2, 2),
        "ENG",
        "ENG-EM",
        date(2018, 3, 19),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        None,
    ),
    (
        "employee",
        "Ananya Iyer",
        "ananya.iyer@example.com",
        Gender.FEMALE,
        date(1996, 11, 5),
        "ENG",
        "ENG-SSE",
        date(2021, 7, 1),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        "arjun.mehta",
    ),
    (
        "vikram.singh",
        "Vikram Singh",
        "vikram.singh@example.com",
        Gender.MALE,
        date(1999, 1, 30),
        "ENG",
        "ENG-SE",
        date(2023, 8, 14),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        "arjun.mehta",
    ),
    (
        "sneha.patel",
        "Sneha Patel",
        "sneha.patel@example.com",
        Gender.FEMALE,
        date(2002, 5, 17),
        "ENG",
        "ENG-SE",
        date(2025, 1, 6),
        EmploymentType.INTERN,
        RoleName.EMPLOYEE,
        "arjun.mehta",
    ),
    (
        "kavya.reddy",
        "Kavya Reddy",
        "kavya.reddy@example.com",
        Gender.FEMALE,
        date(1990, 8, 8),
        "FIN",
        "FIN-MGR",
        date(2020, 2, 24),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        None,
    ),
    (
        "rohan.das",
        "Rohan Das",
        "rohan.das@example.com",
        Gender.MALE,
        date(1997, 12, 12),
        "FIN",
        "FIN-ACC",
        date(2024, 4, 1),
        EmploymentType.CONTRACT,
        RoleName.EMPLOYEE,
        "kavya.reddy",
    ),
    (
        "meera.nair",
        "Meera Nair",
        "meera.nair@example.com",
        Gender.FEMALE,
        date(1992, 3, 3),
        "SAL",
        "SAL-MGR",
        date(2019, 11, 11),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        None,
    ),
    (
        "aditya.kumar",
        "Aditya Kumar",
        "aditya.kumar@example.com",
        Gender.MALE,
        date(1998, 6, 25),
        "SAL",
        "SAL-EXE",
        date(2024, 9, 2),
        EmploymentType.PART_TIME,
        RoleName.EMPLOYEE,
        "meera.nair",
    ),
    (
        "farhan.ali",
        "Farhan Ali",
        "farhan.ali@example.com",
        Gender.MALE,
        date(1995, 10, 9),
        "OPS",
        "OPS-EXE",
        date(2023, 2, 13),
        EmploymentType.FULL_TIME,
        RoleName.EMPLOYEE,
        None,
    ),
]


def main() -> int:
    if settings.is_production:
        print("ERROR: demo data must never be seeded in production.", file=sys.stderr)
        return 1
    password = settings.DEMO_USER_PASSWORD
    if not password:
        print("ERROR: set DEMO_USER_PASSWORD (env var or backend/.env)", file=sys.stderr)
        return 1
    validate_password_strength(password)

    with SessionLocal() as db:
        admin = get_user_by_login(db, settings.BOOTSTRAP_ADMIN_USER_ID)
        if admin is None or admin.role.name != RoleName.ADMIN:
            print("ERROR: run `python -m app.scripts.bootstrap_admin` first.", file=sys.stderr)
            return 1

        departments: dict[str, Department] = {}
        designations: dict[str, Designation] = {}
        for name, code, description, titles in DEPARTMENTS:
            dept = db.scalar(select(Department).where(Department.code == code))
            if dept is None:
                dept = department_service.create_department(
                    db, DepartmentCreate(name=name, code=code, description=description)
                )
                print(f"  + department {code}")
            departments[code] = dept
            for title, des_code in titles:
                des = db.scalar(select(Designation).where(Designation.code == des_code))
                if des is None:
                    des = designation_service.create_designation(
                        db, DesignationCreate(name=title, code=des_code, department_id=dept.id)
                    )
                    print(f"  + designation {des_code}")
                designations[des_code] = des

        for login, name, email, gender, dob, dept_code, des_code, joined, emp_type, role, manager in PEOPLE:
            if get_user_by_login(db, login) is not None:
                continue
            manager_user: User | None = get_user_by_login(db, manager) if manager else None
            employee = employee_service.create_employee(
                db,
                admin,
                EmployeeCreate(
                    full_name=name,
                    email=email,
                    phone_number=f"+91 98{zlib.crc32(login.encode()) % 10**8:08d}",
                    gender=gender,
                    date_of_birth=dob,
                    address="Bengaluru, Karnataka, India",
                    department_id=departments[dept_code].id,
                    designation_id=designations[des_code].id,
                    joining_date=joined,
                    employment_type=emp_type,
                    reporting_manager_id=manager_user.employee.id if manager_user and manager_user.employee else None,
                    account=EmployeeAccount(user_id=login, password=password, role=role),
                ),
            )
            print(f"  + {employee.employee_id} {name} ({role}) — login: {login}")
    print("Demo data ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
