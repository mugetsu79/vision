"""Add core billing tables."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0035_core_billing"
down_revision = "0034_maritime_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "billing_nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.ForeignKeyConstraint(["parent_id"], ["billing_nodes.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_nodes_tenant_kind", "billing_nodes", ["tenant_id", "kind"])
    op.create_index("ix_billing_nodes_tenant_parent", "billing_nodes", ["tenant_id", "parent_id"])

    op.create_table(
        "billing_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "node_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_accounts_tenant_name", "billing_accounts", ["tenant_id", "name"])

    op.create_table(
        "usage_meters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meter_key", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("unit_label", sa.String(length=64), nullable=False),
        sa.Column("aggregation", sa.String(length=32), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pack_id", "meter_key", name="uq_usage_meters_pack_meter"),
    )
    op.create_index("ix_usage_meters_pack", "usage_meters", ["pack_id"])

    op.create_table(
        "price_books",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "meter_prices",
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_books_tenant_effective", "price_books", ["tenant_id", "effective_from"]
    )

    op.create_table(
        "entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("usage_limit", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "attributes",
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
        sa.ForeignKeyConstraint(["account_id"], ["billing_accounts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "account_id",
            "pack_id",
            "feature_key",
            name="uq_entitlements_tenant_account_pack_feature",
        ),
    )
    op.create_index("ix_entitlements_tenant_account", "entitlements", ["tenant_id", "account_id"])

    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meter_key", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_object_type", sa.String(length=80), nullable=False),
        sa.Column("source_object_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("source_started_on", sa.Date(), nullable=True),
        sa.Column("source_ended_on", sa.Date(), nullable=True),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.Column(
            "attributes",
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
        sa.ForeignKeyConstraint(["account_id"], ["billing_accounts.id"]),
        sa.ForeignKeyConstraint(["node_id"], ["billing_nodes.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_usage_records_tenant_meter_period",
        "usage_records",
        ["tenant_id", "meter_key", "occurred_on"],
    )
    op.create_index(
        "ix_usage_records_source", "usage_records", ["source_object_type", "source_object_id"]
    )

    op.create_table(
        "invoice_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["billing_accounts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_invoice_runs_tenant_account_period",
        "invoice_runs",
        ["tenant_id", "account_id", "period_start"],
    )

    op.create_table(
        "invoice_line_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("meter_key", sa.String(length=128), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_label", sa.String(length=64), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("total", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "source_record_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("pack_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["billing_accounts.id"]),
        sa.ForeignKeyConstraint(["invoice_run_id"], ["invoice_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoice_line_items_invoice", "invoice_line_items", ["invoice_run_id"])
    op.create_index(
        "ix_invoice_line_items_tenant_meter", "invoice_line_items", ["tenant_id", "meter_key"]
    )

    op.create_table(
        "billing_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column(
            "payload",
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
        sa.ForeignKeyConstraint(["invoice_run_id"], ["invoice_runs.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_exports_tenant_invoice", "billing_exports", ["tenant_id", "invoice_run_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_billing_exports_tenant_invoice", table_name="billing_exports")
    op.drop_table("billing_exports")
    op.drop_index("ix_invoice_line_items_tenant_meter", table_name="invoice_line_items")
    op.drop_index("ix_invoice_line_items_invoice", table_name="invoice_line_items")
    op.drop_table("invoice_line_items")
    op.drop_index("ix_invoice_runs_tenant_account_period", table_name="invoice_runs")
    op.drop_table("invoice_runs")
    op.drop_index("ix_usage_records_source", table_name="usage_records")
    op.drop_index("ix_usage_records_tenant_meter_period", table_name="usage_records")
    op.drop_table("usage_records")
    op.drop_index("ix_entitlements_tenant_account", table_name="entitlements")
    op.drop_table("entitlements")
    op.drop_index("ix_price_books_tenant_effective", table_name="price_books")
    op.drop_table("price_books")
    op.drop_index("ix_usage_meters_pack", table_name="usage_meters")
    op.drop_table("usage_meters")
    op.drop_index("ix_billing_accounts_tenant_name", table_name="billing_accounts")
    op.drop_table("billing_accounts")
    op.drop_index("ix_billing_nodes_tenant_parent", table_name="billing_nodes")
    op.drop_index("ix_billing_nodes_tenant_kind", table_name="billing_nodes")
    op.drop_table("billing_nodes")
