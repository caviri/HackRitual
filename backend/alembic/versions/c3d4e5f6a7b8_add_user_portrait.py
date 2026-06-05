"""add user portrait fields

Five new columns on users: portrait_path + portrait_original_path (file paths
under UPLOAD_DIR), portrait_effect (dither|halftone|none), and the two tunable
parameters portrait_contrast / portrait_brightness used by the image pipeline.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-14 01:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("portrait_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("portrait_original_path", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("portrait_effect", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("portrait_contrast", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("portrait_brightness", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("portrait_brightness")
        batch_op.drop_column("portrait_contrast")
        batch_op.drop_column("portrait_effect")
        batch_op.drop_column("portrait_original_path")
        batch_op.drop_column("portrait_path")
