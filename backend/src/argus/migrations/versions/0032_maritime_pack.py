"""Add maritime FleetOps pack entity tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0032_maritime_pack"
down_revision = "0031_core_fleet"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maritime_vessels",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("imo_number", sa.String(length=16), nullable=True),
        sa.Column("mmsi", sa.String(length=16), nullable=True),
        sa.Column("call_sign", sa.String(length=32), nullable=True),
        sa.Column("flag_state", sa.String(length=64), nullable=True),
        sa.Column("vessel_type", sa.String(length=80), nullable=True),
        sa.Column("owner_label", sa.String(length=160), nullable=True),
        sa.Column("manager_label", sa.String(length=160), nullable=True),
        sa.Column("charterer_label", sa.String(length=160), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "site_id", name="uq_maritime_vessels_tenant_site"),
        sa.UniqueConstraint("tenant_id", "imo_number", name="uq_maritime_vessels_tenant_imo"),
        sa.UniqueConstraint("tenant_id", "mmsi", name="uq_maritime_vessels_tenant_mmsi"),
        sa.UniqueConstraint(
            "tenant_id",
            "call_sign",
            name="uq_maritime_vessels_tenant_call_sign",
        ),
    )
    op.create_index(
        "ix_maritime_vessels_tenant_active",
        "maritime_vessels",
        ["tenant_id", "active"],
    )

    op.create_table(
        "maritime_voyages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("voyage_number", sa.String(length=80), nullable=True),
        sa.Column("origin", sa.String(length=160), nullable=True),
        sa.Column("destination", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="planned", nullable=False),
        sa.Column("scheduled_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('planned', 'active', 'completed', 'cancelled')",
            name="ck_maritime_voyages_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_voyages_tenant_vessel",
        "maritime_voyages",
        ["tenant_id", "vessel_id"],
    )
    op.create_index(
        "ix_maritime_voyages_one_active_per_vessel",
        "maritime_voyages",
        ["tenant_id", "vessel_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "maritime_port_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voyage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("port_name", sa.String(length=255), nullable=False),
        sa.Column("un_locode", sa.String(length=16), nullable=True),
        sa.Column("terminal_name", sa.String(length=160), nullable=True),
        sa.Column("berth", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="scheduled", nullable=False),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ata", sa.DateTime(timezone=True), nullable=True),
        sa.Column("etd", sa.DateTime(timezone=True), nullable=True),
        sa.Column("atd", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link_profile", sa.String(length=80), nullable=True),
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
        sa.CheckConstraint(
            "status IN ('scheduled', 'arrived', 'alongside', 'departed', 'cancelled')",
            name="ck_maritime_port_calls_status",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.ForeignKeyConstraint(["voyage_id"], ["maritime_voyages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_port_calls_tenant_vessel",
        "maritime_port_calls",
        ["tenant_id", "vessel_id"],
    )
    op.create_index(
        "ix_maritime_port_calls_tenant_voyage",
        "maritime_port_calls",
        ["tenant_id", "voyage_id"],
    )

    op.create_table(
        "maritime_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_roles_tenant_label",
        "maritime_roles",
        ["tenant_id", "label"],
    )

    op.create_table(
        "maritime_watch_rotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vessel_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column(
            "member_user_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["vessel_id"], ["maritime_vessels.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_maritime_watch_rotations_tenant_label",
        "maritime_watch_rotations",
        ["tenant_id", "label"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maritime_watch_rotations_tenant_label",
        table_name="maritime_watch_rotations",
    )
    op.drop_table("maritime_watch_rotations")
    op.drop_index("ix_maritime_roles_tenant_label", table_name="maritime_roles")
    op.drop_table("maritime_roles")
    op.drop_index("ix_maritime_port_calls_tenant_voyage", table_name="maritime_port_calls")
    op.drop_index("ix_maritime_port_calls_tenant_vessel", table_name="maritime_port_calls")
    op.drop_table("maritime_port_calls")
    op.drop_index(
        "ix_maritime_voyages_one_active_per_vessel",
        table_name="maritime_voyages",
    )
    op.drop_index("ix_maritime_voyages_tenant_vessel", table_name="maritime_voyages")
    op.drop_table("maritime_voyages")
    op.drop_index("ix_maritime_vessels_tenant_active", table_name="maritime_vessels")
    op.drop_table("maritime_vessels")
