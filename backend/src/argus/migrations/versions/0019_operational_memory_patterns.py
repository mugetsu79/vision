"""Add operational memory patterns."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019_operational_memory_patterns"
down_revision = "0018_incident_rule_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_memory_patterns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("pattern_type", sa.String(length=64), nullable=False),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "info",
                "warning",
                "critical",
                name="incident_rule_severity_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_incident_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "source_contract_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("pattern_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            name="fk_operational_memory_camera",
        ),
        sa.ForeignKeyConstraint(
            ["site_id"],
            ["sites.id"],
            name="fk_operational_memory_site",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            name="fk_operational_memory_tenant",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pattern_hash", name="uq_operational_memory_pattern_hash"),
    )
    op.create_index(
        "ix_operational_memory_tenant_created",
        "operational_memory_patterns",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_operational_memory_camera_created",
        "operational_memory_patterns",
        ["camera_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_operational_memory_camera_created",
        table_name="operational_memory_patterns",
    )
    op.drop_index(
        "ix_operational_memory_tenant_created",
        table_name="operational_memory_patterns",
    )
    op.drop_table("operational_memory_patterns")
