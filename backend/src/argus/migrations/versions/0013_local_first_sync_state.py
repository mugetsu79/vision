"""Add local-first evidence sync state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_local_first_sync_state"
down_revision = "0012_operator_config_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE evidence_ledger_action_enum "
        "ADD VALUE IF NOT EXISTS 'evidence.upload.started'"
    )
    op.execute(
        "ALTER TYPE evidence_ledger_action_enum "
        "ADD VALUE IF NOT EXISTS 'evidence.upload.available'"
    )
    op.execute(
        "ALTER TYPE evidence_ledger_action_enum "
        "ADD VALUE IF NOT EXISTS 'evidence.upload.failed'"
    )

    op.create_table(
        "local_first_sync_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("remote_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("latest_status", sa.String(length=64), server_default="pending", nullable=False),
        sa.Column("latest_error", sa.Text(), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
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
            ["artifact_id"],
            ["evidence_artifacts.id"],
            name="fk_local_first_sync_artifact",
        ),
        sa.ForeignKeyConstraint(
            ["remote_profile_id"],
            ["operator_config_profiles.id"],
            name="fk_local_first_sync_remote_profile",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_local_first_sync_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id", name="uq_local_first_sync_artifact"),
    )
    op.create_index(
        "ix_local_first_sync_tenant_status",
        "local_first_sync_attempts",
        ["tenant_id", "latest_status"],
    )
    op.create_index(
        "ix_local_first_sync_profile",
        "local_first_sync_attempts",
        ["remote_profile_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_local_first_sync_profile", table_name="local_first_sync_attempts")
    op.drop_index("ix_local_first_sync_tenant_status", table_name="local_first_sync_attempts")
    op.drop_table("local_first_sync_attempts")
