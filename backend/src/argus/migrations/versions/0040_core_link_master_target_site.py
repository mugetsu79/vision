"""Add core link master target site fields."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from argus.compat import UTC

revision: str = "0040_core_link_master_target"
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
    _backfill_control_plane_sites()


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM sites WHERE site_kind = 'control_plane'"))
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


def _backfill_control_plane_sites() -> None:
    bind = op.get_bind()
    tenants = sa.table("tenants", sa.column("id", postgresql.UUID(as_uuid=True)))
    sites = sa.table(
        "sites",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("tz", sa.String()),
        sa.column("geo_point", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("site_kind", sa.String()),
    )
    now = datetime.now(tz=UTC)
    tenant_ids = list(bind.execute(sa.select(tenants.c.id)).scalars())
    for tenant_id in tenant_ids:
        existing = bind.execute(
            sa.select(sites.c.id)
            .where(sites.c.tenant_id == tenant_id, sites.c.site_kind == "control_plane")
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            continue
        bind.execute(
            sites.insert().values(
                id=uuid4(),
                tenant_id=tenant_id,
                name="Vezor Master",
                description="Vezor control-plane probe target",
                tz="UTC",
                geo_point=None,
                created_at=now,
                site_kind="control_plane",
            )
        )
