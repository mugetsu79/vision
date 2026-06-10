"""Add worker runtime source profile hash."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0048_runtime_source_profile_hash"
down_revision: str | Sequence[str] | None = "0047_runtime_capture_backend"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("source_profile_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "source_profile_hash")
