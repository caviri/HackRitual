"""extend tasks for the queue worker

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-06 00:00:00.000000

Adds the columns the MVP-2 task queue needs: a per-task payload, an attempt
ceiling, and run timestamps.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("payload_json", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "max_attempts",
                sa.Integer(),
                nullable=False,
                server_default="3",
            )
        )
        batch_op.add_column(sa.Column("started_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("started_at")
        batch_op.drop_column("max_attempts")
        batch_op.drop_column("payload_json")
