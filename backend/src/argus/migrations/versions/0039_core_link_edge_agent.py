"""Add core link edge agent metadata."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_core_link_edge_agent"
down_revision = "0038_core_link_probe_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "link_health_probes",
        sa.Column("measurement_metadata", sa.JSON(), nullable=True),
    )
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'udp', 'manual')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_link_health_probes_probe_type", "link_health_probes", type_="check")
    op.create_check_constraint(
        "ck_link_health_probes_probe_type",
        "link_health_probes",
        "probe_type IS NULL OR probe_type IN ('icmp', 'tcp', 'http', 'https', 'manual')",
    )
    op.drop_column("link_health_probes", "measurement_metadata")
