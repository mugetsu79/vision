"""Add maritime FleetOps evidence context tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0034_maritime_evidence"
down_revision = "0033_maritime_telemetry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maritime_evidence_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("incident_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("port_call_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_source", sa.String(length=80), nullable=False),
        sa.Column("vessel_name", sa.String(length=255), nullable=True),
        sa.Column("port_name", sa.String(length=255), nullable=True),
        sa.Column("ais_position", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "carrier_terminal",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "telemetry_freshness",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("partial", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"]),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"]),
        sa.ForeignKeyConstraint(["port_call_id"], ["maritime_port_calls.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.ForeignKeyConstraint(["voyage_id"], ["maritime_voyages.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "incident_id",
            name="uq_maritime_evidence_contexts_tenant_incident",
        ),
    )
    op.create_index(
        "ix_maritime_evidence_contexts_tenant_camera",
        "maritime_evidence_contexts",
        ["tenant_id", "camera_id"],
    )

    op.create_table(
        "maritime_evidence_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "artifact_hashes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_maritime_evidence_exports_incident",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_evidence_exports_tenant_incident_created",
        "maritime_evidence_exports",
        ["tenant_id", "incident_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maritime_evidence_exports_tenant_incident_created",
        table_name="maritime_evidence_exports",
    )
    op.drop_table("maritime_evidence_exports")
    op.drop_index(
        "ix_maritime_evidence_contexts_tenant_camera",
        table_name="maritime_evidence_contexts",
    )
    op.drop_table("maritime_evidence_contexts")
