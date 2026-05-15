"""Repair runtime artifact timestamp defaults."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0029_runtime_artifact_timestamps"
down_revision = "0028_master_first_run_bootstrap"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE model_runtime_artifacts "
        "SET created_at = now() "
        "WHERE created_at IS NULL"
    )
    op.execute(
        "UPDATE model_runtime_artifacts "
        "SET updated_at = COALESCE(created_at, now()) "
        "WHERE updated_at IS NULL"
    )
    op.alter_column(
        "model_runtime_artifacts",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )
    op.alter_column(
        "model_runtime_artifacts",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.alter_column(
        "model_runtime_artifacts",
        "updated_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=None,
    )
    op.alter_column(
        "model_runtime_artifacts",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        server_default=None,
    )
