"""Add supervisor operations control-plane tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0022_supervisor_operations"
down_revision = "0021_cross_camera_threads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    worker_runtime_state_enum = postgresql.ENUM(
        "starting",
        "running",
        "stopped",
        "draining",
        "error",
        "unknown",
        name="worker_runtime_state_enum",
    )
    lifecycle_action_enum = postgresql.ENUM(
        "start",
        "stop",
        "restart",
        "drain",
        name="operations_lifecycle_action_enum",
    )
    lifecycle_status_enum = postgresql.ENUM(
        "requested",
        "acknowledged",
        "completed",
        "failed",
        name="operations_lifecycle_status_enum",
    )
    worker_runtime_state_enum.create(op.get_bind(), checkfirst=True)
    lifecycle_action_enum.create(op.get_bind(), checkfirst=True)
    lifecycle_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "worker_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("desired_state", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("supersedes_assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by_subject", sa.String(length=255), nullable=True),
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
            ["camera_id"],
            ["cameras.id"],
            name="fk_worker_assignments_camera",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_worker_assignments_edge",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_assignment_id"],
            ["worker_assignments.id"],
            name="fk_worker_assignments_supersedes",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_worker_assignments_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_worker_assignments_tenant_camera",
        "worker_assignments",
        ["tenant_id", "camera_id"],
    )
    op.create_index(
        "ix_worker_assignments_edge_active",
        "worker_assignments",
        ["edge_node_id", "active"],
    )

    op.create_table(
        "worker_runtime_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "runtime_state",
            postgresql.ENUM(
                "starting",
                "running",
                "stopped",
                "draining",
                "error",
                "unknown",
                name="worker_runtime_state_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("restart_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("runtime_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scene_contract_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["worker_assignments.id"],
            name="fk_worker_runtime_reports_assignment",
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_worker_runtime_reports_camera",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_worker_runtime_reports_edge",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_artifact_id"],
            ["model_runtime_artifacts.id"],
            name="fk_worker_runtime_reports_artifact",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_worker_runtime_reports_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_worker_reports_tenant_camera",
        "worker_runtime_reports",
        ["tenant_id", "camera_id", "heartbeat_at"],
    )
    op.create_index(
        "ix_worker_reports_assignment",
        "worker_runtime_reports",
        ["assignment_id"],
    )

    op.create_table(
        "operations_lifecycle_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "action",
            postgresql.ENUM(
                "start",
                "stop",
                "restart",
                "drain",
                name="operations_lifecycle_action_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "requested",
                "acknowledged",
                "completed",
                "failed",
                name="operations_lifecycle_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("requested_by_subject", sa.String(length=255), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "request_payload",
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
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["worker_assignments.id"],
            name="fk_lifecycle_requests_assignment",
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_lifecycle_requests_camera",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_lifecycle_requests_edge",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_lifecycle_requests_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_lifecycle_requests_tenant_camera",
        "operations_lifecycle_requests",
        ["tenant_id", "camera_id", "requested_at"],
    )
    op.create_index(
        "ix_lifecycle_requests_assignment",
        "operations_lifecycle_requests",
        ["assignment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_lifecycle_requests_assignment",
        table_name="operations_lifecycle_requests",
    )
    op.drop_index(
        "ix_lifecycle_requests_tenant_camera",
        table_name="operations_lifecycle_requests",
    )
    op.drop_table("operations_lifecycle_requests")
    op.drop_index("ix_worker_reports_assignment", table_name="worker_runtime_reports")
    op.drop_index("ix_worker_reports_tenant_camera", table_name="worker_runtime_reports")
    op.drop_table("worker_runtime_reports")
    op.drop_index("ix_worker_assignments_edge_active", table_name="worker_assignments")
    op.drop_index("ix_worker_assignments_tenant_camera", table_name="worker_assignments")
    op.drop_table("worker_assignments")
    postgresql.ENUM(name="operations_lifecycle_status_enum").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="operations_lifecycle_action_enum").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="worker_runtime_state_enum").drop(op.get_bind(), checkfirst=True)
