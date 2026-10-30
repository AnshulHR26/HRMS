from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import RecordStatus
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.designation import Designation
    from app.models.employee import Employee


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status", native_enum=False, create_constraint=True, length=20),
        nullable=False,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
    )

    designations: Mapped[list["Designation"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    employees: Mapped[list["Employee"]] = relationship(back_populates="department", passive_deletes="all")

    def __repr__(self) -> str:
        return f"<Department {self.code}>"
