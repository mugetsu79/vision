"""Add maritime FleetOps telemetry tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0033_maritime_telemetry"
down_revision = "0032_maritime_pack"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maritime_ais_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mmsi", sa.String(length=16), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("speed_over_ground", sa.Float(), nullable=True),
        sa.Column("course_over_ground", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("navigational_status", sa.String(length=80), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="ck_maritime_ais_positions_latitude",
        ),
        sa.CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="ck_maritime_ais_positions_longitude",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "source",
            "mmsi",
            "reported_at",
            "latitude",
            "longitude",
            name="uq_maritime_ais_positions_tenant_source_mmsi_reported_position",
        ),
    )
    op.create_index(
        "ix_maritime_ais_positions_tenant_vessel_reported",
        "maritime_ais_positions",
        ["tenant_id", "vessel_id", "reported_at"],
    )

    op.create_table(
        "maritime_nmea_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sentence_type", sa.String(length=16), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("raw_sentence", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_nmea_readings_tenant_vessel_created",
        "maritime_nmea_readings",
        ["tenant_id", "vessel_id", "created_at"],
    )

    op.create_table(
        "maritime_carrier_terminals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("terminal_id", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=80), server_default="generic", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("link_state", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("downlink_mbps", sa.Float(), nullable=True),
        sa.Column("uplink_mbps", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("packet_loss_percent", sa.Float(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "status IN ('unknown', 'online', 'degraded', 'offline', 'blocked')",
            name="ck_maritime_carrier_terminals_status",
        ),
        sa.CheckConstraint(
            (
                "link_state IN ("
                "'unknown', 'satellite_good', 'satellite_degraded', "
                "'port_wifi', 'dark', 'recovering'"
                ")"
            ),
            name="ck_maritime_carrier_terminals_link_state",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "terminal_id",
            name="uq_maritime_carrier_terminals_tenant_terminal",
        ),
    )
    op.create_index(
        "ix_maritime_carrier_terminals_tenant_vessel",
        "maritime_carrier_terminals",
        ["tenant_id", "vessel_id"],
    )

    op.create_table(
        "maritime_telemetry_ingest_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.String(length=255), nullable=True),
        sa.Column("failure_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('succeeded', 'partial', 'failed')",
            name="ck_maritime_telemetry_ingest_events_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_telemetry_ingest_events_tenant_created",
        "maritime_telemetry_ingest_events",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maritime_telemetry_ingest_events_tenant_created",
        table_name="maritime_telemetry_ingest_events",
    )
    op.drop_table("maritime_telemetry_ingest_events")
    op.drop_index(
        "ix_maritime_carrier_terminals_tenant_vessel",
        table_name="maritime_carrier_terminals",
    )
    op.drop_table("maritime_carrier_terminals")
    op.drop_index(
        "ix_maritime_nmea_readings_tenant_vessel_created",
        table_name="maritime_nmea_readings",
    )
    op.drop_table("maritime_nmea_readings")
    op.drop_index(
        "ix_maritime_ais_positions_tenant_vessel_reported",
        table_name="maritime_ais_positions",
    )
    op.drop_table("maritime_ais_positions")
