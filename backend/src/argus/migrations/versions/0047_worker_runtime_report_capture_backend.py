"""Add worker runtime capture backend evidence."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047_runtime_capture_backend"
down_revision: str | Sequence[str] | None = "0046_worker_runtime_media_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "worker_runtime_reports",
        sa.Column("media_capture_backend", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("worker_runtime_reports", "media_capture_backend")
