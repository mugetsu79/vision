"""Add browser delivery settings to cameras."""

from __future__ import annotations

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_add_camera_browser_delivery"
down_revision = "0001_prompt_one_initial_schema"
branch_labels = None
depends_on = None


DEFAULT_BROWSER_DELIVERY = {
    "default_profile": "720p10",
    "allow_native_on_demand": True,
    "profiles": [
        {"id": "native", "kind": "passthrough"},
        {"id": "1080p15", "kind": "transcode", "w": 1920, "h": 1080, "fps": 15},
        {"id": "720p10", "kind": "transcode", "w": 1280, "h": 720, "fps": 10},
        {"id": "540p5", "kind": "transcode", "w": 960, "h": 540, "fps": 5},
    ],
}


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column(
        "cameras",
        sa.Column(
            "browser_delivery",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    bind.execute(
        sa.text(
            "UPDATE cameras "
            "SET browser_delivery = CAST(:value AS jsonb) "
            "WHERE browser_delivery IS NULL"
        ),
        {"value": json.dumps(DEFAULT_BROWSER_DELIVERY)},
    )
    op.alter_column("cameras", "browser_delivery", nullable=False)


def downgrade() -> None:
    op.drop_column("cameras", "browser_delivery")
