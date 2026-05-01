"""model catalog open vocab runtime

Revision ID: 0008_model_catalog_open_vocab_runtime
Revises: 0007_incident_review_state
Create Date: 2026-05-01
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision = "0008_model_catalog_open_vocab_runtime"
down_revision = "0007_incident_review_state"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE model_format_enum ADD VALUE IF NOT EXISTS 'pt'")


def downgrade() -> None:
    # PostgreSQL enum value removal is intentionally not attempted.
    pass
