"""Add telemetry transport fields to worker runtime reports."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0049_worker_runtime_telemetry"
down_revision: str = "0048_runtime_source_profile_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_transport", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_path", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_cadence_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_fallback_active", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_publish_drops", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_pending_frames", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "worker_runtime_reports",
        sa.Column("telemetry_last_error", sa.String(length=255), nullable=True),
    )
    op.alter_column("worker_runtime_reports", "telemetry_publish_drops", server_default=None)
    op.alter_column("worker_runtime_reports", "telemetry_pending_frames", server_default=None)


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "telemetry_last_error")
    op.drop_column("worker_runtime_reports", "telemetry_pending_frames")
    op.drop_column("worker_runtime_reports", "telemetry_publish_drops")
    op.drop_column("worker_runtime_reports", "telemetry_fallback_active")
    op.drop_column("worker_runtime_reports", "telemetry_cadence_seconds")
    op.drop_column("worker_runtime_reports", "telemetry_path")
    op.drop_column("worker_runtime_reports", "telemetry_transport")
