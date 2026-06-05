from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

JsonObject = dict[str, object]
BillingExportFormat = Literal["json", "csv"]


@dataclass(frozen=True, slots=True)
class BillingNodeRecord:
    id: UUID
    tenant_id: UUID
    label: str
    kind: str
    created_at: datetime
    updated_at: datetime
    parent_id: UUID | None = None
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BillingAccountRecord:
    id: UUID
    tenant_id: UUID
    name: str
    node_ids: list[UUID]
    created_at: datetime
    updated_at: datetime
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EntitlementRecord:
    id: UUID
    tenant_id: UUID
    account_id: UUID
    feature_key: str
    effective_from: date
    created_at: datetime
    updated_at: datetime
    pack_id: str | None = None
    effective_to: date | None = None
    usage_limit: Decimal | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UsageMeterRecord:
    meter_key: str
    label: str
    unit_label: str
    aggregation: str
    category: str
    pack_id: str | None = None
    attributes: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PriceBookRecord:
    id: UUID
    currency: str
    effective_from: date
    meter_prices: dict[str, Decimal]
    created_at: datetime
    updated_at: datetime
    tenant_id: UUID | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class UsageRecord:
    id: UUID
    tenant_id: UUID
    meter_key: str
    quantity: Decimal
    source_object_type: str
    source_object_id: UUID
    occurred_on: date
    created_at: datetime
    account_id: UUID | None = None
    node_id: UUID | None = None
    pack_id: str | None = None
    source_started_on: date | None = None
    source_ended_on: date | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PricedLineItem:
    meter_key: str
    quantity: Decimal
    unit_label: str
    unit_price: Decimal
    total: Decimal
    currency: str
    pack_id: str | None = None


@dataclass(frozen=True, slots=True)
class InvoiceLineItemRecord:
    id: UUID
    invoice_run_id: UUID
    tenant_id: UUID
    account_id: UUID
    meter_key: str
    quantity: Decimal
    unit_label: str
    unit_price: Decimal
    total: Decimal
    currency: str
    period_start: date
    period_end: date
    source_record_ids: list[UUID]
    pack_id: str | None = None


@dataclass(frozen=True, slots=True)
class InvoiceRunRecord:
    id: UUID
    tenant_id: UUID
    account_id: UUID
    period_start: date
    period_end: date
    currency: str
    status: str
    created_at: datetime
    line_items: list[InvoiceLineItemRecord] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class BillingExportRecord:
    id: UUID
    tenant_id: UUID
    invoice_run_id: UUID
    format: BillingExportFormat
    payload: JsonObject
    created_at: datetime
