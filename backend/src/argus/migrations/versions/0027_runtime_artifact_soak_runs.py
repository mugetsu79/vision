"""Add runtime artifact soak run records."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0027_runtime_artifact_soak_runs"
down_revision = "0026_node_credential_rotation"
branch_labels = None
depends_on = None


soak_status_enum = postgresql.ENUM(
    "passed",
    "failed",
    name="runtime_artifact_soak_status_enum",
    create_type=False,
)
runtime_kind_enum = postgresql.ENUM(
    "onnx_export",
    "tensorrt_engine",
    "compiled_open_vocab",
    name="runtime_artifact_kind_enum",
    create_type=False,
)
detector_capability_enum = postgresql.ENUM(
    "fixed_vocab",
    "open_vocab",
    name="admission_detector_capability_enum",
    create_type=False,
)
admission_status_enum = postgresql.ENUM(
    "recommended",
    "supported",
    "degraded",
    "unsupported",
    "unknown",
    name="model_admission_status_enum",
    create_type=False,
)


def upgrade() -> None:
    soak_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "runtime_artifact_soak_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("runtime_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("runtime_kind", runtime_kind_enum, nullable=False),
        sa.Column("runtime_backend", sa.String(length=64), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("model_capability", detector_capability_enum, nullable=True),
        sa.Column("target_profile", sa.String(length=128), nullable=False),
        sa.Column("status", soak_status_enum, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("fallback_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("operations_assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "runtime_selection_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("runtime_selection_profile_hash", sa.String(length=64), nullable=True),
        sa.Column("hardware_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_admission_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hardware_admission_status", admission_status_enum, nullable=True),
        sa.Column("model_recommendation_rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_runtime_soak_camera",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_runtime_soak_edge",
        ),
        sa.ForeignKeyConstraint(
            ["hardware_report_id"],
            ["edge_node_hardware_reports.id"],
            name="fk_runtime_soak_hardware",
        ),
        sa.ForeignKeyConstraint(
            ["model_admission_report_id"],
            ["worker_model_admission_reports.id"],
            name="fk_runtime_soak_admission",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
            name="fk_runtime_soak_model",
        ),
        sa.ForeignKeyConstraint(
            ["operations_assignment_id"],
            ["worker_assignments.id"],
            name="fk_runtime_soak_assignment",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_artifact_id"],
            ["model_runtime_artifacts.id"],
            name="fk_runtime_soak_artifact",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_selection_profile_id"],
            ["operator_config_profiles.id"],
            name="fk_runtime_soak_profile",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_runtime_soak_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_soak_artifact_started",
        "runtime_artifact_soak_runs",
        ["runtime_artifact_id", "started_at"],
    )
    op.create_index(
        "ix_runtime_soak_edge_started",
        "runtime_artifact_soak_runs",
        ["edge_node_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_soak_edge_started", table_name="runtime_artifact_soak_runs")
    op.drop_index("ix_runtime_soak_artifact_started", table_name="runtime_artifact_soak_runs")
    op.drop_table("runtime_artifact_soak_runs")
    soak_status_enum.drop(op.get_bind(), checkfirst=True)
