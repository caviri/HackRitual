"""password auth, applications table, drop login codes and email counter

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-10 00:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Users gain the admin-distributed access password. Plaintext by design
    # (small-event threat model; admins re-copy it from the panel). Unique —
    # login is a lookup on this column alone.
    op.add_column("users", sa.Column("access_password", sa.String(), nullable=True))
    op.create_index("ix_users_access_password", "users", ["access_password"], unique=True)

    # Public sign-up applications, approved by hand in the admin panel.
    op.create_table(
        "applications",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("team", sa.String(), nullable=True),
        sa.Column("project_interest", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(), nullable=False, server_default="form"),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("decided_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_applications_email", "applications", ["email"], unique=True)
    op.create_index("ix_applications_status", "applications", ["status"])

    # Magic-link login codes are gone — nothing emails them anymore.
    op.drop_table("login_codes")

    with op.batch_alter_table("metrics_daily") as batch:
        batch.drop_column("email_sent_count")


def downgrade() -> None:
    with op.batch_alter_table("metrics_daily") as batch:
        batch.add_column(
            sa.Column("email_sent_count", sa.Integer(), nullable=False, server_default="0")
        )

    op.create_table(
        "login_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("code_hash", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("request_ip", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_login_codes_email", "login_codes", ["email"])

    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_email", table_name="applications")
    op.drop_table("applications")

    op.drop_index("ix_users_access_password", table_name="users")
    op.drop_column("users", "access_password")
