"""Persist skipped duplicate count on import runs.

Revision ID: 0002_add_import_duplicate_count
Revises: 0001_initial_schema
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_import_duplicate_count"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "import_runs",
        sa.Column(
            "skipped_duplicates",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("import_runs", "skipped_duplicates")
