from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from argus.models.base import Base, TimestampMixin, UpdatedAtMixin, UUIDPrimaryKeyMixin


class BillingNode(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "billing_nodes"
    __table_args__ = (
        Index("ix_billing_nodes_tenant_kind", "tenant_id", "kind"),
        Index("ix_billing_nodes_tenant_parent", "tenant_id", "parent_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_nodes.id"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class BillingAccount(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "billing_accounts"
    __table_args__ = (Index("ix_billing_accounts_tenant_name", "tenant_id", "name"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    node_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class Entitlement(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "entitlements"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "account_id",
            "pack_id",
            "feature_key",
            name="uq_entitlements_tenant_account_pack_feature",
        ),
        Index("ix_entitlements_tenant_account", "tenant_id", "account_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_accounts.id"),
        nullable=False,
    )
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feature_key: Mapped[str] = mapped_column(String(128), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    usage_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class UsageMeter(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "usage_meters"
    __table_args__ = (
        UniqueConstraint("pack_id", "meter_key", name="uq_usage_meters_pack_meter"),
        Index("ix_usage_meters_pack", "pack_id"),
    )

    meter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    unit_label: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregation: Mapped[str] = mapped_column(String(32), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class PriceBook(UUIDPrimaryKeyMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "price_books"
    __table_args__ = (Index("ix_price_books_tenant_effective", "tenant_id", "effective_from"),)

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    meter_prices: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_records"
    __table_args__ = (
        Index("ix_usage_records_tenant_meter_period", "tenant_id", "meter_key", "occurred_on"),
        Index("ix_usage_records_source", "source_object_type", "source_object_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    meter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_accounts.id"),
        nullable=True,
    )
    node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_nodes.id"),
        nullable=True,
    )
    source_object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    occurred_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attributes: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)


class InvoiceRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoice_runs"
    __table_args__ = (
        Index("ix_invoice_runs_tenant_account_period", "tenant_id", "account_id", "period_start"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_accounts.id"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="generated")


class InvoiceLineItem(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (
        Index("ix_invoice_line_items_invoice", "invoice_run_id"),
        Index("ix_invoice_line_items_tenant_meter", "tenant_id", "meter_key"),
    )

    invoice_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice_runs.id"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("billing_accounts.id"),
        nullable=False,
    )
    meter_key: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_label: Mapped[str] = mapped_column(String(64), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    source_record_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class BillingExport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "billing_exports"
    __table_args__ = (Index("ix_billing_exports_tenant_invoice", "tenant_id", "invoice_run_id"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    invoice_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoice_runs.id"),
        nullable=False,
    )
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
