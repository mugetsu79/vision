"""Add central model edge lifecycle tables."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0042_model_edge_lifecycle"
down_revision: str | Sequence[str] | None = "0041_core_link_reflector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MODEL_LIFECYCLE_JOB_STATUS_VALUES = (
    "queued",
    "accepted",
    "running",
    "succeeded",
    "failed",
    "cancelled",
)

model_import_source_enum = postgresql.ENUM(
    "catalog",
    "url",
    "master_path",
    "upload",
    name="model_import_source_enum",
    create_type=False,
)
model_lifecycle_job_status_enum = postgresql.ENUM(
    *MODEL_LIFECYCLE_JOB_STATUS_VALUES,
    name="model_lifecycle_job_status_enum",
    create_type=False,
)
deployment_model_assignment_status_enum = postgresql.ENUM(
    "desired",
    "syncing",
    "synced",
    "failed",
    "removed",
    name="deployment_model_assignment_status_enum",
    create_type=False,
)
deployment_model_sync_job_status_enum = postgresql.ENUM(
    *MODEL_LIFECYCLE_JOB_STATUS_VALUES,
    name="deployment_model_sync_job_status_enum",
    create_type=False,
)
runtime_artifact_build_job_status_enum = postgresql.ENUM(
    *MODEL_LIFECYCLE_JOB_STATUS_VALUES,
    name="runtime_artifact_build_job_status_enum",
    create_type=False,
)
runtime_artifact_build_format_enum = postgresql.ENUM(
    "onnx_export",
    "tensorrt_engine",
    name="runtime_artifact_build_format_enum",
    create_type=False,
)
runtime_artifact_build_precision_enum = postgresql.ENUM(
    "fp32",
    "fp16",
    "int8",
    name="runtime_artifact_build_precision_enum",
    create_type=False,
)
supervisor_model_job_event_status_enum = postgresql.ENUM(
    *MODEL_LIFECYCLE_JOB_STATUS_VALUES,
    name="supervisor_model_job_event_status_enum",
    create_type=False,
)
edge_configuration_apply_status_enum = postgresql.ENUM(
    "pending",
    "applied",
    "failed",
    name="edge_configuration_apply_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (
        model_import_source_enum,
        model_lifecycle_job_status_enum,
        deployment_model_assignment_status_enum,
        deployment_model_sync_job_status_enum,
        runtime_artifact_build_job_status_enum,
        runtime_artifact_build_format_enum,
        runtime_artifact_build_precision_enum,
        supervisor_model_job_event_status_enum,
        edge_configuration_apply_status_enum,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "model_import_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_id", sa.String(length=128), nullable=True),
        sa.Column("source", model_import_source_enum, nullable=False),
        sa.Column("status", model_lifecycle_job_status_enum, nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("target_path", sa.Text(), nullable=False),
        sa.Column("expected_sha256", sa.String(length=64), nullable=True),
        sa.Column("observed_sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "progress",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_import_jobs_status",
        "model_import_jobs",
        ["status", "created_at"],
    )
    op.create_index("ix_model_import_jobs_catalog", "model_import_jobs", ["catalog_id"])

    op.create_table(
        "deployment_model_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", deployment_model_assignment_status_enum, nullable=False),
        sa.Column("desired_path", sa.Text(), nullable=True),
        sa.Column("last_sync_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deployment_node_id",
            "model_id",
            name="uq_deployment_model_assignment",
        ),
    )
    op.create_index(
        "ix_deployment_model_assignment_node",
        "deployment_model_assignments",
        ["deployment_node_id"],
    )

    op.create_table(
        "deployment_model_sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", deployment_model_sync_job_status_enum, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("claimed_by_supervisor_id", sa.String(length=128), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.ForeignKeyConstraint(["assignment_id"], ["deployment_model_assignments.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deployment_model_sync_jobs_node",
        "deployment_model_sync_jobs",
        ["deployment_node_id", "status"],
    )
    op.create_index(
        "ix_deployment_model_sync_jobs_assignment",
        "deployment_model_sync_jobs",
        ["assignment_id"],
    )
    op.create_foreign_key(
        "fk_deployment_model_assignments_last_sync_job",
        "deployment_model_assignments",
        "deployment_model_sync_jobs",
        ["last_sync_job_id"],
        ["id"],
    )

    op.create_table(
        "deployment_model_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_kind", sa.String(length=32), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("target_profile", sa.String(length=128), nullable=True),
        sa.Column(
            "runtime_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deployment_node_id",
            "asset_kind",
            "asset_id",
            "sha256",
            name="uq_deployment_model_inventory_asset",
        ),
    )
    op.create_index(
        "ix_deployment_model_inventory_node",
        "deployment_model_inventory",
        ["deployment_node_id"],
    )

    op.create_table(
        "runtime_artifact_build_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", runtime_artifact_build_job_status_enum, nullable=False),
        sa.Column("build_format", runtime_artifact_build_format_enum, nullable=False),
        sa.Column("target_profile", sa.String(length=128), nullable=False),
        sa.Column("precision", runtime_artifact_build_precision_enum, nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["artifact_id"], ["model_runtime_artifacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_artifact_build_jobs_node",
        "runtime_artifact_build_jobs",
        ["deployment_node_id", "status"],
    )
    op.create_index(
        "ix_runtime_artifact_build_jobs_model",
        "runtime_artifact_build_jobs",
        ["model_id", "created_at"],
    )

    op.create_table(
        "supervisor_model_job_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_kind", sa.String(length=64), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", supervisor_model_job_event_status_enum, nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_supervisor_model_job_events_job",
        "supervisor_model_job_events",
        ["job_kind", "job_id", "created_at"],
    )

    op.create_table(
        "edge_configuration_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deployment_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "desired_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("applied_revision", sa.Integer(), nullable=True),
        sa.Column("apply_status", edge_configuration_apply_status_enum, nullable=False),
        sa.Column("last_applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actor_subject", sa.String(length=255), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["deployment_node_id"], ["deployment_nodes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "deployment_node_id",
            name="uq_edge_configuration_assignment_node",
        ),
    )


def downgrade() -> None:
    op.drop_table("edge_configuration_assignments")

    op.drop_index(
        "ix_supervisor_model_job_events_job",
        table_name="supervisor_model_job_events",
    )
    op.drop_table("supervisor_model_job_events")

    op.drop_index(
        "ix_runtime_artifact_build_jobs_model",
        table_name="runtime_artifact_build_jobs",
    )
    op.drop_index(
        "ix_runtime_artifact_build_jobs_node",
        table_name="runtime_artifact_build_jobs",
    )
    op.drop_table("runtime_artifact_build_jobs")

    op.drop_index(
        "ix_deployment_model_inventory_node",
        table_name="deployment_model_inventory",
    )
    op.drop_table("deployment_model_inventory")

    op.drop_constraint(
        "fk_deployment_model_assignments_last_sync_job",
        "deployment_model_assignments",
        type_="foreignkey",
    )

    op.drop_index(
        "ix_deployment_model_sync_jobs_assignment",
        table_name="deployment_model_sync_jobs",
    )
    op.drop_index(
        "ix_deployment_model_sync_jobs_node",
        table_name="deployment_model_sync_jobs",
    )
    op.drop_table("deployment_model_sync_jobs")

    op.drop_index(
        "ix_deployment_model_assignment_node",
        table_name="deployment_model_assignments",
    )
    op.drop_table("deployment_model_assignments")

    op.drop_index("ix_model_import_jobs_catalog", table_name="model_import_jobs")
    op.drop_index("ix_model_import_jobs_status", table_name="model_import_jobs")
    op.drop_table("model_import_jobs")

    bind = op.get_bind()
    for enum_type in (
        edge_configuration_apply_status_enum,
        supervisor_model_job_event_status_enum,
        runtime_artifact_build_precision_enum,
        runtime_artifact_build_format_enum,
        runtime_artifact_build_job_status_enum,
        deployment_model_sync_job_status_enum,
        deployment_model_assignment_status_enum,
        model_lifecycle_job_status_enum,
        model_import_source_enum,
    ):
        enum_type.drop(bind, checkfirst=True)
