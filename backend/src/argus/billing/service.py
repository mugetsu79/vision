from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.billing.contracts import (
    BillingAccountRecord,
    BillingExportFormat,
    BillingExportRecord,
    BillingNodeRecord,
    EntitlementRecord,
    InvoiceLineItemRecord,
    InvoiceRunRecord,
    JsonObject,
    PriceBookRecord,
    PricedLineItem,
    UsageMeterRecord,
    UsageRecord,
)
from argus.billing.tables import (
    BillingAccount,
    BillingExport,
    BillingNode,
    Entitlement,
    InvoiceLineItem,
    InvoiceRun,
    PriceBook,
)
from argus.billing.tables import (
    UsageRecord as UsageRecordRow,
)
from argus.compat import UTC

CORE_USAGE_METERS: tuple[UsageMeterRecord, ...] = (
    UsageMeterRecord(
        meter_key="support_session_hour",
        label="support session hour",
        unit_label="hour",
        aggregation="sum",
        category="value",
    ),
    UsageMeterRecord(
        meter_key="evidence_pack_export",
        label="evidence pack export",
        unit_label="export",
        aggregation="sum",
        category="value",
    ),
    UsageMeterRecord(
        meter_key="managed_link_gb",
        label="managed link GB",
        unit_label="GB",
        aggregation="sum",
        category="capacity_guardrail",
    ),
    UsageMeterRecord(
        meter_key="retained_evidence_gb",
        label="retained evidence GB",
        unit_label="GB",
        aggregation="sum",
        category="capacity_guardrail",
    ),
    UsageMeterRecord(
        meter_key="managed_edge_node",
        label="managed edge node",
        unit_label="node",
        aggregation="max",
        category="capacity_guardrail",
    ),
    UsageMeterRecord(
        meter_key="camera_capacity_tier",
        label="camera capacity tier",
        unit_label="tier",
        aggregation="max",
        category="capacity_guardrail",
    ),
)
MONEY_QUANT = Decimal("0.01")
QUANTITY_QUANT = Decimal("0.000001")


class BillingError(ValueError):
    pass


class BillingNotFoundError(BillingError):
    pass


class BillingService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory
        self._nodes: dict[UUID, BillingNodeRecord] = {}
        self._accounts: dict[UUID, BillingAccountRecord] = {}
        self._entitlements: dict[UUID, EntitlementRecord] = {}
        self._price_books: list[PriceBookRecord] = []
        self._usage_records: dict[UUID, UsageRecord] = {}
        self._invoice_runs: dict[UUID, InvoiceRunRecord] = {}
        self._exports: dict[UUID, BillingExportRecord] = {}

    def create_node(
        self,
        *,
        tenant_id: UUID,
        label: str,
        kind: str,
        parent_id: UUID | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> BillingNodeRecord:
        if parent_id is not None:
            self._node_or_raise(tenant_id=tenant_id, node_id=parent_id)
        now = _now()
        node = BillingNodeRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            parent_id=parent_id,
            label=label,
            kind=kind,
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._nodes[node.id] = node
        return node

    async def acreate_node(
        self,
        *,
        tenant_id: UUID,
        label: str,
        kind: str,
        parent_id: UUID | None = None,
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> BillingNodeRecord:
        if self.session_factory is None:
            return self.create_node(
                tenant_id=tenant_id,
                label=label,
                kind=kind,
                parent_id=parent_id,
                pack_id=pack_id,
                attributes=attributes,
            )
        if parent_id is not None:
            await self._db_node_or_raise(tenant_id=tenant_id, node_id=parent_id)
        now = _now()
        row = BillingNode(
            id=uuid4(),
            tenant_id=tenant_id,
            parent_id=parent_id,
            label=label,
            kind=kind,
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _node_record(row)

    def list_nodes(self, *, tenant_id: UUID) -> list[BillingNodeRecord]:
        return sorted(
            (node for node in self._nodes.values() if node.tenant_id == tenant_id),
            key=lambda node: (node.label, str(node.id)),
        )

    async def alist_nodes(self, *, tenant_id: UUID) -> list[BillingNodeRecord]:
        if self.session_factory is None:
            return self.list_nodes(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(BillingNode)
                .where(BillingNode.tenant_id == tenant_id)
                .order_by(BillingNode.label)
            )
        return [_node_record(row) for row in result.scalars().all()]

    def create_account(
        self,
        *,
        tenant_id: UUID,
        name: str,
        node_ids: Sequence[UUID],
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> BillingAccountRecord:
        for node_id in node_ids:
            self._node_or_raise(tenant_id=tenant_id, node_id=node_id)
        now = _now()
        account = BillingAccountRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            node_ids=list(node_ids),
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._accounts[account.id] = account
        return account

    async def acreate_account(
        self,
        *,
        tenant_id: UUID,
        name: str,
        node_ids: Sequence[UUID],
        pack_id: str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> BillingAccountRecord:
        if self.session_factory is None:
            return self.create_account(
                tenant_id=tenant_id,
                name=name,
                node_ids=node_ids,
                pack_id=pack_id,
                attributes=attributes,
            )
        for node_id in node_ids:
            await self._db_node_or_raise(tenant_id=tenant_id, node_id=node_id)
        now = _now()
        row = BillingAccount(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            node_ids=[str(node_id) for node_id in node_ids],
            pack_id=pack_id,
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _account_record(row)

    def list_accounts(self, *, tenant_id: UUID) -> list[BillingAccountRecord]:
        return sorted(
            (account for account in self._accounts.values() if account.tenant_id == tenant_id),
            key=lambda account: (account.name, str(account.id)),
        )

    async def alist_accounts(self, *, tenant_id: UUID) -> list[BillingAccountRecord]:
        if self.session_factory is None:
            return self.list_accounts(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(BillingAccount)
                .where(BillingAccount.tenant_id == tenant_id)
                .order_by(BillingAccount.name)
            )
        return [_account_record(row) for row in result.scalars().all()]

    def grant_entitlement(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        feature_key: str,
        effective_from: date,
        pack_id: str | None = None,
        effective_to: date | None = None,
        usage_limit: Decimal | int | str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> EntitlementRecord:
        self._account_or_raise(tenant_id=tenant_id, account_id=account_id)
        now = _now()
        entitlement = EntitlementRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            pack_id=pack_id,
            feature_key=feature_key,
            effective_from=effective_from,
            effective_to=effective_to,
            usage_limit=_optional_decimal(usage_limit),
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        self._entitlements[entitlement.id] = entitlement
        return entitlement

    async def agrant_entitlement(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        feature_key: str,
        effective_from: date,
        pack_id: str | None = None,
        effective_to: date | None = None,
        usage_limit: Decimal | int | str | None = None,
        attributes: Mapping[str, object] | None = None,
    ) -> EntitlementRecord:
        if self.session_factory is None:
            return self.grant_entitlement(
                tenant_id=tenant_id,
                account_id=account_id,
                feature_key=feature_key,
                effective_from=effective_from,
                pack_id=pack_id,
                effective_to=effective_to,
                usage_limit=usage_limit,
                attributes=attributes,
            )
        await self._db_account_or_raise(tenant_id=tenant_id, account_id=account_id)
        now = _now()
        row = Entitlement(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            pack_id=pack_id,
            feature_key=feature_key,
            effective_from=effective_from,
            effective_to=effective_to,
            usage_limit=_optional_decimal(usage_limit),
            attributes=_json_object(attributes),
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _entitlement_record(row)

    def list_entitlements(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID | None = None,
    ) -> list[EntitlementRecord]:
        return sorted(
            (
                entitlement
                for entitlement in self._entitlements.values()
                if entitlement.tenant_id == tenant_id
                and (account_id is None or entitlement.account_id == account_id)
            ),
            key=lambda entitlement: (entitlement.feature_key, str(entitlement.id)),
        )

    async def alist_entitlements(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID | None = None,
    ) -> list[EntitlementRecord]:
        if self.session_factory is None:
            return self.list_entitlements(tenant_id=tenant_id, account_id=account_id)
        async with self.session_factory() as session:
            statement = select(Entitlement).where(Entitlement.tenant_id == tenant_id)
            if account_id is not None:
                statement = statement.where(Entitlement.account_id == account_id)
            result = await session.execute(statement.order_by(Entitlement.feature_key))
        return [_entitlement_record(row) for row in result.scalars().all()]

    def record_usage(
        self,
        *,
        tenant_id: UUID,
        meter_key: str,
        quantity: Decimal | int | str,
        source_object_type: str,
        source_object_id: UUID,
        account_id: UUID | None = None,
        node_id: UUID | None = None,
        occurred_on: date | None = None,
        pack_id: str | None = None,
        source_started_on: date | None = None,
        source_ended_on: date | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> UsageRecord:
        account_id, node_id = self._resolve_usage_scope(
            tenant_id=tenant_id,
            account_id=account_id,
            node_id=node_id,
        )
        record = UsageRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            meter_key=meter_key,
            quantity=_quantity_decimal(quantity),
            account_id=account_id,
            node_id=node_id,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            occurred_on=occurred_on or date.today(),
            source_started_on=source_started_on,
            source_ended_on=source_ended_on,
            pack_id=pack_id,
            metadata=_json_object(metadata),
            created_at=_now(),
        )
        self._usage_records[record.id] = record
        return record

    async def arecord_usage(
        self,
        *,
        tenant_id: UUID,
        meter_key: str,
        quantity: Decimal | int | str,
        source_object_type: str,
        source_object_id: UUID,
        account_id: UUID | None = None,
        node_id: UUID | None = None,
        occurred_on: date | None = None,
        pack_id: str | None = None,
        source_started_on: date | None = None,
        source_ended_on: date | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> UsageRecord:
        if self.session_factory is None:
            return self.record_usage(
                tenant_id=tenant_id,
                meter_key=meter_key,
                quantity=quantity,
                source_object_type=source_object_type,
                source_object_id=source_object_id,
                account_id=account_id,
                node_id=node_id,
                occurred_on=occurred_on,
                pack_id=pack_id,
                source_started_on=source_started_on,
                source_ended_on=source_ended_on,
                metadata=metadata,
            )
        account_id, node_id = await self._resolve_db_usage_scope(
            tenant_id=tenant_id,
            account_id=account_id,
            node_id=node_id,
        )
        row = UsageRecordRow(
            id=uuid4(),
            tenant_id=tenant_id,
            meter_key=meter_key,
            quantity=_quantity_decimal(quantity),
            account_id=account_id,
            node_id=node_id,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            occurred_on=occurred_on or date.today(),
            source_started_on=source_started_on,
            source_ended_on=source_ended_on,
            pack_id=pack_id,
            attributes=_json_object(metadata),
            created_at=_now(),
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _usage_record(row)

    def list_usage(
        self,
        *,
        tenant_id: UUID,
        meter_key: str | None = None,
        pack_id: str | None = None,
    ) -> list[UsageRecord]:
        return sorted(
            (
                record
                for record in self._usage_records.values()
                if record.tenant_id == tenant_id
                and (meter_key is None or record.meter_key == meter_key)
                and (pack_id is None or record.pack_id == pack_id)
            ),
            key=lambda record: (record.occurred_on, record.meter_key, str(record.id)),
        )

    async def alist_usage(
        self,
        *,
        tenant_id: UUID,
        meter_key: str | None = None,
        pack_id: str | None = None,
    ) -> list[UsageRecord]:
        if self.session_factory is None:
            return self.list_usage(tenant_id=tenant_id, meter_key=meter_key, pack_id=pack_id)
        async with self.session_factory() as session:
            statement = select(UsageRecordRow).where(UsageRecordRow.tenant_id == tenant_id)
            if meter_key is not None:
                statement = statement.where(UsageRecordRow.meter_key == meter_key)
            if pack_id is not None:
                statement = statement.where(UsageRecordRow.pack_id == pack_id)
            result = await session.execute(
                statement.order_by(UsageRecordRow.occurred_on, UsageRecordRow.meter_key)
            )
        return [_usage_record(row) for row in result.scalars().all()]

    def list_meters(self, *, pack_id: str | None = None) -> list[UsageMeterRecord]:
        return [meter for meter in CORE_USAGE_METERS if pack_id is None or meter.pack_id == pack_id]

    async def alist_meters(self, *, pack_id: str | None = None) -> list[UsageMeterRecord]:
        return self.list_meters(pack_id=pack_id)

    def create_price_book(
        self,
        *,
        currency: str,
        effective_from: date,
        meter_prices: Mapping[str, Decimal | int | str],
        tenant_id: UUID | None = None,
        effective_to: date | None = None,
    ) -> PriceBookRecord:
        now = _now()
        price_book = PriceBookRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            currency=currency.upper(),
            effective_from=effective_from,
            effective_to=effective_to,
            meter_prices={
                meter_key: _money_decimal(price) for meter_key, price in meter_prices.items()
            },
            created_at=now,
            updated_at=now,
        )
        self._price_books.append(price_book)
        return price_book

    async def acreate_price_book(
        self,
        *,
        currency: str,
        effective_from: date,
        meter_prices: Mapping[str, Decimal | int | str],
        tenant_id: UUID | None = None,
        effective_to: date | None = None,
    ) -> PriceBookRecord:
        if self.session_factory is None:
            return self.create_price_book(
                tenant_id=tenant_id,
                currency=currency,
                effective_from=effective_from,
                effective_to=effective_to,
                meter_prices=meter_prices,
            )
        now = _now()
        row = PriceBook(
            id=uuid4(),
            tenant_id=tenant_id,
            currency=currency.upper(),
            effective_from=effective_from,
            effective_to=effective_to,
            meter_prices={
                meter_key: str(_money_decimal(price)) for meter_key, price in meter_prices.items()
            },
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _price_book_record(row)

    def list_price_books(self, *, tenant_id: UUID | None = None) -> list[PriceBookRecord]:
        return sorted(
            (
                price_book
                for price_book in self._price_books
                if tenant_id is None
                or price_book.tenant_id is None
                or price_book.tenant_id == tenant_id
            ),
            key=lambda price_book: (price_book.effective_from, str(price_book.id)),
        )

    async def alist_price_books(
        self,
        *,
        tenant_id: UUID | None = None,
    ) -> list[PriceBookRecord]:
        if self.session_factory is None:
            return self.list_price_books(tenant_id=tenant_id)
        async with self.session_factory() as session:
            statement = select(PriceBook)
            if tenant_id is not None:
                statement = statement.where(
                    (PriceBook.tenant_id.is_(None)) | (PriceBook.tenant_id == tenant_id)
                )
            result = await session.execute(statement.order_by(PriceBook.effective_from))
        return [_price_book_record(row) for row in result.scalars().all()]

    def price_line_item(
        self,
        *,
        meter_key: str,
        quantity: Decimal | int | str,
        pack_id: str | None = None,
        as_of: date | None = None,
        tenant_id: UUID | None = None,
    ) -> PricedLineItem:
        return self._price_line_item(
            meter_key=meter_key,
            quantity=quantity,
            price_books=self.list_price_books(tenant_id=tenant_id),
            pack_id=pack_id,
            as_of=as_of,
            tenant_id=tenant_id,
        )

    def run_invoice(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        period_start: date,
        period_end: date,
    ) -> InvoiceRunRecord:
        account = self._account_or_raise(tenant_id=tenant_id, account_id=account_id)
        usage_records = [
            usage
            for usage in self._usage_records.values()
            if usage.tenant_id == tenant_id and period_start <= usage.occurred_on < period_end
        ]
        usage_records = [
            usage
            for usage in usage_records
            if _usage_belongs_to_account(usage, account)
        ]
        invoice = self._build_invoice_record(
            tenant_id=tenant_id,
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            usage_records=usage_records,
            price_books=self.list_price_books(tenant_id=tenant_id),
        )
        self._invoice_runs[invoice.id] = invoice
        return invoice

    async def arun_invoice(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        period_start: date,
        period_end: date,
    ) -> InvoiceRunRecord:
        if self.session_factory is None:
            return self.run_invoice(
                tenant_id=tenant_id,
                account_id=account_id,
                period_start=period_start,
                period_end=period_end,
            )
        account = await self._db_account_or_raise(tenant_id=tenant_id, account_id=account_id)
        price_books = await self.alist_price_books(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(UsageRecordRow).where(
                    UsageRecordRow.tenant_id == tenant_id,
                    UsageRecordRow.occurred_on >= period_start,
                    UsageRecordRow.occurred_on < period_end,
                )
            )
            usage_records = [_usage_record(row) for row in result.scalars().all()]
            usage_records = [
                usage
                for usage in usage_records
                if _usage_belongs_to_account(usage, account)
            ]
            invoice = self._build_invoice_record(
                tenant_id=tenant_id,
                account_id=account_id,
                period_start=period_start,
                period_end=period_end,
                usage_records=usage_records,
                price_books=price_books,
            )
            invoice_row = InvoiceRun(
                id=invoice.id,
                tenant_id=tenant_id,
                account_id=account_id,
                period_start=period_start,
                period_end=period_end,
                currency=invoice.currency,
                status=invoice.status,
                created_at=invoice.created_at,
            )
            session.add(invoice_row)
            await session.flush()
            for line in invoice.line_items:
                session.add(_line_item_row(line))
            await session.commit()
        return invoice

    def get_invoice_run(
        self,
        *,
        tenant_id: UUID,
        invoice_run_id: UUID,
    ) -> InvoiceRunRecord | None:
        invoice = self._invoice_runs.get(invoice_run_id)
        if invoice is None or invoice.tenant_id != tenant_id:
            return None
        return invoice

    async def aget_invoice_run(
        self,
        *,
        tenant_id: UUID,
        invoice_run_id: UUID,
    ) -> InvoiceRunRecord | None:
        if self.session_factory is None:
            return self.get_invoice_run(tenant_id=tenant_id, invoice_run_id=invoice_run_id)
        async with self.session_factory() as session:
            invoice = await session.get(InvoiceRun, invoice_run_id)
            if invoice is None or invoice.tenant_id != tenant_id:
                return None
            result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.invoice_run_id == invoice_run_id)
                .order_by(InvoiceLineItem.meter_key)
            )
        return _invoice_run_record(
            invoice,
            [_line_item_record(row) for row in result.scalars().all()],
        )

    def list_invoice_runs(self, *, tenant_id: UUID) -> list[InvoiceRunRecord]:
        return sorted(
            (
                invoice
                for invoice in self._invoice_runs.values()
                if invoice.tenant_id == tenant_id
            ),
            key=lambda invoice: invoice.created_at,
            reverse=True,
        )

    async def alist_invoice_runs(self, *, tenant_id: UUID) -> list[InvoiceRunRecord]:
        if self.session_factory is None:
            return self.list_invoice_runs(tenant_id=tenant_id)
        async with self.session_factory() as session:
            invoice_result = await session.execute(
                select(InvoiceRun)
                .where(InvoiceRun.tenant_id == tenant_id)
                .order_by(InvoiceRun.created_at.desc())
            )
            invoices = list(invoice_result.scalars().all())
            if not invoices:
                return []
            invoice_ids = [invoice.id for invoice in invoices]
            line_result = await session.execute(
                select(InvoiceLineItem)
                .where(InvoiceLineItem.invoice_run_id.in_(invoice_ids))
                .order_by(InvoiceLineItem.meter_key)
            )
        lines_by_invoice_id: dict[UUID, list[InvoiceLineItemRecord]] = {
            invoice_id: [] for invoice_id in invoice_ids
        }
        for row in line_result.scalars().all():
            lines_by_invoice_id.setdefault(row.invoice_run_id, []).append(
                _line_item_record(row)
            )
        return [
            _invoice_run_record(invoice, lines_by_invoice_id.get(invoice.id, []))
            for invoice in invoices
        ]

    def export_billing(
        self,
        *,
        tenant_id: UUID,
        invoice_run_id: UUID,
        format: BillingExportFormat = "json",
    ) -> BillingExportRecord:
        invoice = self.get_invoice_run(tenant_id=tenant_id, invoice_run_id=invoice_run_id)
        if invoice is None:
            raise BillingNotFoundError("Invoice run not found.")
        export = BillingExportRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            invoice_run_id=invoice_run_id,
            format=format,
            payload=_export_payload(invoice, format=format),
            created_at=_now(),
        )
        self._exports[export.id] = export
        return export

    async def aexport_billing(
        self,
        *,
        tenant_id: UUID,
        invoice_run_id: UUID,
        format: BillingExportFormat = "json",
    ) -> BillingExportRecord:
        if self.session_factory is None:
            return self.export_billing(
                tenant_id=tenant_id,
                invoice_run_id=invoice_run_id,
                format=format,
            )
        invoice = await self.aget_invoice_run(tenant_id=tenant_id, invoice_run_id=invoice_run_id)
        if invoice is None:
            raise BillingNotFoundError("Invoice run not found.")
        export = BillingExportRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            invoice_run_id=invoice_run_id,
            format=format,
            payload=_export_payload(invoice, format=format),
            created_at=_now(),
        )
        async with self.session_factory() as session:
            row = BillingExport(
                id=export.id,
                tenant_id=tenant_id,
                invoice_run_id=invoice_run_id,
                format=format,
                payload=export.payload,
                created_at=export.created_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _billing_export_record(row)

    def get_export(
        self,
        *,
        tenant_id: UUID,
        export_id: UUID,
    ) -> BillingExportRecord | None:
        export = self._exports.get(export_id)
        if export is None or export.tenant_id != tenant_id:
            return None
        return export

    async def aget_export(
        self,
        *,
        tenant_id: UUID,
        export_id: UUID,
    ) -> BillingExportRecord | None:
        if self.session_factory is None:
            return self.get_export(tenant_id=tenant_id, export_id=export_id)
        async with self.session_factory() as session:
            row = await session.get(BillingExport, export_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _billing_export_record(row)

    def _build_invoice_record(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        period_start: date,
        period_end: date,
        usage_records: Sequence[UsageRecord],
        price_books: Sequence[PriceBookRecord],
    ) -> InvoiceRunRecord:
        invoice_id = uuid4()
        grouped: dict[tuple[str, str | None], list[UsageRecord]] = {}
        for usage in usage_records:
            grouped.setdefault((usage.meter_key, usage.pack_id), []).append(usage)
        lines: list[InvoiceLineItemRecord] = []
        currency = "USD"
        for (meter_key, pack_id), records in sorted(grouped.items(), key=lambda item: item[0][0]):
            quantity = sum((record.quantity for record in records), Decimal("0"))
            priced = self._price_line_item(
                tenant_id=tenant_id,
                meter_key=meter_key,
                quantity=quantity,
                price_books=price_books,
                pack_id=pack_id,
                as_of=period_start,
            )
            currency = priced.currency
            lines.append(
                InvoiceLineItemRecord(
                    id=uuid4(),
                    invoice_run_id=invoice_id,
                    tenant_id=tenant_id,
                    account_id=account_id,
                    meter_key=meter_key,
                    quantity=quantity,
                    unit_label=priced.unit_label,
                    unit_price=priced.unit_price,
                    total=priced.total,
                    currency=priced.currency,
                    period_start=period_start,
                    period_end=period_end,
                    source_record_ids=[record.id for record in records],
                    pack_id=pack_id,
                )
            )
        return InvoiceRunRecord(
            id=invoice_id,
            tenant_id=tenant_id,
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            status="generated",
            created_at=_now(),
            line_items=lines,
        )

    def _price_line_item(
        self,
        *,
        meter_key: str,
        quantity: Decimal | int | str,
        price_books: Sequence[PriceBookRecord],
        pack_id: str | None = None,
        tenant_id: UUID | None,
        as_of: date | None,
    ) -> PricedLineItem:
        quantity_decimal = _quantity_decimal(quantity)
        price_book = self._active_price_book(
            price_books=price_books,
            tenant_id=tenant_id,
            as_of=as_of,
        )
        unit_price = (
            price_book.meter_prices.get(meter_key, Decimal("0.00"))
            if price_book is not None
            else Decimal("0.00")
        )
        currency = price_book.currency if price_book is not None else "USD"
        meter = self._meter_for_key(meter_key)
        return PricedLineItem(
            meter_key=meter_key,
            quantity=quantity_decimal,
            unit_label=meter.unit_label,
            unit_price=_money_decimal(unit_price),
            total=_money_decimal(quantity_decimal * unit_price),
            currency=currency,
            pack_id=pack_id,
        )

    @staticmethod
    def _active_price_book(
        *,
        price_books: Sequence[PriceBookRecord],
        tenant_id: UUID | None,
        as_of: date | None,
    ) -> PriceBookRecord | None:
        effective_on = as_of or date.today()
        candidates = [
            price_book
            for price_book in price_books
            if price_book.effective_from <= effective_on
            and (price_book.effective_to is None or price_book.effective_to > effective_on)
            and (
                tenant_id is None
                or price_book.tenant_id is None
                or price_book.tenant_id == tenant_id
            )
        ]
        return max(candidates, key=lambda price_book: price_book.effective_from, default=None)

    def _meter_for_key(self, meter_key: str) -> UsageMeterRecord:
        return next(
            (meter for meter in CORE_USAGE_METERS if meter.meter_key == meter_key),
            UsageMeterRecord(
                meter_key=meter_key,
                label=meter_key.replace("_", " "),
                unit_label="unit",
                aggregation="sum",
                category="custom",
            ),
        )

    def _account_or_raise(self, *, tenant_id: UUID, account_id: UUID) -> BillingAccountRecord:
        account = self._accounts.get(account_id)
        if account is None or account.tenant_id != tenant_id:
            raise BillingNotFoundError("Billing account not found.")
        return account

    def _node_or_raise(self, *, tenant_id: UUID, node_id: UUID) -> BillingNodeRecord:
        node = self._nodes.get(node_id)
        if node is None or node.tenant_id != tenant_id:
            raise BillingNotFoundError("Billing node not found.")
        return node

    def _resolve_usage_scope(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID | None,
        node_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None]:
        account = (
            self._account_or_raise(tenant_id=tenant_id, account_id=account_id)
            if account_id is not None
            else None
        )
        if node_id is not None:
            self._node_or_raise(tenant_id=tenant_id, node_id=node_id)
        if account is not None and node_id is not None:
            if node_id not in account.node_ids:
                raise BillingNotFoundError("Billing node not linked to account.")
        if account_id is None and node_id is not None:
            account_id = _single_account_for_node(
                accounts=self.list_accounts(tenant_id=tenant_id),
                node_id=node_id,
            )
        if account_id is None and node_id is None:
            account_id = _single_account_for_tenant(self.list_accounts(tenant_id=tenant_id))
        return account_id, node_id

    async def _db_account_or_raise(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
    ) -> BillingAccountRecord:
        if self.session_factory is None:
            return self._account_or_raise(tenant_id=tenant_id, account_id=account_id)
        async with self.session_factory() as session:
            row = await session.get(BillingAccount, account_id)
        if row is None or row.tenant_id != tenant_id:
            raise BillingNotFoundError("Billing account not found.")
        return _account_record(row)

    async def _db_node_or_raise(self, *, tenant_id: UUID, node_id: UUID) -> BillingNodeRecord:
        if self.session_factory is None:
            return self._node_or_raise(tenant_id=tenant_id, node_id=node_id)
        async with self.session_factory() as session:
            row = await session.get(BillingNode, node_id)
        if row is None or row.tenant_id != tenant_id:
            raise BillingNotFoundError("Billing node not found.")
        return _node_record(row)

    async def _resolve_db_usage_scope(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID | None,
        node_id: UUID | None,
    ) -> tuple[UUID | None, UUID | None]:
        account = (
            await self._db_account_or_raise(tenant_id=tenant_id, account_id=account_id)
            if account_id is not None
            else None
        )
        if node_id is not None:
            await self._db_node_or_raise(tenant_id=tenant_id, node_id=node_id)
        if account is not None and node_id is not None:
            if node_id not in account.node_ids:
                raise BillingNotFoundError("Billing node not linked to account.")
        accounts = await self.alist_accounts(tenant_id=tenant_id)
        if account_id is None and node_id is not None:
            account_id = _single_account_for_node(accounts=accounts, node_id=node_id)
        if account_id is None and node_id is None:
            account_id = _single_account_for_tenant(accounts)
        return account_id, node_id


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_object(value: Mapping[str, object] | None) -> JsonObject:
    return dict(value or {})


def _quantity_decimal(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(QUANTITY_QUANT)


def _money_decimal(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _optional_decimal(value: Decimal | int | str | None) -> Decimal | None:
    if value is None:
        return None
    return _quantity_decimal(value)


def _node_record(row: BillingNode) -> BillingNodeRecord:
    return BillingNodeRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        parent_id=row.parent_id,
        label=row.label,
        kind=row.kind,
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _account_record(row: BillingAccount) -> BillingAccountRecord:
    return BillingAccountRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        node_ids=[UUID(str(node_id)) for node_id in row.node_ids],
        pack_id=row.pack_id,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _entitlement_record(row: Entitlement) -> EntitlementRecord:
    return EntitlementRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        account_id=row.account_id,
        pack_id=row.pack_id,
        feature_key=row.feature_key,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        usage_limit=row.usage_limit,
        attributes=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _price_book_record(row: PriceBook) -> PriceBookRecord:
    return PriceBookRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        currency=row.currency,
        effective_from=row.effective_from,
        effective_to=row.effective_to,
        meter_prices={
            meter_key: _money_decimal(price) for meter_key, price in row.meter_prices.items()
        },
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _usage_record(row: UsageRecordRow) -> UsageRecord:
    return UsageRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        meter_key=row.meter_key,
        quantity=_quantity_decimal(row.quantity),
        account_id=row.account_id,
        node_id=row.node_id,
        source_object_type=row.source_object_type,
        source_object_id=row.source_object_id,
        occurred_on=row.occurred_on,
        source_started_on=row.source_started_on,
        source_ended_on=row.source_ended_on,
        pack_id=row.pack_id,
        metadata=dict(row.attributes or {}),
        created_at=row.created_at,
    )


def _usage_belongs_to_account(
    usage: UsageRecord,
    account: BillingAccountRecord,
) -> bool:
    if usage.account_id is not None:
        return usage.account_id == account.id
    if usage.node_id is not None:
        return usage.node_id in account.node_ids
    return False


def _single_account_for_node(
    *,
    accounts: Sequence[BillingAccountRecord],
    node_id: UUID,
) -> UUID | None:
    candidates = [account.id for account in accounts if node_id in account.node_ids]
    return candidates[0] if len(candidates) == 1 else None


def _single_account_for_tenant(accounts: Sequence[BillingAccountRecord]) -> UUID | None:
    return accounts[0].id if len(accounts) == 1 else None


def _line_item_row(line: InvoiceLineItemRecord) -> InvoiceLineItem:
    return InvoiceLineItem(
        id=line.id,
        invoice_run_id=line.invoice_run_id,
        tenant_id=line.tenant_id,
        account_id=line.account_id,
        meter_key=line.meter_key,
        quantity=line.quantity,
        unit_label=line.unit_label,
        unit_price=line.unit_price,
        total=line.total,
        currency=line.currency,
        period_start=line.period_start,
        period_end=line.period_end,
        source_record_ids=[str(record_id) for record_id in line.source_record_ids],
        pack_id=line.pack_id,
    )


def _line_item_record(row: InvoiceLineItem) -> InvoiceLineItemRecord:
    return InvoiceLineItemRecord(
        id=row.id,
        invoice_run_id=row.invoice_run_id,
        tenant_id=row.tenant_id,
        account_id=row.account_id,
        meter_key=row.meter_key,
        quantity=_quantity_decimal(row.quantity),
        unit_label=row.unit_label,
        unit_price=_money_decimal(row.unit_price),
        total=_money_decimal(row.total),
        currency=row.currency,
        period_start=row.period_start,
        period_end=row.period_end,
        source_record_ids=[UUID(str(record_id)) for record_id in row.source_record_ids],
        pack_id=row.pack_id,
    )


def _invoice_run_record(
    row: InvoiceRun,
    line_items: Sequence[InvoiceLineItemRecord],
) -> InvoiceRunRecord:
    return InvoiceRunRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        account_id=row.account_id,
        period_start=row.period_start,
        period_end=row.period_end,
        currency=row.currency,
        status=row.status,
        created_at=row.created_at,
        line_items=list(line_items),
    )


def _billing_export_record(row: BillingExport) -> BillingExportRecord:
    return BillingExportRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        invoice_run_id=row.invoice_run_id,
        format="csv" if row.format == "csv" else "json",
        payload=dict(row.payload or {}),
        created_at=row.created_at,
    )


def _export_payload(invoice: InvoiceRunRecord, *, format: BillingExportFormat) -> JsonObject:
    line_items = [_line_payload(line) for line in invoice.line_items]
    payload: JsonObject = {
        "invoice_run_id": str(invoice.id),
        "tenant_id": str(invoice.tenant_id),
        "account_id": str(invoice.account_id),
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "currency": invoice.currency,
        "line_items": line_items,
    }
    if format == "csv":
        payload["csv"] = _csv_payload(line_items)
    return payload


def _line_payload(line: InvoiceLineItemRecord) -> JsonObject:
    return {
        "id": str(line.id),
        "meter_key": line.meter_key,
        "quantity": _decimal_text(line.quantity),
        "unit_label": line.unit_label,
        "unit_price": _decimal_text(line.unit_price),
        "total": _decimal_text(line.total),
        "currency": line.currency,
        "pack_id": line.pack_id,
        "source_record_ids": [str(record_id) for record_id in line.source_record_ids],
    }


def _csv_payload(line_items: Sequence[JsonObject]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["meter_key", "quantity", "unit_label", "unit_price", "total", "currency"],
    )
    writer.writeheader()
    for line in line_items:
        writer.writerow(
            {
                "meter_key": line["meter_key"],
                "quantity": line["quantity"],
                "unit_label": line["unit_label"],
                "unit_price": line["unit_price"],
                "total": line["total"],
                "currency": line["currency"],
            }
        )
    return output.getvalue()


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")
