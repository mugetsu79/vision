"""Add Prompt 12 count event storage and aggregates."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_prompt12_count_events"
down_revision = "0003_prompt11_quota"
branch_labels = None
depends_on = None


count_event_type_enum = postgresql.ENUM(
    "line_cross",
    "zone_enter",
    "zone_exit",
    name="count_event_type_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    count_event_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "count_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id"),
            nullable=False,
        ),
        sa.Column("class_name", sa.String(length=255), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("event_type", count_event_type_enum, nullable=False),
        sa.Column("boundary_id", sa.String(length=255), nullable=False),
        sa.Column("direction", sa.String(length=64), nullable=True),
        sa.Column("from_zone_id", sa.String(length=255), nullable=True),
        sa.Column("to_zone_id", sa.String(length=255), nullable=True),
        sa.Column("speed_kph", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.alter_column("count_events", "payload", server_default=None)
    op.execute("SELECT create_hypertable('count_events', 'ts', if_not_exists => TRUE)")

    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS count_events_1m
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 minute', ts) AS bucket,
              camera_id,
              class_name,
              boundary_id,
              event_type,
              COUNT(*) AS event_count
            FROM count_events
            GROUP BY bucket, camera_id, class_name, boundary_id, event_type
            """
        )
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS count_events_1h
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 hour', ts) AS bucket,
              camera_id,
              class_name,
              boundary_id,
              event_type,
              COUNT(*) AS event_count
            FROM count_events
            GROUP BY bucket, camera_id, class_name, boundary_id, event_type
            """
        )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS count_events_1h")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS count_events_1m")
    op.drop_table("count_events")
    bind = op.get_bind()
    count_event_type_enum.drop(bind, checkfirst=True)
