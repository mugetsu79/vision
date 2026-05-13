"""Add installable supervisor deployment node state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0024_installable_supervisor"
down_revision = "0023_supervisor_reconciler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    deployment_node_kind_enum = postgresql.ENUM(
        "central",
        "edge",
        name="deployment_node_kind_enum",
    )
    deployment_install_status_enum = postgresql.ENUM(
        "not_installed",
        "pairing_pending",
        "installed",
        "healthy",
        "degraded",
        "offline",
        "revoked",
        name="deployment_install_status_enum",
    )
    deployment_credential_status_enum = postgresql.ENUM(
        "missing",
        "pending",
        "active",
        "expired",
        "revoked",
        name="deployment_credential_status_enum",
    )
    deployment_service_manager_enum = postgresql.ENUM(
        "systemd",
        "launchd",
        "compose",
        "direct_child",
        "unknown",
        name="deployment_service_manager_enum",
    )
    report_node_kind_enum = postgresql.ENUM(
        "central",
        "edge",
        name="deployment_report_node_kind_enum",
    )
    report_service_manager_enum = postgresql.ENUM(
        "systemd",
        "launchd",
        "compose",
        "direct_child",
        "unknown",
        name="deployment_report_service_manager_enum",
    )
    report_install_status_enum = postgresql.ENUM(
        "not_installed",
        "pairing_pending",
        "installed",
        "healthy",
        "degraded",
        "offline",
        "revoked",
        name="deployment_report_install_status_enum",
    )
    report_credential_status_enum = postgresql.ENUM(
        "missing",
        "pending",
        "active",
        "expired",
        "revoked",
        name="deployment_report_credential_status_enum",
    )
    pairing_session_node_kind_enum = postgresql.ENUM(
        "central",
        "edge",
        name="pairing_session_node_kind_enum",
    )
    supervisor_credential_status_enum = postgresql.ENUM(
        "missing",
        "pending",
        "active",
        "expired",
        "revoked",
        name="supervisor_credential_status_enum",
    )
    for enum_type in (
        deployment_node_kind_enum,
        deployment_install_status_enum,
        deployment_credential_status_enum,
        deployment_service_manager_enum,
        report_node_kind_enum,
        report_service_manager_enum,
        report_install_status_enum,
        report_credential_status_enum,
        pairing_session_node_kind_enum,
        supervisor_credential_status_enum,
    ):
        enum_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "deployment_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "node_kind",
            postgresql.ENUM(
                "central",
                "edge",
                name="deployment_node_kind_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "install_status",
            postgresql.ENUM(
                "not_installed",
                "pairing_pending",
                "installed",
                "healthy",
                "degraded",
                "offline",
                "revoked",
                name="deployment_install_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "credential_status",
            postgresql.ENUM(
                "missing",
                "pending",
                "active",
                "expired",
                "revoked",
                name="deployment_credential_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "service_manager",
            postgresql.ENUM(
                "systemd",
                "launchd",
                "compose",
                "direct_child",
                "unknown",
                name="deployment_service_manager_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("service_status", sa.String(length=64), nullable=True),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("os_name", sa.String(length=64), nullable=True),
        sa.Column("host_profile", sa.String(length=128), nullable=True),
        sa.Column("last_service_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "diagnostics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
            "(node_kind = 'central' AND edge_node_id IS NULL) "
            "OR (node_kind = 'edge' AND edge_node_id IS NOT NULL)",
            name="ck_deploy_nodes_kind_edge",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_deploy_nodes_tenant"),
        sa.ForeignKeyConstraint(["edge_node_id"], ["edge_nodes.id"], name="fk_deploy_nodes_edge"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "supervisor_id", name="uq_deploy_nodes_supervisor"),
    )
    op.create_index("ix_deploy_nodes_tenant_kind", "deployment_nodes", ["tenant_id", "node_kind"])
    op.create_index("ix_deploy_nodes_edge", "deployment_nodes", ["edge_node_id"])

    op.create_table(
        "supervisor_service_status_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_id", sa.String(length=128), nullable=False),
        sa.Column(
            "node_kind",
            postgresql.ENUM(
                "central",
                "edge",
                name="deployment_report_node_kind_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column(
            "service_manager",
            postgresql.ENUM(
                "systemd",
                "launchd",
                "compose",
                "direct_child",
                "unknown",
                name="deployment_report_service_manager_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("service_status", sa.String(length=64), nullable=False),
        sa.Column(
            "install_status",
            postgresql.ENUM(
                "not_installed",
                "pairing_pending",
                "installed",
                "healthy",
                "degraded",
                "offline",
                "revoked",
                name="deployment_report_install_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "credential_status",
            postgresql.ENUM(
                "missing",
                "pending",
                "active",
                "expired",
                "revoked",
                name="deployment_report_credential_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("version", sa.String(length=64), nullable=True),
        sa.Column("os_name", sa.String(length=64), nullable=False),
        sa.Column("host_profile", sa.String(length=128), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "diagnostics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(node_kind = 'central' AND edge_node_id IS NULL) "
            "OR (node_kind = 'edge' AND edge_node_id IS NOT NULL)",
            name="ck_svc_reports_kind_edge",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_svc_reports_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_node_id"],
            ["deployment_nodes.id"],
            name="fk_svc_reports_node",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_svc_reports_edge",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_svc_reports_node_heartbeat",
        "supervisor_service_status_reports",
        ["deployment_node_id", "heartbeat_at"],
    )
    op.create_index(
        "ix_svc_reports_supervisor",
        "supervisor_service_status_reports",
        ["tenant_id", "supervisor_id", "heartbeat_at"],
    )

    op.create_table(
        "node_pairing_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "node_kind",
            postgresql.ENUM(
                "central",
                "edge",
                name="pairing_session_node_kind_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("pairing_code_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by_supervisor", sa.String(length=128), nullable=True),
        sa.Column("created_by_subject", sa.String(length=255), nullable=True),
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
            ["tenant_id"],
            ["tenants.id"],
            name="fk_pairing_sessions_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_node_id"],
            ["deployment_nodes.id"],
            name="fk_pairing_sessions_node",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_pairing_sessions_edge",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pairing_sessions_tenant_status",
        "node_pairing_sessions",
        ["tenant_id", "status"],
    )
    op.create_index("ix_pairing_sessions_node", "node_pairing_sessions", ["deployment_node_id"])

    op.create_table(
        "supervisor_node_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supervisor_id", sa.String(length=128), nullable=False),
        sa.Column("credential_hash", sa.String(length=128), nullable=False),
        sa.Column("encrypted_credential", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "missing",
                "pending",
                "active",
                "expired",
                "revoked",
                name="supervisor_credential_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
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
            ["tenant_id"],
            ["tenants.id"],
            name="fk_node_credentials_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_node_id"],
            ["deployment_nodes.id"],
            name="fk_node_credentials_node",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_node_credentials_node_status",
        "supervisor_node_credentials",
        ["deployment_node_id", "status"],
    )
    op.create_index(
        "ix_node_credentials_tenant_status",
        "supervisor_node_credentials",
        ["tenant_id", "status"],
    )

    op.create_table(
        "deployment_credential_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_credential_events_tenant",
        ),
        sa.ForeignKeyConstraint(
            ["deployment_node_id"],
            ["deployment_nodes.id"],
            name="fk_credential_events_node",
        ),
        sa.ForeignKeyConstraint(
            ["credential_id"],
            ["supervisor_node_credentials.id"],
            name="fk_credential_events_credential",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_credential_events_node_time",
        "deployment_credential_events",
        ["deployment_node_id", "occurred_at"],
    )
    op.create_index(
        "ix_credential_events_tenant_time",
        "deployment_credential_events",
        ["tenant_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_credential_events_tenant_time", table_name="deployment_credential_events")
    op.drop_index("ix_credential_events_node_time", table_name="deployment_credential_events")
    op.drop_table("deployment_credential_events")

    op.drop_index("ix_node_credentials_tenant_status", table_name="supervisor_node_credentials")
    op.drop_index("ix_node_credentials_node_status", table_name="supervisor_node_credentials")
    op.drop_table("supervisor_node_credentials")

    op.drop_index("ix_pairing_sessions_node", table_name="node_pairing_sessions")
    op.drop_index("ix_pairing_sessions_tenant_status", table_name="node_pairing_sessions")
    op.drop_table("node_pairing_sessions")

    op.drop_index("ix_svc_reports_supervisor", table_name="supervisor_service_status_reports")
    op.drop_index(
        "ix_svc_reports_node_heartbeat",
        table_name="supervisor_service_status_reports",
    )
    op.drop_table("supervisor_service_status_reports")

    op.drop_index("ix_deploy_nodes_edge", table_name="deployment_nodes")
    op.drop_index("ix_deploy_nodes_tenant_kind", table_name="deployment_nodes")
    op.drop_table("deployment_nodes")

    for enum_name in (
        "supervisor_credential_status_enum",
        "pairing_session_node_kind_enum",
        "deployment_report_credential_status_enum",
        "deployment_report_install_status_enum",
        "deployment_report_service_manager_enum",
        "deployment_report_node_kind_enum",
        "deployment_service_manager_enum",
        "deployment_credential_status_enum",
        "deployment_install_status_enum",
        "deployment_node_kind_enum",
    ):
        postgresql.ENUM(name=enum_name).drop(op.get_bind(), checkfirst=True)
