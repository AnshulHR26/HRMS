from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.role import Role


class User(TimestampMixin, Base):
    """Login account. Optionally linked 1:1 to an employee profile."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    # Incremented to invalidate every outstanding JWT for this user at once.
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    role: Mapped["Role"] = relationship(back_populates="users", lazy="joined")
    employee: Mapped["Employee | None"] = relationship(back_populates="user", uselist=False, lazy="selectin")

    @property
    def role_name(self) -> str:
        return self.role.name

    def __repr__(self) -> str:
        return f"<User {self.user_id}>"
