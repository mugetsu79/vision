"""Add prompt-to-policy drafts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020_policy_drafts"
down_revision = "0019_operational_memory_patterns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    policy_draft_status_enum = postgresql.ENUM(
        "draft",
        "approved",
        "rejected",
        "applied",
        name="policy_draft_status_enum",
    )
    policy_draft_status_enum.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "policy_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "approved",
                "rejected",
                "applied",
                name="policy_draft_status_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "structured_diff",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_by_subject", sa.String(length=255), nullable=True),
        sa.Column("approved_by_subject", sa.String(length=255), nullable=True),
        sa.Column("rejected_by_subject", sa.String(length=255), nullable=True),
        sa.Column("applied_by_subject", sa.String(length=255), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], name="fk_policy_drafts_camera"),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], name="fk_policy_drafts_site"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], name="fk_policy_drafts_tenant"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_drafts_tenant_created",
        "policy_drafts",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_policy_drafts_camera_created",
        "policy_drafts",
        ["camera_id", "created_at"],
    )
    op.create_index(
        "ix_policy_drafts_status_created",
        "policy_drafts",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_policy_drafts_status_created", table_name="policy_drafts")
    op.drop_index("ix_policy_drafts_camera_created", table_name="policy_drafts")
    op.drop_index("ix_policy_drafts_tenant_created", table_name="policy_drafts")
    op.drop_table("policy_drafts")
    postgresql.ENUM(name="policy_draft_status_enum").drop(op.get_bind(), checkfirst=True)
