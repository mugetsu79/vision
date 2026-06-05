"""Add core link baseline tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0030_core_link"
down_revision = "0029_runtime_artifact_timestamps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "link_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monthly_bytes", sa.BigInteger(), nullable=False),
        sa.Column("bulk_daily_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "policy",
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_budgets_tenant_site",
        "link_budgets",
        ["tenant_id", "site_id"],
        unique=True,
    )

    op.create_table(
        "link_queue_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority_lane", sa.String(length=32), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("source_object_type", sa.String(length=64), nullable=False),
        sa.Column("source_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("pause_reason", sa.Text(), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_successful_transfer_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["evidence_artifact_id"], ["evidence_artifacts.id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_queue_items_tenant_site_lane",
        "link_queue_items",
        ["tenant_id", "site_id", "priority_lane"],
    )
    op.create_index("ix_link_queue_items_incident", "link_queue_items", ["incident_id"])

    op.create_table(
        "link_transfer_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("bytes_transferred", sa.BigInteger(), nullable=False),
        sa.Column("resume_token", sa.Text(), nullable=True),
        sa.Column("interruption_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["queue_item_id"], ["link_queue_items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_transfer_attempts_queue_item",
        "link_transfer_attempts",
        ["queue_item_id", "created_at"],
    )

    op.create_table(
        "link_health_probes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("throughput_mbps", sa.Float(), nullable=False),
        sa.Column("packet_loss_percent", sa.Float(), nullable=False),
        sa.Column("reachable", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_health_probes_tenant_site_recorded",
        "link_health_probes",
        ["tenant_id", "site_id", "recorded_at"],
    )

    op.create_table(
        "link_passport_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column("link_state", sa.String(length=32), nullable=False),
        sa.Column("passport_hash", sa.String(length=64), nullable=False),
        sa.Column("passport", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["evidence_artifact_id"], ["evidence_artifacts.id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_passports_tenant_site_created",
        "link_passport_snapshots",
        ["tenant_id", "site_id", "created_at"],
    )
    op.create_index("ix_link_passports_incident", "link_passport_snapshots", ["incident_id"])
    op.create_index(
        "ix_link_passports_hash",
        "link_passport_snapshots",
        ["passport_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_link_passports_hash", table_name="link_passport_snapshots")
    op.drop_index("ix_link_passports_incident", table_name="link_passport_snapshots")
    op.drop_index(
        "ix_link_passports_tenant_site_created",
        table_name="link_passport_snapshots",
    )
    op.drop_table("link_passport_snapshots")

    op.drop_index(
        "ix_link_health_probes_tenant_site_recorded",
        table_name="link_health_probes",
    )
    op.drop_table("link_health_probes")

    op.drop_index("ix_link_transfer_attempts_queue_item", table_name="link_transfer_attempts")
    op.drop_table("link_transfer_attempts")

    op.drop_index("ix_link_queue_items_incident", table_name="link_queue_items")
    op.drop_index("ix_link_queue_items_tenant_site_lane", table_name="link_queue_items")
    op.drop_table("link_queue_items")

    op.drop_index("ix_link_budgets_tenant_site", table_name="link_budgets")
    op.drop_table("link_budgets")
