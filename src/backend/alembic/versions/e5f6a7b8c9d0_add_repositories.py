"""add repositories + repo_commits

Repositories link a project to its source-of-truth (initially GitHub).
RepoCommits hold the recent commit history fetched from the host's public
API so the front-end can show "evolution" without re-hitting the API.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-14 02:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("host", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("repo", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("default_branch", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("stars", sa.Integer(), nullable=True),
        sa.Column("last_pushed_at", sa.DateTime(), nullable=True),
        sa.Column("last_polled_at", sa.DateTime(), nullable=True),
        sa.Column("polling_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "url", name="uq_repositories_project_url"),
    )
    with op.batch_alter_table("repositories", schema=None) as batch:
        batch.create_index("ix_repositories_project_id", ["project_id"], unique=False)

    op.create_table(
        "repo_commits",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("repository_id", sa.String(), nullable=False),
        sa.Column("sha", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("author_name", sa.String(), nullable=False),
        sa.Column("author_login", sa.String(), nullable=True),
        sa.Column("author_avatar_url", sa.String(), nullable=True),
        sa.Column("author_profile_url", sa.String(), nullable=True),
        sa.Column("committed_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["repository_id"], ["repositories.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "sha", name="uq_repo_commits_repo_sha"),
    )
    with op.batch_alter_table("repo_commits", schema=None) as batch:
        batch.create_index("ix_repo_commits_repository_id", ["repository_id"], unique=False)
        batch.create_index("ix_repo_commits_committed_at", ["committed_at"], unique=False)


def downgrade() -> None:
    op.drop_table("repo_commits")
    op.drop_table("repositories")
