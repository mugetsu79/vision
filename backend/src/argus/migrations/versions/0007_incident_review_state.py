"""Add incident review state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_incident_review_state"
down_revision = "0006_open_vocab_hybrid_detector"
branch_labels = None
depends_on = None

incident_review_status_enum = sa.Enum(
    "pending",
    "reviewed",
    name="incident_review_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    incident_review_status_enum.create(bind, checkfirst=True)
    op.add_column(
        "incidents",
        sa.Column(
            "review_status",
            incident_review_status_enum,
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("incidents", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("reviewed_by_subject", sa.String(length=255), nullable=True))
    op.alter_column("incidents", "review_status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_column("incidents", "reviewed_by_subject")
    op.drop_column("incidents", "reviewed_at")
    op.drop_column("incidents", "review_status")
    incident_review_status_enum.drop(bind, checkfirst=True)
