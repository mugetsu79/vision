"""Add core generic fleet baseline tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0031_core_fleet"
down_revision = "0030_core_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fleet_site_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        "ix_fleet_site_groups_tenant_kind",
        "fleet_site_groups",
        ["tenant_id", "kind"],
    )

    op.create_table(
        "fleet_hierarchy_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("node_id", sa.String(length=128), nullable=False),
        sa.Column("parent_id", sa.String(length=128), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        "ix_fleet_hierarchy_nodes_tenant_node",
        "fleet_hierarchy_nodes",
        ["tenant_id", "node_id"],
        unique=True,
    )
    op.create_index(
        "ix_fleet_hierarchy_nodes_tenant_parent",
        "fleet_hierarchy_nodes",
        ["tenant_id", "parent_id"],
    )
    op.create_index(
        "ix_fleet_hierarchy_nodes_tenant_site",
        "fleet_hierarchy_nodes",
        ["tenant_id", "site_id"],
    )

    op.create_table(
        "fleet_rotation_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column(
            "member_user_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "pack_labels",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "attributes",
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
        sa.UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_fleet_rotation_groups_tenant_id_id",
        ),
    )
    op.create_index(
        "ix_fleet_rotation_groups_tenant_label",
        "fleet_rotation_groups",
        ["tenant_id", "label"],
    )

    op.create_table(
        "fleet_site_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("heartbeat_status", sa.String(length=32), nullable=False),
        sa.Column("link_state", sa.String(length=32), nullable=False),
        sa.Column("runtime_status", sa.String(length=32), nullable=False),
        sa.Column("evidence_backlog_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("active_incident_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("privacy_status", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column(
            "model_artifact_status",
            sa.String(length=32),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.CheckConstraint(
            "heartbeat_status IN ('unknown', 'healthy', 'stale', 'offline')",
            name="ck_fleet_site_states_heartbeat_status",
        ),
        sa.CheckConstraint(
            "link_state IN ('unknown', 'healthy', 'degraded', 'dark', 'recovering', 'port_wifi')",
            name="ck_fleet_site_states_link_state",
        ),
        sa.CheckConstraint(
            "runtime_status IN ('unknown', 'running', 'degraded', 'stopped')",
            name="ck_fleet_site_states_runtime_status",
        ),
        sa.CheckConstraint(
            "privacy_status IN ('unknown', 'ok', 'mismatch')",
            name="ck_fleet_site_states_privacy_status",
        ),
        sa.CheckConstraint(
            "model_artifact_status IN ('unknown', 'ok', 'mismatch')",
            name="ck_fleet_site_states_model_artifact_status",
        ),
    )
    op.create_index(
        "ix_fleet_site_states_tenant_site",
        "fleet_site_states",
        ["tenant_id", "site_id"],
        unique=True,
    )

    op.create_table(
        "fleet_site_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_type", sa.String(length=32), nullable=False),
        sa.Column("assignee_id", sa.String(length=160), nullable=False),
        sa.Column("rotation_group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.ForeignKeyConstraint(
            ["tenant_id", "rotation_group_id"],
            ["fleet_rotation_groups.tenant_id", "fleet_rotation_groups.id"],
            name="fk_fleet_site_assignments_rotation_group_tenant",
        ),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "assignee_type IN ('support_queue', 'user', 'team', 'service_account')",
            name="ck_fleet_site_assignments_assignee_type",
        ),
    )
    op.create_index(
        "ix_fleet_site_assignments_tenant_site",
        "fleet_site_assignments",
        ["tenant_id", "site_id"],
    )
    op.create_index(
        "ix_fleet_site_assignments_tenant_assignee",
        "fleet_site_assignments",
        ["tenant_id", "assignee_type", "assignee_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_fleet_site_assignments_tenant_assignee",
        table_name="fleet_site_assignments",
    )
    op.drop_index("ix_fleet_site_assignments_tenant_site", table_name="fleet_site_assignments")
    op.drop_table("fleet_site_assignments")

    op.drop_index("ix_fleet_site_states_tenant_site", table_name="fleet_site_states")
    op.drop_table("fleet_site_states")

    op.drop_index("ix_fleet_rotation_groups_tenant_label", table_name="fleet_rotation_groups")
    op.drop_table("fleet_rotation_groups")

    op.drop_index("ix_fleet_hierarchy_nodes_tenant_site", table_name="fleet_hierarchy_nodes")
    op.drop_index("ix_fleet_hierarchy_nodes_tenant_parent", table_name="fleet_hierarchy_nodes")
    op.drop_index("ix_fleet_hierarchy_nodes_tenant_node", table_name="fleet_hierarchy_nodes")
    op.drop_table("fleet_hierarchy_nodes")

    op.drop_index("ix_fleet_site_groups_tenant_kind", table_name="fleet_site_groups")
    op.drop_table("fleet_site_groups")
