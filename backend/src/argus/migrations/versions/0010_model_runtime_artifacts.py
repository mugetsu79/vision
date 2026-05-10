"""Add model runtime artifacts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_model_runtime_artifacts"
down_revision = "0009_scene_vision_profiles"
branch_labels = None
depends_on = None


scope_enum = postgresql.ENUM(
    "model",
    "scene",
    name="runtime_artifact_scope_enum",
    create_type=False,
)
kind_enum = postgresql.ENUM(
    "onnx_export",
    "tensorrt_engine",
    name="runtime_artifact_kind_enum",
    create_type=False,
)
precision_enum = postgresql.ENUM(
    "fp32",
    "fp16",
    "int8",
    name="runtime_artifact_precision_enum",
    create_type=False,
)
capability_enum = postgresql.ENUM(
    "fixed_vocab",
    "open_vocab",
    name="runtime_artifact_detector_capability_enum",
    create_type=False,
)
status_enum = postgresql.ENUM(
    "unvalidated",
    "valid",
    "invalid",
    "stale",
    "missing_artifact",
    "target_mismatch",
    name="runtime_artifact_validation_status_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (scope_enum, kind_enum, precision_enum, capability_enum, status_enum):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "model_runtime_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scope", scope_enum, nullable=False),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("capability", capability_enum, nullable=False),
        sa.Column("runtime_backend", sa.String(length=64), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("target_profile", sa.String(length=128), nullable=False),
        sa.Column("precision", precision_enum, nullable=False),
        sa.Column("input_shape", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("vocabulary_hash", sa.String(length=64), nullable=True),
        sa.Column("vocabulary_version", sa.Integer(), nullable=True),
        sa.Column("source_model_sha256", sa.String(length=64), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("builder", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("runtime_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_status", status_enum, nullable=False),
        sa.Column("validation_error", sa.Text(), nullable=True),
        sa.Column("build_duration_seconds", sa.Float(), nullable=True),
        sa.Column("validation_duration_seconds", sa.Float(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["model_id"], ["models.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_model_runtime_artifacts_model_target",
        "model_runtime_artifacts",
        ["model_id", "target_profile", "validation_status"],
    )
    op.create_index(
        "ix_model_runtime_artifacts_scene_vocab",
        "model_runtime_artifacts",
        ["camera_id", "vocabulary_hash", "target_profile", "validation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_runtime_artifacts_scene_vocab", table_name="model_runtime_artifacts")
    op.drop_index("ix_model_runtime_artifacts_model_target", table_name="model_runtime_artifacts")
    op.drop_table("model_runtime_artifacts")
    bind = op.get_bind()
    for enum in (status_enum, capability_enum, precision_enum, kind_enum, scope_enum):
        enum.drop(bind, checkfirst=True)
