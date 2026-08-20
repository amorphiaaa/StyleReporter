"""Add persisted style report run boundary.

Revision ID: 0003_add_style_report_runs
Revises: 0002_add_import_duplicate_count
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_add_style_report_runs"
down_revision: str | None = "0002_add_import_duplicate_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "style_report_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("submission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("runtime_type", sa.String(length=50), nullable=False),
        sa.Column("report_version", sa.String(length=100), nullable=False),
        sa.Column("report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["questionnaire_submissions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_style_report_runs_client_id",
        "style_report_runs",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_style_report_runs_submission_id",
        "style_report_runs",
        ["submission_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_style_report_runs_submission_id", table_name="style_report_runs")
    op.drop_index("ix_style_report_runs_client_id", table_name="style_report_runs")
    op.drop_table("style_report_runs")
