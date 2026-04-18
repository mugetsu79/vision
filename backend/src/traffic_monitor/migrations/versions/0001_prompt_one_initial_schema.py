"""Prompt 1 initial schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_prompt_one_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


role_enum = postgresql.ENUM(
    "viewer", "operator", "admin", "superadmin", name="role_enum", create_type=False
)
processing_mode_enum = postgresql.ENUM(
    "central", "edge", "hybrid", name="processing_mode_enum", create_type=False
)
tracker_type_enum = postgresql.ENUM(
    "botsort", "bytetrack", "ocsort", name="tracker_type_enum", create_type=False
)
model_task_enum = postgresql.ENUM(
    "detect", "classify", "attribute", name="model_task_enum", create_type=False
)
model_format_enum = postgresql.ENUM("onnx", "engine", name="model_format_enum", create_type=False)
rule_action_enum = postgresql.ENUM(
    "count", "alert", "record_clip", "webhook", name="rule_action_enum", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()

    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    role_enum.create(bind, checkfirst=True)
    processing_mode_enum.create(bind, checkfirst=True)
    tracker_type_enum.create(bind, checkfirst=True)
    model_task_enum.create(bind, checkfirst=True)
    model_format_enum.create(bind, checkfirst=True)
    rule_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("oidc_sub", sa.String(length=255), nullable=False, unique=True),
        sa.Column("role", role_enum, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("hashed_key", sa.String(length=255), nullable=False),
        sa.Column("scope", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "sites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tz", sa.String(length=64), nullable=False),
        sa.Column("geo_point", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "edge_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False
        ),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("task", model_task_enum, nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("format", model_format_enum, nullable=False),
        sa.Column("classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_shape", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("license", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=False
        ),
        sa.Column(
            "edge_node_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("edge_nodes.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("rtsp_url_encrypted", sa.Text(), nullable=False),
        sa.Column("processing_mode", processing_mode_enum, nullable=False),
        sa.Column(
            "primary_model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("models.id"),
            nullable=False,
        ),
        sa.Column(
            "secondary_model_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("models.id"),
            nullable=True,
        ),
        sa.Column("tracker_type", tracker_type_enum, nullable=False),
        sa.Column("active_classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attribute_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("zones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("homography", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("privacy", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("frame_skip", sa.Integer(), nullable=False),
        sa.Column("fps_cap", sa.Integer(), nullable=False),
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
    )
    op.create_table(
        "detection_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=False
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("zone_id", sa.String(length=255), nullable=True),
        sa.Column("predicate", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action", rule_action_enum, nullable=False),
        sa.Column("webhook_url", sa.Text(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
    )
    op.create_table(
        "tracking_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=False
        ),
        sa.Column("class_name", sa.String(length=255), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("speed_kph", sa.Float(), nullable=True),
        sa.Column("direction_deg", sa.Float(), nullable=True),
        sa.Column("zone_id", sa.String(length=255), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_table(
        "rule_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=False
        ),
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("detection_rules.id"),
            nullable=False,
        ),
        sa.Column("event_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot_url", sa.Text(), nullable=True),
    )
    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cameras.id"), nullable=False
        ),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot_url", sa.Text(), nullable=True),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False
        ),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("target", sa.String(length=255), nullable=False),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
    )

    op.execute("SELECT create_hypertable('tracking_events', 'ts', if_not_exists => TRUE)")
    op.execute("SELECT create_hypertable('rule_events', 'ts', if_not_exists => TRUE)")
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS events_1m
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 minute', ts) AS bucket,
              camera_id,
              class_name,
              COUNT(*) AS event_count
            FROM tracking_events
            GROUP BY bucket, camera_id, class_name
            """
        )
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS events_1h
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 hour', ts) AS bucket,
              camera_id,
              class_name,
              COUNT(*) AS event_count
            FROM tracking_events
            GROUP BY bucket, camera_id, class_name
            """
        )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS events_1h")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS events_1m")
    op.drop_table("audit_log")
    op.drop_table("incidents")
    op.drop_table("rule_events")
    op.drop_table("tracking_events")
    op.drop_table("detection_rules")
    op.drop_table("cameras")
    op.drop_table("models")
    op.drop_table("edge_nodes")
    op.drop_table("sites")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("tenants")

    bind = op.get_bind()
    rule_action_enum.drop(bind, checkfirst=True)
    model_format_enum.drop(bind, checkfirst=True)
    model_task_enum.drop(bind, checkfirst=True)
    tracker_type_enum.drop(bind, checkfirst=True)
    processing_mode_enum.drop(bind, checkfirst=True)
    role_enum.drop(bind, checkfirst=True)
