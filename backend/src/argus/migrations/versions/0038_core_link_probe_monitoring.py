"""Add core link probe monitoring fields."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_core_link_probe_monitoring"
down_revision = "0037_core_link_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("link_health_probes", sa.Column("target_id", sa.String(length=96), nullable=True))
    op.add_column(
        "link_health_probes",
        sa.Column("target_label", sa.String(length=160), nullable=True),
    )
    op.add_column("link_health_probes", sa.Column("target_address", sa.Text(), nullable=True))
    op.add_column("link_health_probes", sa.Column("probe_type", sa.String(length=16), nullable=True))
    op.add_column(
        "link_health_probes",
        sa.Column(
            "source_type",
            sa.String(length=32),
            server_default="manual",
            nullable=False,
        ),
    )
    op.add_column(
        "link_health_probes",
        sa.Column("source_label", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "link_health_probes",
        sa.Column(
            "sample_kind",
            sa.String(length=32),
            server_default="manual",
            nullable=False,
        ),
    )
    op.add_column(
        "link_health_probes",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_link_health_probes_target", "link_health_probes", ["target_id"])
    op.create_index("ix_link_health_probes_deleted", "link_health_probes", ["deleted_at"])
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'manual')",
    )
    op.create_check_constraint(
        "ck_link_health_probes_source_type",
        "link_health_probes",
        "source_type IN ('manual', 'backend_synthetic', 'edge_agent', 'provider_api', 'import')",
    )
    op.create_check_constraint(
        "ck_link_health_probes_sample_kind",
        "link_health_probes",
        "sample_kind IN ('manual', 'automated', 'imported')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_link_health_probes_sample_kind", "link_health_probes", type_="check")
    op.drop_constraint("ck_link_health_probes_source_type", "link_health_probes", type_="check")
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.drop_index("ix_link_health_probes_deleted", table_name="link_health_probes")
    op.drop_index("ix_link_health_probes_target", table_name="link_health_probes")
    op.drop_column("link_health_probes", "deleted_at")
    op.drop_column("link_health_probes", "sample_kind")
    op.drop_column("link_health_probes", "source_label")
    op.drop_column("link_health_probes", "source_type")
    op.drop_column("link_health_probes", "probe_type")
    op.drop_column("link_health_probes", "target_address")
    op.drop_column("link_health_probes", "target_label")
    op.drop_column("link_health_probes", "target_id")
