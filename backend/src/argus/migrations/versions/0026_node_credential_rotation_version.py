"""Track supervisor node credential versions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026_node_credential_rotation"
down_revision = "0025_pairing_session_hostname"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "supervisor_node_credentials",
        sa.Column(
            "credential_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.alter_column(
        "supervisor_node_credentials",
        "credential_version",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("supervisor_node_credentials", "credential_version")
