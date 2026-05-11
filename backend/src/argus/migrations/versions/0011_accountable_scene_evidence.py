"""Add accountable scene evidence tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_accountable_scene_evidence"
down_revision = "0010_model_runtime_artifacts"
branch_labels = None
depends_on = None


artifact_kind_enum = postgresql.ENUM(
    "event_clip",
    "snapshot",
    "manifest_export",
    "case_export",
    name="evidence_artifact_kind_enum",
    create_type=False,
)
artifact_status_enum = postgresql.ENUM(
    "available",
    "local_only",
    "remote_available",
    "upload_pending",
    "quota_exceeded",
    "capture_failed",
    "expired",
    name="evidence_artifact_status_enum",
    create_type=False,
)
storage_provider_enum = postgresql.ENUM(
    "local_filesystem",
    "minio",
    "s3_compatible",
    name="evidence_storage_provider_enum",
    create_type=False,
)
storage_scope_enum = postgresql.ENUM(
    "edge",
    "central",
    "cloud",
    name="evidence_storage_scope_enum",
    create_type=False,
)
ledger_action_enum = postgresql.ENUM(
    "incident.triggered",
    "scene_contract.attached",
    "privacy_manifest.attached",
    "evidence.clip.capture_started",
    "evidence.clip.available",
    "evidence.clip.quota_exceeded",
    "evidence.clip.capture_failed",
    "incident.reviewed",
    "incident.reopened",
    name="evidence_ledger_action_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        artifact_kind_enum,
        artifact_status_enum,
        storage_provider_enum,
        storage_scope_enum,
        ledger_action_enum,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "scene_contract_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("contract_hash", sa.String(length=64), nullable=False),
        sa.Column("contract", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_hash", name="uq_scene_contract_snapshots_contract_hash"),
    )
    op.create_index(
        "ix_scene_contract_snapshots_camera_created",
        "scene_contract_snapshots",
        ["camera_id", "created_at"],
    )

    op.create_table(
        "privacy_manifest_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("manifest", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("manifest_hash", name="uq_privacy_manifest_snapshots_manifest_hash"),
    )
    op.create_index(
        "ix_privacy_manifest_snapshots_camera_created",
        "privacy_manifest_snapshots",
        ["camera_id", "created_at"],
    )

    op.add_column("cameras", sa.Column("source_kind", sa.String(length=32), nullable=True))
    op.add_column(
        "cameras",
        sa.Column("source_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "evidence_recording_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE cameras SET source_kind = 'rtsp', source_config = '{\"kind\":\"rtsp\"}'::jsonb "
        "WHERE source_kind IS NULL"
    )

    op.add_column(
        "incidents",
        sa.Column("scene_contract_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("scene_contract_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("privacy_manifest_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("privacy_manifest_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("recording_policy", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_foreign_key(
        "fk_incidents_scene_contract_snapshot",
        "incidents",
        "scene_contract_snapshots",
        ["scene_contract_snapshot_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_incidents_privacy_manifest_snapshot",
        "incidents",
        "privacy_manifest_snapshots",
        ["privacy_manifest_snapshot_id"],
        ["id"],
    )

    op.create_table(
        "evidence_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", artifact_kind_enum, nullable=False),
        sa.Column("status", artifact_status_enum, nullable=False),
        sa.Column("storage_provider", storage_provider_enum, nullable=False),
        sa.Column("storage_scope", storage_scope_enum, nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("clip_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clip_ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("fps", sa.Integer(), nullable=True),
        sa.Column("scene_contract_hash", sa.String(length=64), nullable=True),
        sa.Column("privacy_manifest_hash", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evidence_artifacts_incident_kind",
        "evidence_artifacts",
        ["incident_id", "kind"],
    )
    op.create_index(
        "ix_evidence_artifacts_camera_created",
        "evidence_artifacts",
        ["camera_id", "created_at"],
    )
    op.create_index(
        "ix_evidence_artifacts_status_scope",
        "evidence_artifacts",
        ["status", "storage_scope"],
    )

    op.create_table(
        "evidence_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("action", ledger_action_enum, nullable=False),
        sa.Column("actor_type", sa.String(length=64), nullable=False),
        sa.Column("actor_subject", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("previous_entry_hash", sa.String(length=64), nullable=True),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "incident_id",
            "sequence",
            name="uq_evidence_ledger_entries_incident_sequence",
        ),
    )
    op.create_index(
        "ix_evidence_ledger_entries_incident_occurred",
        "evidence_ledger_entries",
        ["incident_id", "occurred_at"],
    )
    op.create_index(
        "ix_evidence_ledger_entries_entry_hash",
        "evidence_ledger_entries",
        ["entry_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_ledger_entries_entry_hash", table_name="evidence_ledger_entries")
    op.drop_index(
        "ix_evidence_ledger_entries_incident_occurred",
        table_name="evidence_ledger_entries",
    )
    op.drop_table("evidence_ledger_entries")

    op.drop_index("ix_evidence_artifacts_status_scope", table_name="evidence_artifacts")
    op.drop_index("ix_evidence_artifacts_camera_created", table_name="evidence_artifacts")
    op.drop_index("ix_evidence_artifacts_incident_kind", table_name="evidence_artifacts")
    op.drop_table("evidence_artifacts")

    op.drop_constraint(
        "fk_incidents_privacy_manifest_snapshot",
        "incidents",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_incidents_scene_contract_snapshot",
        "incidents",
        type_="foreignkey",
    )
    op.drop_column("incidents", "recording_policy")
    op.drop_column("incidents", "privacy_manifest_hash")
    op.drop_column("incidents", "privacy_manifest_snapshot_id")
    op.drop_column("incidents", "scene_contract_hash")
    op.drop_column("incidents", "scene_contract_snapshot_id")

    op.drop_column("cameras", "evidence_recording_policy")
    op.drop_column("cameras", "source_config")
    op.drop_column("cameras", "source_kind")

    op.drop_index(
        "ix_privacy_manifest_snapshots_camera_created",
        table_name="privacy_manifest_snapshots",
    )
    op.drop_table("privacy_manifest_snapshots")
    op.drop_index(
        "ix_scene_contract_snapshots_camera_created",
        table_name="scene_contract_snapshots",
    )
    op.drop_table("scene_contract_snapshots")

    bind = op.get_bind()
    for enum in (
        ledger_action_enum,
        storage_scope_enum,
        storage_provider_enum,
        artifact_status_enum,
        artifact_kind_enum,
    ):
        enum.drop(bind, checkfirst=True)
