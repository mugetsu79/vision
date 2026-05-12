"""Add runtime passport snapshots."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_runtime_passports"
down_revision = "0015_snapshot_ledger_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE runtime_artifact_kind_enum "
        "ADD VALUE IF NOT EXISTS 'compiled_open_vocab'"
    )
    op.create_table(
        "runtime_passport_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("passport_hash", sa.String(length=64), nullable=False),
        sa.Column("passport", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_runtime_passports_camera",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_runtime_passports_incident",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_runtime_passports_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("passport_hash", name="uq_runtime_passports_hash"),
    )
    op.create_index(
        "ix_runtime_passports_camera_created",
        "runtime_passport_snapshots",
        ["camera_id", "created_at"],
    )
    op.create_index(
        "ix_runtime_passports_incident",
        "runtime_passport_snapshots",
        ["incident_id"],
    )

    op.add_column(
        "incidents",
        sa.Column("runtime_passport_snapshot_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "incidents",
        sa.Column("runtime_passport_hash", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_incidents_runtime_passport",
        "incidents",
        "runtime_passport_snapshots",
        ["runtime_passport_snapshot_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_incidents_runtime_passport", "incidents", type_="foreignkey")
    op.drop_column("incidents", "runtime_passport_hash")
    op.drop_column("incidents", "runtime_passport_snapshot_id")

    op.drop_index("ix_runtime_passports_incident", table_name="runtime_passport_snapshots")
    op.drop_index(
        "ix_runtime_passports_camera_created",
        table_name="runtime_passport_snapshots",
    )
    op.drop_table("runtime_passport_snapshots")
