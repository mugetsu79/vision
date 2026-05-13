"""Add supervisor hardware reports and model admission."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0023_supervisor_reconciler"
down_revision = "0022_supervisor_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    model_admission_status_enum = postgresql.ENUM(
        "recommended",
        "supported",
        "degraded",
        "unsupported",
        "unknown",
        name="model_admission_status_enum",
    )
    admission_detector_capability_enum = postgresql.ENUM(
        "fixed_vocab",
        "open_vocab",
        name="admission_detector_capability_enum",
    )
    model_admission_status_enum.create(op.get_bind(), checkfirst=True)
    admission_detector_capability_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "edge_node_hardware_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("supervisor_id", sa.String(length=128), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("host_profile", sa.String(length=128), nullable=False),
        sa.Column("os_name", sa.String(length=64), nullable=False),
        sa.Column("machine_arch", sa.String(length=64), nullable=False),
        sa.Column("cpu_model", sa.String(length=255), nullable=True),
        sa.Column("cpu_cores", sa.Integer(), nullable=True),
        sa.Column("memory_total_mb", sa.Integer(), nullable=True),
        sa.Column(
            "accelerators",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provider_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "observed_performance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("thermal_state", sa.String(length=64), nullable=True),
        sa.Column("report_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_hardware_reports_edge",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_hardware_reports_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supervisor_id",
            "report_hash",
            name="uq_hardware_reports_supervisor_hash",
        ),
    )
    op.create_index(
        "ix_hardware_reports_edge_reported",
        "edge_node_hardware_reports",
        ["edge_node_id", "reported_at"],
    )
    op.create_index(
        "ix_hardware_reports_tenant_reported",
        "edge_node_hardware_reports",
        ["tenant_id", "reported_at"],
    )

    op.create_table(
        "worker_model_admission_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("edge_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assignment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hardware_report_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "model_capability",
            postgresql.ENUM(
                "fixed_vocab",
                "open_vocab",
                name="admission_detector_capability_enum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("runtime_artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "runtime_selection_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "stream_profile",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "recommended",
                "supported",
                "degraded",
                "unsupported",
                "unknown",
                name="model_admission_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("selected_backend", sa.String(length=64), nullable=True),
        sa.Column("recommended_model_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("recommended_model_name", sa.String(length=255), nullable=True),
        sa.Column(
            "recommended_runtime_profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("recommended_backend", sa.String(length=64), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["worker_assignments.id"],
            name="fk_model_admissions_assignment",
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_model_admissions_camera",
        ),
        sa.ForeignKeyConstraint(
            ["edge_node_id"],
            ["edge_nodes.id"],
            name="fk_model_admissions_edge",
        ),
        sa.ForeignKeyConstraint(
            ["hardware_report_id"],
            ["edge_node_hardware_reports.id"],
            name="fk_model_admissions_hardware",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["models.id"],
            name="fk_model_admissions_model",
        ),
        sa.ForeignKeyConstraint(
            ["recommended_model_id"],
            ["models.id"],
            name="fk_model_admissions_rec_model",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_artifact_id"],
            ["model_runtime_artifacts.id"],
            name="fk_model_admissions_artifact",
        ),
        sa.ForeignKeyConstraint(
            ["runtime_selection_profile_id"],
            ["operator_config_profiles.id"],
            name="fk_model_admissions_profile",
        ),
        sa.ForeignKeyConstraint(
            ["recommended_runtime_profile_id"],
            ["operator_config_profiles.id"],
            name="fk_model_admissions_rec_profile",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_model_admissions_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_admissions_camera_eval",
        "worker_model_admission_reports",
        ["camera_id", "evaluated_at"],
    )
    op.create_index(
        "ix_model_admissions_edge_eval",
        "worker_model_admission_reports",
        ["edge_node_id", "evaluated_at"],
    )
    op.create_index(
        "ix_model_admissions_status_eval",
        "worker_model_admission_reports",
        ["status", "evaluated_at"],
    )

    op.add_column(
        "operations_lifecycle_requests",
        sa.Column("claimed_by_supervisor", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "operations_lifecycle_requests",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "operations_lifecycle_requests",
        sa.Column("admission_report_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_lifecycle_requests_admission",
        "operations_lifecycle_requests",
        "worker_model_admission_reports",
        ["admission_report_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_lifecycle_requests_admission",
        "operations_lifecycle_requests",
        type_="foreignkey",
    )
    op.drop_column("operations_lifecycle_requests", "admission_report_id")
    op.drop_column("operations_lifecycle_requests", "claimed_at")
    op.drop_column("operations_lifecycle_requests", "claimed_by_supervisor")

    op.drop_index(
        "ix_model_admissions_status_eval",
        table_name="worker_model_admission_reports",
    )
    op.drop_index(
        "ix_model_admissions_edge_eval",
        table_name="worker_model_admission_reports",
    )
    op.drop_index(
        "ix_model_admissions_camera_eval",
        table_name="worker_model_admission_reports",
    )
    op.drop_table("worker_model_admission_reports")

    op.drop_index(
        "ix_hardware_reports_tenant_reported",
        table_name="edge_node_hardware_reports",
    )
    op.drop_index(
        "ix_hardware_reports_edge_reported",
        table_name="edge_node_hardware_reports",
    )
    op.drop_table("edge_node_hardware_reports")

    postgresql.ENUM(name="admission_detector_capability_enum").drop(
        op.get_bind(),
        checkfirst=True,
    )
    postgresql.ENUM(name="model_admission_status_enum").drop(
        op.get_bind(),
        checkfirst=True,
    )
