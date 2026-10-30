"""Controlled Employee ID generation.

IDs come from the PostgreSQL sequence ``employee_code_seq`` so concurrent
requests can never receive the same number, and gaps (from rolled-back
transactions) are harmless. The unique index on ``employees.employee_id`` is
the final guarantee.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import employee_code_seq

EMPLOYEE_ID_PREFIX = "EMP"
EMPLOYEE_ID_DIGITS = 5


def format_employee_id(number: int) -> str:
    return f"{EMPLOYEE_ID_PREFIX}-{number:0{EMPLOYEE_ID_DIGITS}d}"


def next_employee_id(db: Session) -> str:
    number = db.scalar(select(employee_code_seq.next_value()))
    if number is None:  # pragma: no cover - sequence always returns a value
        raise RuntimeError("employee_code_seq returned no value")
    return format_employee_id(int(number))
