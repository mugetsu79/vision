"""Add evidence expiry ledger action."""

from __future__ import annotations

from alembic import op

revision = "0014_evidence_expiry_ledger_action"
down_revision = "0013_local_first_sync_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE evidence_ledger_action_enum "
        "ADD VALUE IF NOT EXISTS 'evidence.expired'"
    )


def downgrade() -> None:
    pass
