from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.roles import RecordStatus
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.employee import Employee


class Designation(TimestampMixin, Base):
    __tablename__ = "designations"
    __table_args__ = (UniqueConstraint("department_id", "name", name="uq_designations_department_id_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus, name="record_status", native_enum=False, create_constraint=True, length=20),
        nullable=False,
        default=RecordStatus.ACTIVE,
        server_default=RecordStatus.ACTIVE.value,
    )

    department: Mapped["Department"] = relationship(back_populates="designations", lazy="joined")
    employees: Mapped[list["Employee"]] = relationship(back_populates="designation", passive_deletes="all")

    def __repr__(self) -> str:
        return f"<Designation {self.code}>"
