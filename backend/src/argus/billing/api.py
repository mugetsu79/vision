from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.billing.contracts import (
    BillingAccountRecord,
    BillingExportRecord,
    BillingNodeRecord,
    EntitlementRecord,
    InvoiceLineItemRecord,
    InvoiceRunRecord,
    JsonObject,
    PriceBookRecord,
    UsageMeterRecord,
    UsageRecord,
)
from argus.billing.service import BillingNotFoundError
from argus.core.security import AuthenticatedUser, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class BillingNodeCreate(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=64)
    parent_id: UUID | None = None
    pack_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, object] = Field(default_factory=dict)


class BillingAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    node_ids: list[UUID] = Field(default_factory=list)
    pack_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, object] = Field(default_factory=dict)


class EntitlementCreate(BaseModel):
    account_id: UUID
    feature_key: str = Field(min_length=1, max_length=128)
    effective_from: date
    pack_id: str | None = Field(default=None, max_length=128)
    effective_to: date | None = None
    usage_limit: Decimal | None = None
    attributes: dict[str, object] = Field(default_factory=dict)


class PriceBookCreate(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    effective_from: date
    effective_to: date | None = None
    meter_prices: dict[str, Decimal] = Field(default_factory=dict)


class UsageCreate(BaseModel):
    meter_key: str = Field(min_length=1, max_length=128)
    quantity: Decimal
    account_id: UUID | None = None
    node_id: UUID | None = None
    source_object_type: str = Field(min_length=1, max_length=80)
    source_object_id: UUID
    occurred_on: date | None = None
    source_started_on: date | None = None
    source_ended_on: date | None = None
    pack_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, object] = Field(default_factory=dict)


class InvoiceRunCreate(BaseModel):
    account_id: UUID
    period_start: date
    period_end: date


class InvoiceLineItemResponse(BaseModel):
    id: UUID
    invoice_run_id: UUID
    tenant_id: UUID
    account_id: UUID
    meter_key: str
    quantity: str
    unit_label: str
    unit_price: str
    total: str
    currency: str
    period_start: date
    period_end: date
    source_record_ids: list[UUID]
    pack_id: str | None = None


class InvoiceRunResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    account_id: UUID
    period_start: date
    period_end: date
    currency: str
    status: str
    created_at: str
    line_items: list[InvoiceLineItemResponse] = Field(default_factory=list)


class InvoiceRunListResponse(BaseModel):
    items: list[InvoiceRunResponse] = Field(default_factory=list)


@router.get("/nodes")
async def get_billing_nodes(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> JsonObject:
    _ensure_requested_tenant(tenant_context, tenant_id)
    nodes = await services.billing.alist_nodes(tenant_id=tenant_context.tenant_id)
    return {"items": [_node_payload(node) for node in nodes]}


@router.post("/nodes", status_code=status.HTTP_201_CREATED)
async def post_billing_node(
    payload: BillingNodeCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        node = await services.billing.acreate_node(
            tenant_id=tenant_context.tenant_id,
            label=payload.label,
            kind=payload.kind,
            parent_id=payload.parent_id,
            pack_id=payload.pack_id,
            attributes=payload.attributes,
        )
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _node_payload(node)


@router.get("/accounts")
async def get_billing_accounts(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> JsonObject:
    _ensure_requested_tenant(tenant_context, tenant_id)
    accounts = await services.billing.alist_accounts(tenant_id=tenant_context.tenant_id)
    return {"items": [_account_payload(account) for account in accounts]}


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def post_billing_account(
    payload: BillingAccountCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        account = await services.billing.acreate_account(
            tenant_id=tenant_context.tenant_id,
            name=payload.name,
            node_ids=payload.node_ids,
            pack_id=payload.pack_id,
            attributes=payload.attributes,
        )
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _account_payload(account)


@router.get("/entitlements")
async def get_entitlements(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    account_id: Annotated[UUID | None, Query()] = None,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> JsonObject:
    _ensure_requested_tenant(tenant_context, tenant_id)
    entitlements = await services.billing.alist_entitlements(
        tenant_id=tenant_context.tenant_id,
        account_id=account_id,
    )
    return {"items": [_entitlement_payload(entitlement) for entitlement in entitlements]}


@router.post("/entitlements", status_code=status.HTTP_201_CREATED)
async def post_entitlement(
    payload: EntitlementCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        entitlement = await services.billing.agrant_entitlement(
            tenant_id=tenant_context.tenant_id,
            account_id=payload.account_id,
            feature_key=payload.feature_key,
            effective_from=payload.effective_from,
            pack_id=payload.pack_id,
            effective_to=payload.effective_to,
            usage_limit=payload.usage_limit,
            attributes=payload.attributes,
        )
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _entitlement_payload(entitlement)


@router.get("/meters")
async def get_usage_meters(
    current_user: ViewerUser,
    services: ServicesDependency,
    pack_id: Annotated[str | None, Query(max_length=128)] = None,
) -> JsonObject:
    meters = await services.billing.alist_meters(pack_id=pack_id)
    return {"items": [_meter_payload(meter) for meter in meters]}


@router.get("/price-books")
async def get_price_books(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    price_books = await services.billing.alist_price_books(
        tenant_id=tenant_context.tenant_id,
    )
    return {"items": [_price_book_payload(price_book) for price_book in price_books]}


@router.post("/price-books", status_code=status.HTTP_201_CREATED)
async def post_price_book(
    payload: PriceBookCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    price_book = await services.billing.acreate_price_book(
        tenant_id=tenant_context.tenant_id,
        currency=payload.currency,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        meter_prices=payload.meter_prices,
    )
    return _price_book_payload(price_book)


@router.get("/usage")
async def get_usage(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    meter_key: Annotated[str | None, Query(max_length=128)] = None,
    pack_id: Annotated[str | None, Query(max_length=128)] = None,
    tenant_id: Annotated[UUID | None, Query()] = None,
) -> JsonObject:
    _ensure_requested_tenant(tenant_context, tenant_id)
    usage = await services.billing.alist_usage(
        tenant_id=tenant_context.tenant_id,
        meter_key=meter_key,
        pack_id=pack_id,
    )
    return {"items": [_usage_payload(record) for record in usage]}


@router.post("/usage", status_code=status.HTTP_201_CREATED)
async def post_usage(
    payload: UsageCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        usage = await services.billing.arecord_usage(
            tenant_id=tenant_context.tenant_id,
            meter_key=payload.meter_key,
            quantity=payload.quantity,
            account_id=payload.account_id,
            node_id=payload.node_id,
            source_object_type=payload.source_object_type,
            source_object_id=payload.source_object_id,
            occurred_on=payload.occurred_on,
            source_started_on=payload.source_started_on,
            source_ended_on=payload.source_ended_on,
            pack_id=payload.pack_id,
            metadata=payload.metadata,
        )
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _usage_payload(usage)


@router.post("/invoice-runs", status_code=status.HTTP_201_CREATED)
async def post_invoice_run(
    payload: InvoiceRunCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    try:
        invoice = await services.billing.arun_invoice(
            tenant_id=tenant_context.tenant_id,
            account_id=payload.account_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
        )
    except BillingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _invoice_payload(invoice)


@router.get("/invoice-runs", response_model=InvoiceRunListResponse)
async def get_invoice_runs(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> InvoiceRunListResponse:
    invoices = await services.billing.alist_invoice_runs(
        tenant_id=tenant_context.tenant_id,
    )
    return InvoiceRunListResponse(
        items=[InvoiceRunResponse.model_validate(_invoice_payload(invoice)) for invoice in invoices]
    )


@router.get("/invoice-runs/{invoice_run_id}")
async def get_invoice_run(
    invoice_run_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    invoice = await services.billing.aget_invoice_run(
        tenant_id=tenant_context.tenant_id,
        invoice_run_id=invoice_run_id,
    )
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice run not found.")
    return _invoice_payload(invoice)


@router.get("/exports/{export_id}")
async def get_billing_export(
    export_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    export = await services.billing.aget_export(
        tenant_id=tenant_context.tenant_id,
        export_id=export_id,
    )
    if export is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Billing export not found."
        )
    return _export_payload(export)


def _ensure_requested_tenant(
    tenant_context: TenantContext,
    requested_tenant_id: UUID | None,
) -> None:
    if requested_tenant_id is not None and requested_tenant_id != tenant_context.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch.")


def _node_payload(node: BillingNodeRecord) -> JsonObject:
    return {
        "id": str(node.id),
        "tenant_id": str(node.tenant_id),
        "parent_id": str(node.parent_id) if node.parent_id is not None else None,
        "label": node.label,
        "kind": node.kind,
        "pack_id": node.pack_id,
        "attributes": node.attributes,
        "created_at": node.created_at.isoformat(),
        "updated_at": node.updated_at.isoformat(),
    }


def _account_payload(account: BillingAccountRecord) -> JsonObject:
    return {
        "id": str(account.id),
        "tenant_id": str(account.tenant_id),
        "name": account.name,
        "node_ids": [str(node_id) for node_id in account.node_ids],
        "pack_id": account.pack_id,
        "attributes": account.attributes,
        "created_at": account.created_at.isoformat(),
        "updated_at": account.updated_at.isoformat(),
    }


def _entitlement_payload(entitlement: EntitlementRecord) -> JsonObject:
    return {
        "id": str(entitlement.id),
        "tenant_id": str(entitlement.tenant_id),
        "account_id": str(entitlement.account_id),
        "pack_id": entitlement.pack_id,
        "feature_key": entitlement.feature_key,
        "effective_from": entitlement.effective_from.isoformat(),
        "effective_to": (
            entitlement.effective_to.isoformat() if entitlement.effective_to is not None else None
        ),
        "usage_limit": (
            _decimal_text(entitlement.usage_limit) if entitlement.usage_limit is not None else None
        ),
        "attributes": entitlement.attributes,
        "created_at": entitlement.created_at.isoformat(),
        "updated_at": entitlement.updated_at.isoformat(),
    }


def _meter_payload(meter: UsageMeterRecord) -> JsonObject:
    return {
        "meter_key": meter.meter_key,
        "label": meter.label,
        "unit_label": meter.unit_label,
        "aggregation": meter.aggregation,
        "category": meter.category,
        "pack_id": meter.pack_id,
        "attributes": meter.attributes,
    }


def _price_book_payload(price_book: PriceBookRecord) -> JsonObject:
    return {
        "id": str(price_book.id),
        "tenant_id": str(price_book.tenant_id) if price_book.tenant_id is not None else None,
        "currency": price_book.currency,
        "effective_from": price_book.effective_from.isoformat(),
        "effective_to": (
            price_book.effective_to.isoformat() if price_book.effective_to is not None else None
        ),
        "meter_prices": {
            meter_key: _decimal_text(price) for meter_key, price in price_book.meter_prices.items()
        },
        "created_at": price_book.created_at.isoformat(),
        "updated_at": price_book.updated_at.isoformat(),
    }


def _usage_payload(record: UsageRecord) -> JsonObject:
    return {
        "id": str(record.id),
        "tenant_id": str(record.tenant_id),
        "meter_key": record.meter_key,
        "quantity": _decimal_text(record.quantity),
        "account_id": str(record.account_id) if record.account_id is not None else None,
        "node_id": str(record.node_id) if record.node_id is not None else None,
        "source_object_type": record.source_object_type,
        "source_object_id": str(record.source_object_id),
        "occurred_on": record.occurred_on.isoformat(),
        "source_started_on": (
            record.source_started_on.isoformat() if record.source_started_on is not None else None
        ),
        "source_ended_on": (
            record.source_ended_on.isoformat() if record.source_ended_on is not None else None
        ),
        "pack_id": record.pack_id,
        "metadata": record.metadata,
        "created_at": record.created_at.isoformat(),
    }


def _invoice_payload(invoice: InvoiceRunRecord) -> JsonObject:
    return {
        "id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "account_id": str(invoice.account_id),
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "currency": invoice.currency,
        "status": invoice.status,
        "created_at": invoice.created_at.isoformat(),
        "line_items": [_line_item_payload(line) for line in invoice.line_items],
    }


def _line_item_payload(line: InvoiceLineItemRecord) -> JsonObject:
    return {
        "id": str(line.id),
        "invoice_run_id": str(line.invoice_run_id),
        "tenant_id": str(line.tenant_id),
        "account_id": str(line.account_id),
        "meter_key": line.meter_key,
        "quantity": _decimal_text(line.quantity),
        "unit_label": line.unit_label,
        "unit_price": _decimal_text(line.unit_price),
        "total": _decimal_text(line.total),
        "currency": line.currency,
        "period_start": line.period_start.isoformat(),
        "period_end": line.period_end.isoformat(),
        "source_record_ids": [str(record_id) for record_id in line.source_record_ids],
        "pack_id": line.pack_id,
    }


def _export_payload(export: BillingExportRecord) -> JsonObject:
    return {
        "id": str(export.id),
        "tenant_id": str(export.tenant_id),
        "invoice_run_id": str(export.invoice_run_id),
        "format": export.format,
        "payload": export.payload,
        "created_at": export.created_at.isoformat(),
    }


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")
