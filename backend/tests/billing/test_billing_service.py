from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from argus.billing.service import BillingNotFoundError, BillingService
from argus.billing.tables import BillingAccount, InvoiceLineItem, InvoiceRun, PriceBook
from argus.billing.tables import UsageRecord as UsageRecordRow
from argus.compat import UTC


def test_packless_billing_node_account_entitlement_usage_invoice_flow(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    node = billing_service.create_node(
        tenant_id=tenant_id,
        label="Generic deployment",
        kind="deployment",
        pack_id=None,
    )
    account = billing_service.create_account(
        tenant_id=tenant_id,
        name="Mugetsu Ops",
        node_ids=[node.id],
    )
    entitlement = billing_service.grant_entitlement(
        tenant_id=tenant_id,
        account_id=account.id,
        pack_id=None,
        feature_key="core_support",
        effective_from=date(2026, 6, 1),
    )
    usage = billing_service.record_usage(
        tenant_id=tenant_id,
        meter_key="support_session_hour",
        quantity=Decimal("1.5"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000020"),
    )
    invoice = billing_service.run_invoice(
        tenant_id=tenant_id,
        account_id=account.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )

    assert entitlement.pack_id is None
    assert usage.pack_id is None
    assert invoice.line_items[0].meter_key == "support_session_hour"


def test_price_book_prices_invoice_line_items(billing_service: BillingService) -> None:
    billing_service.create_price_book(
        currency="USD",
        effective_from=date(2026, 6, 1),
        meter_prices={
            "vessel_month": Decimal("299.00"),
            "evidence_pack_export": Decimal("9.00"),
        },
    )

    line = billing_service.price_line_item(
        meter_key="evidence_pack_export",
        quantity=Decimal("3"),
    )

    assert line.unit_price == Decimal("9.00")
    assert line.total == Decimal("27.00")


def test_billing_export_includes_usage_and_invoice_lines(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    account = billing_service.create_account(
        tenant_id=tenant_id,
        name="Export account",
        node_ids=[],
    )
    billing_service.create_price_book(
        currency="USD",
        effective_from=date(2026, 6, 1),
        meter_prices={"support_session_hour": Decimal("25.00")},
    )
    billing_service.record_usage(
        tenant_id=tenant_id,
        meter_key="support_session_hour",
        quantity=Decimal("2"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000021"),
    )
    invoice = billing_service.run_invoice(
        tenant_id=tenant_id,
        account_id=account.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )

    export = billing_service.export_billing(
        tenant_id=tenant_id,
        invoice_run_id=invoice.id,
        format="json",
    )

    assert export.format == "json"
    assert export.payload["invoice_run_id"] == str(invoice.id)
    assert export.payload["line_items"][0]["total"] == "50.00"


def test_billing_service_is_tenant_scoped(billing_service: BillingService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    other_tenant_id = UUID("00000000-0000-4000-8000-000000000099")
    billing_service.create_account(
        tenant_id=tenant_id,
        name="Visible account",
        node_ids=[],
    )
    billing_service.create_account(
        tenant_id=other_tenant_id,
        name="Hidden account",
        node_ids=[],
    )

    accounts = billing_service.list_accounts(tenant_id=tenant_id)

    assert [account.name for account in accounts] == ["Visible account"]


def test_usage_meter_catalog_stays_packless_by_default(
    billing_service: BillingService,
) -> None:
    meters = billing_service.list_meters()

    assert {meter.meter_key for meter in meters} >= {
        "support_session_hour",
        "evidence_pack_export",
        "managed_link_gb",
    }
    assert all(meter.pack_id is None for meter in meters)


def test_invoice_ignores_usage_outside_billing_period(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    account = billing_service.create_account(
        tenant_id=tenant_id,
        name="Windowed account",
        node_ids=[],
    )
    billing_service.record_usage(
        tenant_id=tenant_id,
        meter_key="support_session_hour",
        quantity=Decimal("2"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000022"),
        occurred_on=date(2026, 5, 31),
    )
    billing_service.record_usage(
        tenant_id=tenant_id,
        meter_key="support_session_hour",
        quantity=Decimal("3"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000023"),
        occurred_on=date(2026, 6, 15),
    )

    invoice = billing_service.run_invoice(
        tenant_id=tenant_id,
        account_id=account.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )

    assert invoice.line_items[0].quantity == Decimal("3")


def test_invoice_only_includes_usage_for_requested_account(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    node_a = billing_service.create_node(
        tenant_id=tenant_id,
        label="Deployment A",
        kind="deployment",
    )
    node_b = billing_service.create_node(
        tenant_id=tenant_id,
        label="Deployment B",
        kind="deployment",
    )
    account_a = billing_service.create_account(
        tenant_id=tenant_id,
        name="Account A",
        node_ids=[node_a.id],
    )
    account_b = billing_service.create_account(
        tenant_id=tenant_id,
        name="Account B",
        node_ids=[node_b.id],
    )
    billing_service.record_usage(
        tenant_id=tenant_id,
        account_id=account_a.id,
        node_id=node_a.id,
        meter_key="support_session_hour",
        quantity=Decimal("2"),
        source_object_type="support_session",
        source_object_id=UUID("00000000-0000-4000-8000-000000000024"),
        occurred_on=date(2026, 6, 15),
    )

    invoice_a = billing_service.run_invoice(
        tenant_id=tenant_id,
        account_id=account_a.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )
    invoice_b = billing_service.run_invoice(
        tenant_id=tenant_id,
        account_id=account_b.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )

    assert invoice_a.line_items[0].quantity == Decimal("2.000000")
    assert invoice_b.line_items == []


def test_account_node_links_must_belong_to_tenant(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    other_tenant_id = UUID("00000000-0000-4000-8000-000000000099")
    other_node = billing_service.create_node(
        tenant_id=other_tenant_id,
        label="Other deployment",
        kind="deployment",
    )

    with pytest.raises(BillingNotFoundError):
        billing_service.create_account(
            tenant_id=tenant_id,
            name="Invalid account",
            node_ids=[other_node.id],
        )


def test_usage_with_account_and_node_requires_account_node_link(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    node = billing_service.create_node(
        tenant_id=tenant_id,
        label="Deployment",
        kind="deployment",
    )
    account = billing_service.create_account(
        tenant_id=tenant_id,
        name="Tenant-wide account",
        node_ids=[],
    )

    with pytest.raises(BillingNotFoundError):
        billing_service.record_usage(
            tenant_id=tenant_id,
            account_id=account.id,
            node_id=node.id,
            meter_key="support_session_hour",
            quantity=Decimal("1"),
            source_object_type="support_session",
            source_object_id=UUID("00000000-0000-4000-8000-000000000025"),
        )


def test_billing_node_parent_must_belong_to_tenant(
    billing_service: BillingService,
) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    other_tenant_id = UUID("00000000-0000-4000-8000-000000000099")
    other_parent = billing_service.create_node(
        tenant_id=other_tenant_id,
        label="Other parent",
        kind="deployment",
    )

    with pytest.raises(BillingNotFoundError):
        billing_service.create_node(
            tenant_id=tenant_id,
            parent_id=other_parent.id,
            label="Invalid child",
            kind="deployment",
        )


@pytest.mark.asyncio
async def test_async_invoice_flushes_invoice_run_before_line_items() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    account_id = UUID("00000000-0000-4000-8000-000000000010")
    session_factory = _InvoiceOrderingSessionFactory(
        tenant_id=tenant_id,
        account_id=account_id,
    )
    billing = BillingService(session_factory)

    invoice = await billing.arun_invoice(
        tenant_id=tenant_id,
        account_id=account_id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 7, 1),
    )

    assert invoice.line_items[0].meter_key == "support_session_hour"
    assert session_factory.invoice_flush_count == 1


class _InvoiceOrderingSessionFactory:
    def __init__(self, *, tenant_id: UUID, account_id: UUID) -> None:
        now = datetime(2026, 6, 9, 12, 0, tzinfo=UTC)
        self.account = BillingAccount(
            id=account_id,
            tenant_id=tenant_id,
            name="Smoke account",
            node_ids=[],
            pack_id=None,
            attributes={},
        )
        self.account.created_at = now
        self.account.updated_at = now
        self.price_book = PriceBook(
            id=uuid4(),
            tenant_id=tenant_id,
            currency="USD",
            effective_from=date(2026, 6, 1),
            effective_to=None,
            meter_prices={"support_session_hour": "25.00"},
        )
        self.price_book.created_at = now
        self.price_book.updated_at = now
        self.usage = UsageRecordRow(
            id=uuid4(),
            tenant_id=tenant_id,
            meter_key="support_session_hour",
            quantity=Decimal("2"),
            account_id=account_id,
            node_id=None,
            source_object_type="support_session",
            source_object_id=UUID("00000000-0000-4000-8000-000000000020"),
            occurred_on=date(2026, 6, 15),
            source_started_on=None,
            source_ended_on=None,
            pack_id=None,
            attributes={},
        )
        self.usage.created_at = now
        self.invoice_flush_count = 0

    def __call__(self) -> _InvoiceOrderingSession:
        return _InvoiceOrderingSession(self)


class _InvoiceOrderingSession:
    def __init__(self, factory: _InvoiceOrderingSessionFactory) -> None:
        self.factory = factory
        self.invoice_row_added = False
        self.invoice_row_flushed = False

    async def __aenter__(self) -> _InvoiceOrderingSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def get(self, entity: type[object], row_id: object) -> object | None:
        if entity is BillingAccount and row_id == self.factory.account.id:
            return self.factory.account
        return None

    async def execute(self, statement):  # noqa: ANN001
        entity = statement.column_descriptions[0]["entity"]
        if entity is PriceBook:
            return _InvoiceOrderingResult([self.factory.price_book])
        if entity is UsageRecordRow:
            return _InvoiceOrderingResult([self.factory.usage])
        return _InvoiceOrderingResult([])

    def add(self, row: object) -> None:
        if isinstance(row, InvoiceRun):
            self.invoice_row_added = True
            return
        if isinstance(row, InvoiceLineItem):
            if not self.invoice_row_flushed:
                raise AssertionError("invoice line item added before invoice run flush")
            return

    async def flush(self) -> None:
        if self.invoice_row_added:
            self.invoice_row_flushed = True
            self.factory.invoice_flush_count += 1

    async def commit(self) -> None:
        return None


class _InvoiceOrderingResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _InvoiceOrderingResult:
        return self

    def all(self) -> list[object]:
        return list(self.rows)
