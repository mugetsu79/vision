"""Add canonical tracking frame persistence and compatibility fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0050_tracking_frame_observations"
down_revision: str = "0049_worker_runtime_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tracking_frames",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id"),
            nullable=False,
        ),
        sa.Column("frame_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("frame_sequence", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("profile", sa.String(length=64), nullable=False),
        sa.Column("stream_mode", sa.String(length=64), nullable=False),
        sa.Column("stream_profile_id", sa.String(length=255), nullable=False),
        sa.Column("source_size", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("track_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("telemetry_transport", sa.String(length=64), nullable=False),
        sa.Column("worker_origin", sa.String(length=32), nullable=False),
        sa.Column("live_broadcast_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("camera_id", "frame_id", name="uq_tracking_frames_camera_frame"),
    )
    op.create_index(
        "ix_tracking_frames_camera_ts",
        "tracking_frames",
        ["camera_id", "ts"],
        unique=False,
    )
    op.alter_column("tracking_frames", "track_count", server_default=None)

    op.add_column(
        "tracking_events",
        sa.Column("frame_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("frame_sequence", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("stable_track_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("source_track_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("track_state", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("last_seen_age_ms", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("telemetry_transport", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("worker_origin", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tracking_events", "worker_origin")
    op.drop_column("tracking_events", "telemetry_transport")
    op.drop_column("tracking_events", "last_seen_age_ms")
    op.drop_column("tracking_events", "track_state")
    op.drop_column("tracking_events", "source_track_id")
    op.drop_column("tracking_events", "stable_track_id")
    op.drop_column("tracking_events", "frame_sequence")
    op.drop_column("tracking_events", "frame_id")

    op.drop_index("ix_tracking_frames_camera_ts", table_name="tracking_frames")
    op.drop_table("tracking_frames")
