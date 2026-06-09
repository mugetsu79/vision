"""Add user management profile fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0044_user_mgmt_profile_fields"
down_revision: str | Sequence[str] | None = "0043_model_catalog_unique_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=128), nullable=True))
    op.add_column(
        "users",
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("users", "enabled", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "enabled")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
