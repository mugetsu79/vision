"""Add master first-run bootstrap sessions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0028_master_first_run_bootstrap"
down_revision = "0027_runtime_artifact_soak_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "master_bootstrap_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_subject", sa.String(length=255), nullable=True),
        sa.Column("consumed_by_subject", sa.String(length=255), nullable=True),
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
            name="fk_master_bootstrap_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_master_bootstrap_status",
        "master_bootstrap_sessions",
        ["status", "expires_at"],
    )
    op.create_index(
        "ix_master_bootstrap_tenant",
        "master_bootstrap_sessions",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_master_bootstrap_tenant", table_name="master_bootstrap_sessions")
    op.drop_index("ix_master_bootstrap_status", table_name="master_bootstrap_sessions")
    op.drop_table("master_bootstrap_sessions")
