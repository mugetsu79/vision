"""Persist pairing session requested hostname."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0025_pairing_session_hostname"
down_revision = "0024_installable_supervisor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "node_pairing_sessions",
        sa.Column("hostname", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("node_pairing_sessions", "hostname")
