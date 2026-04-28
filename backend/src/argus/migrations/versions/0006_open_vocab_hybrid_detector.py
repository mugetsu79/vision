"""Add hybrid detector capability and runtime vocabulary state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_open_vocab_hybrid_detector"
down_revision = "0005_source_capability"
branch_labels = None
depends_on = None


detector_capability_enum = postgresql.ENUM(
    "fixed_vocab",
    "open_vocab",
    name="detector_capability_enum",
    create_type=False,
)
runtime_vocabulary_source_enum = postgresql.ENUM(
    "default",
    "query",
    "manual",
    name="runtime_vocabulary_source_enum",
    create_type=False,
)
camera_vocabulary_snapshot_source_enum = postgresql.ENUM(
    "default",
    "query",
    "manual",
    name="camera_vocabulary_snapshot_source_enum",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    detector_capability_enum.create(bind, checkfirst=True)
    runtime_vocabulary_source_enum.create(bind, checkfirst=True)
    camera_vocabulary_snapshot_source_enum.create(bind, checkfirst=True)

    op.add_column(
        "models",
        sa.Column(
            "capability",
            detector_capability_enum,
            nullable=False,
            server_default="fixed_vocab",
        ),
    )
    op.add_column(
        "models",
        sa.Column(
            "capability_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.alter_column("models", "capability", server_default=None)
    op.alter_column("models", "capability_config", server_default=None)

    op.add_column(
        "cameras",
        sa.Column(
            "runtime_vocabulary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "runtime_vocabulary_source",
            runtime_vocabulary_source_enum,
            nullable=False,
            server_default="default",
        ),
    )
    op.add_column(
        "cameras",
        sa.Column(
            "runtime_vocabulary_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cameras",
        sa.Column("runtime_vocabulary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("cameras", "runtime_vocabulary", server_default=None)
    op.alter_column("cameras", "runtime_vocabulary_source", server_default=None)
    op.alter_column("cameras", "runtime_vocabulary_version", server_default=None)

    op.create_table(
        "camera_vocabulary_snapshots",
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("vocabulary_hash", sa.String(length=64), nullable=False),
        sa.Column("source", camera_vocabulary_snapshot_source_enum, nullable=False),
        sa.Column(
            "terms",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
    )
    op.alter_column("camera_vocabulary_snapshots", "terms", server_default=None)

    op.add_column(
        "tracking_events",
        sa.Column("vocabulary_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "tracking_events",
        sa.Column("vocabulary_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "count_events",
        sa.Column("vocabulary_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "count_events",
        sa.Column("vocabulary_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("count_events", "vocabulary_hash")
    op.drop_column("count_events", "vocabulary_version")
    op.drop_column("tracking_events", "vocabulary_hash")
    op.drop_column("tracking_events", "vocabulary_version")
    op.drop_table("camera_vocabulary_snapshots")
    op.drop_column("cameras", "runtime_vocabulary_updated_at")
    op.drop_column("cameras", "runtime_vocabulary_version")
    op.drop_column("cameras", "runtime_vocabulary_source")
    op.drop_column("cameras", "runtime_vocabulary")
    op.drop_column("models", "capability_config")
    op.drop_column("models", "capability")

    bind = op.get_bind()
    camera_vocabulary_snapshot_source_enum.drop(bind, checkfirst=True)
    runtime_vocabulary_source_enum.drop(bind, checkfirst=True)
    detector_capability_enum.drop(bind, checkfirst=True)
