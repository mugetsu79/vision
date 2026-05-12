"""Add prompt-to-policy ledger entries."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020a_policy_draft_ledger"
down_revision = "0020_policy_drafts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    policy_draft_ledger_action_enum = postgresql.ENUM(
        "policy_draft.proposed",
        "policy_draft.approved",
        "policy_draft.rejected",
        "policy_draft.applied",
        name="policy_draft_ledger_action_enum",
    )
    policy_draft_ledger_action_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "policy_draft_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("policy_draft_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "action",
            postgresql.ENUM(
                "policy_draft.proposed",
                "policy_draft.approved",
                "policy_draft.rejected",
                "policy_draft.applied",
                name="policy_draft_ledger_action_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("actor_subject", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("previous_entry_hash", sa.String(length=64), nullable=True),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_policy_draft_ledger_camera",
        ),
        sa.ForeignKeyConstraint(
            ["policy_draft_id"],
            ["policy_drafts.id"],
            name="fk_policy_draft_ledger_draft",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_policy_draft_ledger_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "policy_draft_id",
            "sequence",
            name="uq_policy_draft_ledger_sequence",
        ),
    )
    op.create_index(
        "ix_policy_draft_ledger_draft_sequence",
        "policy_draft_ledger_entries",
        ["policy_draft_id", "sequence"],
    )
    op.create_index(
        "ix_policy_draft_ledger_tenant_created",
        "policy_draft_ledger_entries",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_policy_draft_ledger_tenant_created",
        table_name="policy_draft_ledger_entries",
    )
    op.drop_index(
        "ix_policy_draft_ledger_draft_sequence",
        table_name="policy_draft_ledger_entries",
    )
    op.drop_table("policy_draft_ledger_entries")
    postgresql.ENUM(name="policy_draft_ledger_action_enum").drop(
        op.get_bind(),
        checkfirst=True,
    )
