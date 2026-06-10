"""Add worker runtime media evidence fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0046_worker_runtime_media_fields"
down_revision: str | Sequence[str] | None = "0045_platform_superadmin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("selected_provider", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("media_pipeline_mode", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("encoder_mode", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "encoder_mode")
    op.drop_column("worker_runtime_reports", "media_pipeline_mode")
    op.drop_column("worker_runtime_reports", "selected_provider")
