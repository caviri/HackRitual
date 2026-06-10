"""metrics_daily aggregate counters

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-07 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metrics_daily",
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("submissions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("logins_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agent_submissions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("email_sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rate_limit_triggered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scoring_avg_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scoring_max_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("scoring_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("date"),
    )


def downgrade() -> None:
    op.drop_table("metrics_daily")
