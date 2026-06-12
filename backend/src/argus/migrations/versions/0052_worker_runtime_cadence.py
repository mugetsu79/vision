"""Add cadence fields to worker runtime reports."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0052_worker_runtime_cadence"
down_revision: str = "0051_worker_runtime_ingest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("processing_fps_cap", sa.Float(), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("output_fps", sa.Float(), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("stream_profile_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column(
            "tracking_diagnostics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column(
        "worker_runtime_reports",
        "tracking_diagnostics",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "tracking_diagnostics")
    op.drop_column("worker_runtime_reports", "stream_profile_id")
    op.drop_column("worker_runtime_reports", "output_fps")
    op.drop_column("worker_runtime_reports", "processing_fps_cap")
