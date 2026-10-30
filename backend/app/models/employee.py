from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Sequence, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import EmploymentStatus, EmploymentType, Gender
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.designation import Designation
    from app.models.user import User

# Backs the controlled Employee ID generator (EMP-00001, EMP-00002, ...).
employee_code_seq = Sequence("employee_code_seq", start=1, increment=1, metadata=Base.metadata)


def _enum(enum_cls: type, name: str) -> Enum:
    return Enum(enum_cls, name=name, native_enum=False, create_constraint=True, length=30)


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), unique=True, nullable=False)

    full_name: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20))
    gender: Mapped[Gender | None] = mapped_column(_enum(Gender, "gender"))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(Text)

    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="RESTRICT"), index=True)
    designation_id: Mapped[int | None] = mapped_column(ForeignKey("designations.id", ondelete="RESTRICT"), index=True)
    reporting_manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), index=True
    )

    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_type: Mapped[EmploymentType] = mapped_column(
        _enum(EmploymentType, "employment_type"),
        nullable=False,
        default=EmploymentType.FULL_TIME,
    )
    employment_status: Mapped[EmploymentStatus] = mapped_column(
        _enum(EmploymentStatus, "employment_status"),
        index=True,
        nullable=False,
        default=EmploymentStatus.ACTIVE,
    )

    user: Mapped["User"] = relationship(back_populates="employee", lazy="joined")
    department: Mapped["Department | None"] = relationship(back_populates="employees", lazy="joined")
    designation: Mapped["Designation | None"] = relationship(back_populates="employees", lazy="joined")
    reporting_manager: Mapped["Employee | None"] = relationship(
        remote_side="Employee.id", back_populates="direct_reports", lazy="joined", join_depth=1
    )
    direct_reports: Mapped[list["Employee"]] = relationship(back_populates="reporting_manager")

    def __repr__(self) -> str:
        return f"<Employee {self.employee_id}>"
