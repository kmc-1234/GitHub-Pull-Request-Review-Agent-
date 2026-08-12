"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_full_name", sa.String(length=255), nullable=False),
        sa.Column("pull_request_number", sa.Integer(), nullable=False),
        sa.Column("installation_id", sa.Integer(), nullable=False),
        sa.Column("head_sha", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "repository_full_name",
            "pull_request_number",
            "head_sha",
            name="uq_review_run",
        ),
    )
    op.create_index("ix_review_runs_head_sha", "review_runs", ["head_sha"])
    op.create_index("ix_review_runs_pull_request_number", "review_runs", ["pull_request_number"])
    op.create_index("ix_review_runs_repository_full_name", "review_runs", ["repository_full_name"])

    op.create_table(
        "finding_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("review_run_id", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("line", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("published_comment_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("review_run_id", "fingerprint", name="uq_finding_fingerprint"),
    )
    op.create_index("ix_finding_records_fingerprint", "finding_records", ["fingerprint"])
    op.create_index("ix_finding_records_review_run_id", "finding_records", ["review_run_id"])

    op.create_table(
        "review_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("repository_full_name", sa.String(length=255), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_review_rules_repository_full_name",
        "review_rules",
        ["repository_full_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("review_rules")
    op.drop_index("ix_finding_records_review_run_id", table_name="finding_records")
    op.drop_index("ix_finding_records_fingerprint", table_name="finding_records")
    op.drop_table("finding_records")
    op.drop_index("ix_review_runs_repository_full_name", table_name="review_runs")
    op.drop_index("ix_review_runs_pull_request_number", table_name="review_runs")
    op.drop_index("ix_review_runs_head_sha", table_name="review_runs")
    op.drop_table("review_runs")
