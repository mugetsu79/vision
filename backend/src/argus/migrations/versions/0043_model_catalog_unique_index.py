"""Add catalog model uniqueness backstop."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0043_model_catalog_unique_idx"
down_revision: str | Sequence[str] | None = "0042_model_edge_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDEX_NAME = "uq_models_catalog_id"


def upgrade() -> None:
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_models_catalog_id "
            "ON models ((capability_config->>'catalog_id')) "
            "WHERE capability_config ? 'catalog_id'"
        )
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="models")
