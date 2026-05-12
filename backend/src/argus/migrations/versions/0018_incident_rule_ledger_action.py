"""Add incident rule ledger action."""

from __future__ import annotations

from alembic import op

revision = "0018_incident_rule_ledger"
down_revision = "0017_detection_rule_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE evidence_ledger_action_enum ADD VALUE IF NOT EXISTS 'incident_rule.attached'"
    )


def downgrade() -> None:
    pass
