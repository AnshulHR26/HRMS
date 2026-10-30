"""Initial schema: roles, users, departments, designations, employees, revoked_tokens.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

RECORD_STATUS = ("ACTIVE", "INACTIVE")
GENDER = ("MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY")
EMPLOYMENT_TYPE = ("FULL_TIME", "PART_TIME", "CONTRACT", "INTERN")
EMPLOYMENT_STATUS = ("ACTIVE", "PROBATION", "NOTICE_PERIOD", "INACTIVE", "TERMINATED")


def _enum(values: tuple[str, ...], name: str, length: int) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=length)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # --- roles ---------------------------------------------------------------
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )

    # --- users ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("token_version", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed_login_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], name="fk_users_role_id_roles", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_user_id", "users", ["user_id"], unique=True)
    op.create_index("ix_users_role_id", "users", ["role_id"], unique=False)

    # --- departments ---------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum(RECORD_STATUS, "record_status", 20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("name", name="uq_departments_name"),
        sa.UniqueConstraint("code", name="uq_departments_code"),
    )

    # --- designations --------------------------------------------------------
    op.create_table(
        "designations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=False),
        sa.Column("status", _enum(RECORD_STATUS, "record_status", 20), server_default="ACTIVE", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_designations_department_id_departments",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_designations"),
        sa.UniqueConstraint("code", name="uq_designations_code"),
        sa.UniqueConstraint("department_id", "name", name="uq_designations_department_id_name"),
    )
    op.create_index("ix_designations_department_id", "designations", ["department_id"], unique=False)

    # --- employees -----------------------------------------------------------
    op.execute(sa.schema.CreateSequence(sa.Sequence("employee_code_seq", start=1, increment=1)))
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(20), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("gender", _enum(GENDER, "gender", 30), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("designation_id", sa.Integer(), nullable=True),
        sa.Column("reporting_manager_id", sa.Integer(), nullable=True),
        sa.Column("joining_date", sa.Date(), nullable=False),
        sa.Column("employment_type", _enum(EMPLOYMENT_TYPE, "employment_type", 30), nullable=False),
        sa.Column("employment_status", _enum(EMPLOYMENT_STATUS, "employment_status", 30), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_employees_user_id_users", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_employees_department_id_departments",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["designation_id"],
            ["designations.id"],
            name="fk_employees_designation_id_designations",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporting_manager_id"],
            ["employees.id"],
            name="fk_employees_reporting_manager_id_employees",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint("user_id", name="uq_employees_user_id"),
    )
    op.create_index("ix_employees_employee_id", "employees", ["employee_id"], unique=True)
    op.create_index("ix_employees_email", "employees", ["email"], unique=True)
    op.create_index("ix_employees_full_name", "employees", ["full_name"], unique=False)
    op.create_index("ix_employees_department_id", "employees", ["department_id"], unique=False)
    op.create_index("ix_employees_designation_id", "employees", ["designation_id"], unique=False)
    op.create_index("ix_employees_reporting_manager_id", "employees", ["reporting_manager_id"], unique=False)
    op.create_index("ix_employees_employment_status", "employees", ["employment_status"], unique=False)

    # --- revoked_tokens ------------------------------------------------------
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_revoked_tokens_user_id_users", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jti", name="pk_revoked_tokens"),
    )
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"], unique=False)
    op.create_index("ix_revoked_tokens_expires_at", "revoked_tokens", ["expires_at"], unique=False)

    # --- reference data: the three application roles -------------------------
    op.bulk_insert(
        roles,
        [
            {"name": "ADMIN", "description": "Full system-level access"},
            {"name": "HR", "description": "Employee management and HR operations"},
            {"name": "EMPLOYEE", "description": "Self-service access to own records"},
        ],
    )


def downgrade() -> None:
    op.drop_table("revoked_tokens")
    op.drop_table("employees")
    op.execute(sa.schema.DropSequence(sa.Sequence("employee_code_seq")))
    op.drop_table("designations")
    op.drop_table("departments")
    op.drop_table("users")
    op.drop_table("roles")
