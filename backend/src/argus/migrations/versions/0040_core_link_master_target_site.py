"""Add core link master target site fields."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0040_core_link_master_target_site"
down_revision: str | Sequence[str] | None = "0039_core_link_edge_agent"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "sites",
        sa.Column("site_kind", sa.String(length=32), nullable=False, server_default="edge"),
    )
    op.create_check_constraint(
        "ck_sites_site_kind",
        "sites",
        "site_kind in ('edge', 'control_plane')",
    )
    op.add_column(
        "link_health_probes",
        sa.Column("target_site_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_link_health_probes_target_site_id_sites",
        "link_health_probes",
        "sites",
        ["target_site_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_link_health_probes_tenant_target_site_recorded",
        "link_health_probes",
        ["tenant_id", "target_site_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_link_health_probes_tenant_target_site_recorded",
        table_name="link_health_probes",
    )
    op.drop_constraint(
        "fk_link_health_probes_target_site_id_sites",
        "link_health_probes",
        type_="foreignkey",
    )
    op.drop_column("link_health_probes", "target_site_id")
    op.drop_constraint("ck_sites_site_kind", "sites", type_="check")
    op.drop_column("sites", "site_kind")
