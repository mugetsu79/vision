"""Add Prompt 11 tenant quota and incident clip columns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_prompt11_quota"
down_revision = "0002_add_camera_browser_delivery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column(
            "query_requests_per_minute",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "incident_storage_quota_bytes",
            sa.BigInteger(),
            nullable=False,
            server_default=str(10 * 1024 * 1024 * 1024),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column(
            "anpr_store_plaintext",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "tenants",
        sa.Column("anpr_plaintext_justification", sa.Text(), nullable=True),
    )
    op.add_column("incidents", sa.Column("clip_url", sa.Text(), nullable=True))
    op.add_column(
        "incidents",
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
    )

    op.alter_column("tenants", "query_requests_per_minute", server_default=None)
    op.alter_column("tenants", "incident_storage_quota_bytes", server_default=None)
    op.alter_column("tenants", "anpr_store_plaintext", server_default=None)
    op.alter_column("incidents", "storage_bytes", server_default=None)


def downgrade() -> None:
    op.drop_column("incidents", "storage_bytes")
    op.drop_column("incidents", "clip_url")
    op.drop_column("tenants", "anpr_plaintext_justification")
    op.drop_column("tenants", "anpr_store_plaintext")
    op.drop_column("tenants", "incident_storage_quota_bytes")
    op.drop_column("tenants", "query_requests_per_minute")
