"""Add ingest health fields to worker runtime reports."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0051_worker_runtime_ingest"
down_revision: str = "0050_tracking_frame_observations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("worker_origin", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("processing_mode", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_ingest_lag_ms", sa.Float(), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column(
            "telemetry_duplicate_frames",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.alter_column(
        "worker_runtime_reports",
        "telemetry_duplicate_frames",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "telemetry_duplicate_frames")
    op.drop_column("worker_runtime_reports", "telemetry_ingest_lag_ms")
    op.drop_column("worker_runtime_reports", "processing_mode")
    op.drop_column("worker_runtime_reports", "worker_origin")
