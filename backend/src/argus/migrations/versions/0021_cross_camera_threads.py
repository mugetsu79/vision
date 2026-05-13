"""Add identity-light cross-camera thread snapshots."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021_cross_camera_threads"
down_revision = "0020a_policy_draft_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cross_camera_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "camera_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "source_incident_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "privacy_manifest_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "rationale",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "signals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "privacy_labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("thread_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name="fk_cross_camera_threads_site",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_cross_camera_threads_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("thread_hash", name="uq_cross_camera_thread_hash"),
    )
    op.create_index(
        "ix_cross_camera_threads_tenant_created",
        "cross_camera_threads",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cross_camera_threads_site_created",
        "cross_camera_threads",
        ["site_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cross_camera_threads_site_created",
        table_name="cross_camera_threads",
    )
    op.drop_index(
        "ix_cross_camera_threads_tenant_created",
        table_name="cross_camera_threads",
    )
    op.drop_table("cross_camera_threads")
