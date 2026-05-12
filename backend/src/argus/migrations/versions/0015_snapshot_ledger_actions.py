"""Add snapshot evidence ledger actions."""

from __future__ import annotations

from alembic import op

revision = "0015_snapshot_ledger_actions"
down_revision = "0014_evidence_expiry_action"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for action in (
        "evidence.snapshot.available",
        "evidence.snapshot.quota_exceeded",
        "evidence.snapshot.capture_failed",
    ):
        op.execute(
            "ALTER TYPE evidence_ledger_action_enum "
            f"ADD VALUE IF NOT EXISTS '{action}'"
        )


def downgrade() -> None:
    pass
