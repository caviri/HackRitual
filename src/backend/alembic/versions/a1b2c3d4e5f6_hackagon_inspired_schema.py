"""adopt hackagon-inspired schema: tracks, phases, pages, projects, versioned submissions, waitlist

Adds:
  - tracks, phases, pages, projects tables (admin-managed content + entrant proposals)
  - User.display_name
  - Participant.is_waiting (waitlist support)
  - TimestampMixin + AuditMixin columns (modified_at, created_by_user_id,
    modified_by_user_id) on the new tables and on submissions
  - Submission becomes a versioned snapshot keyed on (project_id, participant_id, version)

Revision ID: a1b2c3d4e5f6
Revises: 4ccb063860c1
Create Date: 2026-05-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4ccb063860c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- tracks ----------------------------------------------------------
    op.create_table(
        "tracks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("modified_by_user_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["modified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "name", name="uq_tracks_event_name"),
    )

    # --- phases ----------------------------------------------------------
    op.create_table(
        "phases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=True),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("modified_by_user_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["modified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("phases", schema=None) as batch_op:
        batch_op.create_index("ix_phases_event_id", ["event_id"], unique=False)
        batch_op.create_index("ix_phases_starts_at", ["starts_at"], unique=False)
        batch_op.create_index("ix_phases_ends_at", ["ends_at"], unique=False)

    # --- pages -----------------------------------------------------------
    op.create_table(
        "pages",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("visible", sa.Boolean(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("modified_by_user_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["modified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phase_id"),  # O2O — at most one page per phase
    )
    with op.batch_alter_table("pages", schema=None) as batch_op:
        batch_op.create_index("ix_pages_event_id", ["event_id"], unique=False)
        batch_op.create_index("ix_pages_order", ["order"], unique=False)
        batch_op.create_index("ix_pages_visible", ["visible"], unique=False)

    # --- projects --------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("track_id", sa.String(), nullable=True),
        sa.Column("proposed_by_participant_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("image", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("modified_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.String(), nullable=True),
        sa.Column("modified_by_user_id", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["track_id"], ["tracks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["proposed_by_participant_id"], ["participants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["modified_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("projects", schema=None) as batch_op:
        batch_op.create_index("ix_projects_event_id", ["event_id"], unique=False)
        batch_op.create_index("ix_projects_track_id", ["track_id"], unique=False)
        batch_op.create_index("ix_projects_status", ["status"], unique=False)
        batch_op.create_index("ix_projects_title", ["title"], unique=False)

    # --- users: display_name --------------------------------------------
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(), nullable=True))

    # --- participants: is_waiting ---------------------------------------
    with op.batch_alter_table("participants", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_waiting",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # --- submissions: rewrite as versioned snapshots --------------------
    # No submission code exists yet, so any rows are throw-away dev data.
    # We use batch_alter so FKs from files/scores referencing submissions
    # are preserved via SQLite's table-copy strategy.
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index("ix_submissions_participant_id")
        batch_op.add_column(sa.Column("project_id", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column("version", sa.Integer(), nullable=False, server_default="1")
        )
        batch_op.add_column(sa.Column("result", sa.String(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "modified_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.current_timestamp(),
            )
        )
        batch_op.add_column(sa.Column("created_by_user_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("modified_by_user_id", sa.String(), nullable=True))
        batch_op.create_foreign_key(
            "fk_submissions_project_id",
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_submissions_created_by_user_id",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_submissions_modified_by_user_id",
            "users",
            ["modified_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_unique_constraint(
            "uq_submissions_project_participant_version",
            ["project_id", "participant_id", "version"],
        )
        batch_op.create_index("ix_submissions_project_id", ["project_id"], unique=False)
        batch_op.create_index(
            "ix_submissions_participant_id", ["participant_id"], unique=False
        )
        batch_op.create_index("ix_submissions_status", ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("submissions", schema=None) as batch_op:
        batch_op.drop_index("ix_submissions_status")
        batch_op.drop_index("ix_submissions_project_id")
        batch_op.drop_constraint(
            "uq_submissions_project_participant_version", type_="unique"
        )
        batch_op.drop_constraint("fk_submissions_modified_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_submissions_created_by_user_id", type_="foreignkey")
        batch_op.drop_constraint("fk_submissions_project_id", type_="foreignkey")
        batch_op.drop_column("modified_by_user_id")
        batch_op.drop_column("created_by_user_id")
        batch_op.drop_column("modified_at")
        batch_op.drop_column("result")
        batch_op.drop_column("version")
        batch_op.drop_column("project_id")
        # ix_submissions_participant_id was dropped & recreated; leave it.

    with op.batch_alter_table("participants", schema=None) as batch_op:
        batch_op.drop_column("is_waiting")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("display_name")

    op.drop_table("projects")
    op.drop_table("pages")
    op.drop_table("phases")
    op.drop_table("tracks")
