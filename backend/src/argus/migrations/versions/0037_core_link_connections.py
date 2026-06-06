"""Add core link connections."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0037_core_link_connections"
down_revision = "0036_core_support"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "link_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("transport_kind", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("priority_rank", sa.Integer(), server_default=sa.text("100"), nullable=False),
        sa.Column(
            "availability_scope",
            sa.String(length=32),
            server_default="always",
            nullable=False,
        ),
        sa.Column("metered", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("monthly_bytes", sa.BigInteger(), nullable=True),
        sa.Column("bulk_daily_bytes", sa.BigInteger(), nullable=True),
        sa.Column("expected_downlink_mbps", sa.Float(), nullable=True),
        sa.Column("expected_uplink_mbps", sa.Float(), nullable=True),
        sa.Column("expected_latency_ms", sa.Integer(), nullable=True),
        sa.Column("packet_loss_percent", sa.Float(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata",
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
            "transport_kind IN ('satellite', 'lte', '5g', 'wifi', 'fiber', 'ethernet', 'other')",
            name="ck_link_connections_transport_kind",
        ),
        sa.CheckConstraint(
            "status IN ('unknown', 'online', 'degraded', 'offline', 'blocked', 'recovering')",
            name="ck_link_connections_status",
        ),
        sa.CheckConstraint(
            "availability_scope IN ('always', 'remote', 'nearby', 'local', 'maintenance')",
            name="ck_link_connections_availability_scope",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_connections_tenant_site_rank",
        "link_connections",
        ["tenant_id", "site_id", "priority_rank"],
    )
    op.add_column(
        "link_health_probes",
        sa.Column("connection_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_link_health_probes_connection",
        "link_health_probes",
        ["connection_id"],
    )
    op.create_foreign_key(
        "fk_link_health_probes_connection_id",
        "link_health_probes",
        "link_connections",
        ["connection_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_link_health_probes_connection_id",
        "link_health_probes",
        type_="foreignkey",
    )
    op.drop_index("ix_link_health_probes_connection", table_name="link_health_probes")
    op.drop_column("link_health_probes", "connection_id")
    op.drop_index("ix_link_connections_tenant_site_rank", table_name="link_connections")
    op.drop_table("link_connections")
