"""Application roles and domain enumerations shared by models, schemas and services."""

from enum import StrEnum


class RoleName(StrEnum):
    ADMIN = "ADMIN"
    HR = "HR"
    EMPLOYEE = "EMPLOYEE"


class Gender(StrEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"


class EmploymentType(StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    INTERN = "INTERN"


class EmploymentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PROBATION = "PROBATION"
    NOTICE_PERIOD = "NOTICE_PERIOD"
    INACTIVE = "INACTIVE"
    TERMINATED = "TERMINATED"

    @property
    def is_working(self) -> bool:
        """Statuses that keep the linked user account able to sign in."""
        return self in WORKING_STATUSES


WORKING_STATUSES = frozenset({EmploymentStatus.ACTIVE, EmploymentStatus.PROBATION, EmploymentStatus.NOTICE_PERIOD})


class RecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
