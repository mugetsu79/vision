"""Add core support tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0036_core_support"
down_revision = "0035_core_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "support_bundles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column("include_logs", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "payload",
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_bundles_tenant_site_created",
        "support_bundles",
        ["tenant_id", "site_id", "created_at"],
    )
    op.create_index("ix_support_bundles_pack", "support_bundles", ["pack_id"])

    op.create_table(
        "support_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("operator_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "billable_duration_minutes",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "usage_meter_key",
            sa.String(length=128),
            server_default="support_session_hour",
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_sessions_tenant_site_status",
        "support_sessions",
        ["tenant_id", "site_id", "status"],
    )
    op.create_index("ix_support_sessions_operator", "support_sessions", ["operator_id"])

    op.create_table(
        "support_tunnels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("transport", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="requested", nullable=False),
        sa.Column("credential_ref", sa.String(length=256), nullable=False),
        sa.Column("credential_ref_hash", sa.String(length=64), nullable=False),
        sa.Column("relay_host", sa.String(length=255), nullable=False),
        sa.Column(
            "allowed_ports",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("dispatch_method", sa.String(length=64), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.String(length=255), nullable=True),
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_support_tunnels_tenant_site_status",
        "support_tunnels",
        ["tenant_id", "site_id", "status"],
    )
    op.create_index("ix_support_tunnels_node_status", "support_tunnels", ["node_id", "status"])

    op.create_table(
        "break_glass_access_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column(
            "scope",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(length=160), nullable=False),
        sa.Column("approver_id", sa.String(length=160), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closure_notes", sa.String(length=500), nullable=True),
        sa.Column(
            "audit_payload",
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_break_glass_records_tenant_started",
        "break_glass_access_records",
        ["tenant_id", "started_at"],
    )
    op.create_index("ix_break_glass_records_actor", "break_glass_access_records", ["actor_id"])

    op.create_table(
        "onboarding_check_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "checks",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_onboarding_check_runs_tenant_site_created",
        "onboarding_check_runs",
        ["tenant_id", "site_id", "created_at"],
    )
    op.create_index("ix_onboarding_check_runs_pack", "onboarding_check_runs", ["pack_id"])


def downgrade() -> None:
    op.drop_index("ix_onboarding_check_runs_pack", table_name="onboarding_check_runs")
    op.drop_index(
        "ix_onboarding_check_runs_tenant_site_created",
        table_name="onboarding_check_runs",
    )
    op.drop_table("onboarding_check_runs")
    op.drop_index("ix_break_glass_records_actor", table_name="break_glass_access_records")
    op.drop_index(
        "ix_break_glass_records_tenant_started",
        table_name="break_glass_access_records",
    )
    op.drop_table("break_glass_access_records")
    op.drop_index("ix_support_tunnels_node_status", table_name="support_tunnels")
    op.drop_index("ix_support_tunnels_tenant_site_status", table_name="support_tunnels")
    op.drop_table("support_tunnels")
    op.drop_index("ix_support_sessions_operator", table_name="support_sessions")
    op.drop_index("ix_support_sessions_tenant_site_status", table_name="support_sessions")
    op.drop_table("support_sessions")
    op.drop_index("ix_support_bundles_pack", table_name="support_bundles")
    op.drop_index("ix_support_bundles_tenant_site_created", table_name="support_bundles")
    op.drop_table("support_bundles")
