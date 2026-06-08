"""Add core link master reflector profiles."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0041_core_link_reflector"
down_revision: str | Sequence[str] | None = "0040_core_link_master_target"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "link_reflector_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_kind", sa.String(length=32), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "mode",
            sa.String(length=32),
            nullable=False,
            server_default="vezor_udp_sequence",
        ),
        sa.Column("public_address", sa.String(length=255), nullable=True),
        sa.Column("bind_address", sa.String(length=64), nullable=False, server_default="0.0.0.0"),
        sa.Column("udp_port", sa.Integer(), nullable=False, server_default="8622"),
        sa.Column("key_id", sa.String(length=128), nullable=False),
        sa.Column("encrypted_secret", sa.Text(), nullable=True),
        sa.Column(
            "allowed_edge_site_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "allowed_source_cidrs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rate_limit_pps_per_source",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column(
            "last_status",
            sa.String(length=32),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("profile_kind IN ('master')", name="ck_link_reflector_profiles_kind"),
        sa.CheckConstraint(
            "mode IN ('vezor_udp_sequence')",
            name="ck_link_reflector_profiles_mode",
        ),
        sa.CheckConstraint(
            "last_status IN ('disabled', 'starting', 'listening', 'unhealthy')",
            name="ck_link_reflector_profiles_status",
        ),
        sa.CheckConstraint(
            "udp_port > 0 AND udp_port <= 65535",
            name="ck_link_reflector_profiles_udp_port",
        ),
        sa.CheckConstraint(
            "rate_limit_pps_per_source >= 0",
            name="ck_link_reflector_profiles_rate_limit",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_link_reflector_profiles_tenant_site_kind",
        "link_reflector_profiles",
        ["tenant_id", "site_id", "profile_kind"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_link_reflector_profiles_tenant_site_kind",
        table_name="link_reflector_profiles",
    )
    op.drop_table("link_reflector_profiles")
