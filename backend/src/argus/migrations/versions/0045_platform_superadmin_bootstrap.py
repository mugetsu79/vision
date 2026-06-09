"""Add platform superadmin bootstrap sessions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0045_platform_superadmin"
down_revision = "0044_user_mgmt_profile_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_bootstrap_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_by_subject", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_platform_bootstrap_consumed",
        "platform_bootstrap_sessions",
        ["consumed_at"],
        unique=False,
    )
    op.create_index(
        "ix_platform_bootstrap_token_hash",
        "platform_bootstrap_sessions",
        ["token_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_platform_bootstrap_token_hash", table_name="platform_bootstrap_sessions")
    op.drop_index("ix_platform_bootstrap_consumed", table_name="platform_bootstrap_sessions")
    op.drop_table("platform_bootstrap_sessions")
