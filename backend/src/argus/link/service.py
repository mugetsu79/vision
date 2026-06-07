from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.link.contracts import (
    LINK_PRIORITY_ORDER,
    BackpressureDecision,
    JsonObject,
    LinkAvailabilityScope,
    LinkBudgetSnapshot,
    LinkConnectionRecord,
    LinkConnectionStatus,
    LinkHealthProbeRecord,
    LinkPassportSnapshotRecord,
    LinkPriorityLane,
    LinkProbeSampleKind,
    LinkProbeSourceType,
    LinkProbeType,
    LinkQueueItemRecord,
    LinkSiteSummaryRecord,
    LinkState,
    LinkTransferAttemptRecord,
    LinkTransportKind,
)
from argus.link.tables import (
    LinkBudget,
    LinkConnection,
    LinkHealthProbe,
    LinkPassportSnapshot,
    LinkQueueItem,
    LinkTransferAttempt,
)

LINK_STATES = {"unknown", "healthy", "degraded", "dark", "recovering", "port_wifi"}
LINK_TRANSPORT_KINDS = {"satellite", "lte", "5g", "wifi", "fiber", "ethernet", "other"}
LINK_CONNECTION_STATUSES = {"unknown", "online", "degraded", "offline", "blocked", "recovering"}
LINK_AVAILABILITY_SCOPES = {"always", "remote", "nearby", "local", "maintenance"}
LINK_USABLE_CONNECTION_STATUSES = {"online", "recovering", "degraded"}
LINK_CONNECTION_STATUS_ORDER = {
    "online": 0,
    "recovering": 1,
    "degraded": 2,
    "offline": 3,
    "blocked": 4,
    "unknown": 5,
}
QUEUE_STATUSES = {"queued", "paused", "interrupted", "succeeded", "failed"}
TRANSFER_ATTEMPT_STATUSES = {"interrupted", "succeeded", "failed"}


class LinkService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory
        self._budgets: dict[tuple[UUID, UUID], LinkBudgetSnapshot] = {}
        self._connections: dict[UUID, LinkConnectionRecord] = {}
        self._queue_items: dict[UUID, LinkQueueItemRecord] = {}
        self._attempts: dict[UUID, LinkTransferAttemptRecord] = {}
        self._probes: list[LinkHealthProbeRecord] = []
        self._passports: list[LinkPassportSnapshotRecord] = []
        self._policies: dict[tuple[UUID, UUID], JsonObject] = {}

    def upsert_budget(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        monthly_bytes: int,
        bulk_daily_bytes: int,
    ) -> LinkBudgetSnapshot:
        self._ensure_memory_mode()
        now = _now()
        existing = self._budgets.get((tenant_id, site_id))
        budget = LinkBudgetSnapshot(
            id=existing.id if existing is not None else uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            monthly_bytes=monthly_bytes,
            bulk_daily_bytes=bulk_daily_bytes,
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        self._budgets[(tenant_id, site_id)] = budget
        return budget

    def get_budget(self, *, tenant_id: UUID, site_id: UUID) -> LinkBudgetSnapshot | None:
        self._ensure_memory_mode()
        return self._budgets.get((tenant_id, site_id))

    async def aupsert_budget(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        monthly_bytes: int,
        bulk_daily_bytes: int,
    ) -> LinkBudgetSnapshot:
        if self.session_factory is None:
            return self.upsert_budget(
                tenant_id=tenant_id,
                site_id=site_id,
                monthly_bytes=monthly_bytes,
                bulk_daily_bytes=bulk_daily_bytes,
            )
        async with self.session_factory() as session:
            budget = await self._find_budget_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            now = _now()
            if budget is None:
                budget = LinkBudget(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    site_id=site_id,
                    monthly_bytes=monthly_bytes,
                    bulk_daily_bytes=bulk_daily_bytes,
                    policy={},
                    created_at=now,
                    updated_at=now,
                )
                session.add(budget)
            else:
                budget.monthly_bytes = monthly_bytes
                budget.bulk_daily_bytes = bulk_daily_bytes
                budget.updated_at = now
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                budget = await self._find_budget_row(
                    session,
                    tenant_id=tenant_id,
                    site_id=site_id,
                )
                if budget is None:
                    raise
                budget.monthly_bytes = monthly_bytes
                budget.bulk_daily_bytes = bulk_daily_bytes
                budget.updated_at = now
                await session.commit()
            await session.refresh(budget)
            return _budget_record(budget)

    async def aget_budget(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> LinkBudgetSnapshot | None:
        if self.session_factory is None:
            return self.get_budget(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as session:
            budget = await self._find_budget_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            return _budget_record(budget) if budget is not None else None

    def upsert_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        label: str,
        transport_kind: LinkTransportKind,
        status: LinkConnectionStatus = "unknown",
        priority_rank: int = 100,
        availability_scope: LinkAvailabilityScope = "always",
        metered: bool = False,
        provider: str | None = None,
        monthly_bytes: int | None = None,
        bulk_daily_bytes: int | None = None,
        expected_downlink_mbps: float | None = None,
        expected_uplink_mbps: float | None = None,
        expected_latency_ms: int | None = None,
        packet_loss_percent: float | None = None,
        last_seen_at: datetime | None = None,
        metadata: JsonObject | None = None,
        connection_id: UUID | None = None,
    ) -> LinkConnectionRecord:
        self._ensure_memory_mode()
        _validate_connection_values(
            label=label,
            transport_kind=transport_kind,
            status=status,
            priority_rank=priority_rank,
            availability_scope=availability_scope,
        )
        existing = self._connections.get(connection_id) if connection_id is not None else None
        if existing is not None and (
            existing.tenant_id != tenant_id or existing.site_id != site_id
        ):
            raise ValueError("Connection not found.")
        now = _now()
        record = LinkConnectionRecord(
            id=existing.id if existing is not None else connection_id or uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            label=label.strip(),
            transport_kind=transport_kind,
            provider=provider.strip() if provider is not None else None,
            status=status,
            priority_rank=priority_rank,
            availability_scope=availability_scope,
            metered=metered,
            monthly_bytes=monthly_bytes,
            bulk_daily_bytes=bulk_daily_bytes,
            expected_downlink_mbps=expected_downlink_mbps,
            expected_uplink_mbps=expected_uplink_mbps,
            expected_latency_ms=expected_latency_ms,
            packet_loss_percent=packet_loss_percent,
            last_seen_at=last_seen_at,
            metadata=dict(metadata or {}),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        self._connections[record.id] = record
        return record

    async def aupsert_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        label: str,
        transport_kind: LinkTransportKind,
        status: LinkConnectionStatus = "unknown",
        priority_rank: int = 100,
        availability_scope: LinkAvailabilityScope = "always",
        metered: bool = False,
        provider: str | None = None,
        monthly_bytes: int | None = None,
        bulk_daily_bytes: int | None = None,
        expected_downlink_mbps: float | None = None,
        expected_uplink_mbps: float | None = None,
        expected_latency_ms: int | None = None,
        packet_loss_percent: float | None = None,
        last_seen_at: datetime | None = None,
        metadata: JsonObject | None = None,
        connection_id: UUID | None = None,
    ) -> LinkConnectionRecord:
        _validate_connection_values(
            label=label,
            transport_kind=transport_kind,
            status=status,
            priority_rank=priority_rank,
            availability_scope=availability_scope,
        )
        if self.session_factory is None:
            return self.upsert_connection(
                tenant_id=tenant_id,
                site_id=site_id,
                label=label,
                transport_kind=transport_kind,
                status=status,
                priority_rank=priority_rank,
                availability_scope=availability_scope,
                metered=metered,
                provider=provider,
                monthly_bytes=monthly_bytes,
                bulk_daily_bytes=bulk_daily_bytes,
                expected_downlink_mbps=expected_downlink_mbps,
                expected_uplink_mbps=expected_uplink_mbps,
                expected_latency_ms=expected_latency_ms,
                packet_loss_percent=packet_loss_percent,
                last_seen_at=last_seen_at,
                metadata=metadata,
                connection_id=connection_id,
            )
        async with self.session_factory() as session:
            row = (
                await session.get(LinkConnection, connection_id)
                if connection_id is not None
                else None
            )
            if row is not None and (row.tenant_id != tenant_id or row.site_id != site_id):
                raise ValueError("Connection not found.")
            now = _now()
            if row is None:
                row = LinkConnection(
                    id=connection_id or uuid4(),
                    tenant_id=tenant_id,
                    site_id=site_id,
                    label=label.strip(),
                    transport_kind=transport_kind,
                    provider=provider.strip() if provider is not None else None,
                    status=status,
                    priority_rank=priority_rank,
                    availability_scope=availability_scope,
                    metered=metered,
                    monthly_bytes=monthly_bytes,
                    bulk_daily_bytes=bulk_daily_bytes,
                    expected_downlink_mbps=expected_downlink_mbps,
                    expected_uplink_mbps=expected_uplink_mbps,
                    expected_latency_ms=expected_latency_ms,
                    packet_loss_percent=packet_loss_percent,
                    last_seen_at=last_seen_at,
                    connection_metadata=dict(metadata or {}),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.label = label.strip()
                row.transport_kind = transport_kind
                row.provider = provider.strip() if provider is not None else None
                row.status = status
                row.priority_rank = priority_rank
                row.availability_scope = availability_scope
                row.metered = metered
                row.monthly_bytes = monthly_bytes
                row.bulk_daily_bytes = bulk_daily_bytes
                row.expected_downlink_mbps = expected_downlink_mbps
                row.expected_uplink_mbps = expected_uplink_mbps
                row.expected_latency_ms = expected_latency_ms
                row.packet_loss_percent = packet_loss_percent
                row.last_seen_at = last_seen_at
                row.connection_metadata = dict(metadata or {})
                row.updated_at = now
            await session.commit()
            await session.refresh(row)
            return _connection_record(row)

    def list_connections(self, *, tenant_id: UUID, site_id: UUID) -> list[LinkConnectionRecord]:
        self._ensure_memory_mode()
        return _sort_connections(
            [
                connection
                for connection in self._connections.values()
                if connection.tenant_id == tenant_id and connection.site_id == site_id
            ]
        )

    async def alist_connections(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> list[LinkConnectionRecord]:
        if self.session_factory is None:
            return self.list_connections(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(LinkConnection).where(
                    LinkConnection.tenant_id == tenant_id,
                    LinkConnection.site_id == site_id,
                )
            )
            rows = cast(list[LinkConnection], result.scalars().all())
        return _sort_connections([_connection_record(row) for row in rows])

    def target_for_connection_metadata(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        target_id: str,
    ) -> JsonObject | None:
        self._ensure_memory_mode()
        for connection in self.list_connections(tenant_id=tenant_id, site_id=site_id):
            for target in _metadata_targets(connection.metadata):
                if target.get("id") == target_id:
                    return target
        return None

    async def atarget_for_connection_metadata(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        target_id: str,
    ) -> JsonObject | None:
        if self.session_factory is None:
            return self.target_for_connection_metadata(
                tenant_id=tenant_id,
                site_id=site_id,
                target_id=target_id,
            )
        for connection in await self.alist_connections(tenant_id=tenant_id, site_id=site_id):
            for target in _metadata_targets(connection.metadata):
                if target.get("id") == target_id:
                    return target
        return None

    def get_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID,
    ) -> LinkConnectionRecord | None:
        self._ensure_memory_mode()
        connection = self._connections.get(connection_id)
        if connection is None or connection.tenant_id != tenant_id or connection.site_id != site_id:
            return None
        return connection

    async def aget_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID,
    ) -> LinkConnectionRecord | None:
        if self.session_factory is None:
            return self.get_connection(
                tenant_id=tenant_id,
                site_id=site_id,
                connection_id=connection_id,
            )
        async with self.session_factory() as session:
            row = await session.get(LinkConnection, connection_id)
        if row is None or row.tenant_id != tenant_id or row.site_id != site_id:
            return None
        return _connection_record(row)

    def delete_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID,
    ) -> bool:
        self._ensure_memory_mode()
        connection = self.get_connection(
            tenant_id=tenant_id,
            site_id=site_id,
            connection_id=connection_id,
        )
        if connection is None:
            return False
        del self._connections[connection_id]
        self._probes = [
            replace(probe, connection_id=None)
            if probe.connection_id == connection_id
            else probe
            for probe in self._probes
        ]
        return True

    async def adelete_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID,
    ) -> bool:
        if self.session_factory is None:
            return self.delete_connection(
                tenant_id=tenant_id,
                site_id=site_id,
                connection_id=connection_id,
            )
        async with self.session_factory() as session:
            row = await session.get(LinkConnection, connection_id)
            if row is None or row.tenant_id != tenant_id or row.site_id != site_id:
                return False
            result = await session.execute(
                select(LinkHealthProbe).where(LinkHealthProbe.connection_id == connection_id)
            )
            probes = cast(list[LinkHealthProbe], result.scalars().all())
            for probe in probes:
                if probe.connection_id == connection_id:
                    probe.connection_id = None
            await session.delete(row)
            await session.commit()
            return True

    def select_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        priority_lane: LinkPriorityLane,
        remaining_budget_bytes: int,
    ) -> LinkConnectionRecord | None:
        self._ensure_memory_mode()
        connections = self.list_connections(tenant_id=tenant_id, site_id=site_id)
        return _select_connection(
            connections,
            priority_lane=priority_lane,
            remaining_budget_bytes=remaining_budget_bytes,
        )

    async def aselect_connection(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        priority_lane: LinkPriorityLane,
        remaining_budget_bytes: int,
    ) -> LinkConnectionRecord | None:
        connections = await self.alist_connections(tenant_id=tenant_id, site_id=site_id)
        return _select_connection(
            connections,
            priority_lane=priority_lane,
            remaining_budget_bytes=remaining_budget_bytes,
        )

    def list_site_summaries(
        self,
        *,
        tenant_id: UUID,
        sites: Sequence[Mapping[str, object]],
    ) -> list[LinkSiteSummaryRecord]:
        self._ensure_memory_mode()
        summaries: list[LinkSiteSummaryRecord] = []
        for site in sites:
            site_id = cast(UUID, site["id"])
            connections = self.list_connections(tenant_id=tenant_id, site_id=site_id)
            budget = self.get_budget(tenant_id=tenant_id, site_id=site_id)
            active_connection = _select_connection(
                connections,
                priority_lane="bulk",
                remaining_budget_bytes=(
                    budget.bulk_daily_bytes if budget is not None else 0
                ),
            )
            latest_probe = self.latest_probe(tenant_id=tenant_id, site_id=site_id)
            queue = self.list_queue(tenant_id=tenant_id, site_id=site_id)
            last_sync_at = self.last_successful_transfer_at(
                tenant_id=tenant_id,
                site_id=site_id,
            )
            passport = self.build_passport(tenant_id=tenant_id, site_id=site_id)
            summaries.append(
                LinkSiteSummaryRecord(
                    site_id=site_id,
                    site_name=str(site["name"]),
                    site_tz=str(site.get("tz", "UTC")),
                    link_state=self.derive_link_state(latest_probe),
                    active_connection=active_connection,
                    connection_count=len(connections),
                    metered_connection_count=sum(
                        1 for connection in connections if connection.metered
                    ),
                    latest_probe=latest_probe,
                    queue_depth=self.queue_depth_by_lane(queue),
                    queued_bytes=sum(
                        item.byte_size
                        for item in queue
                        if item.status not in {"paused", "succeeded"}
                    ),
                    budget=budget,
                    last_sync_at=last_sync_at,
                    passport_hash=passport.passport_hash,
                )
            )
        return summaries

    async def alist_site_summaries(
        self,
        *,
        tenant_id: UUID,
        sites: Sequence[Mapping[str, object]],
    ) -> list[LinkSiteSummaryRecord]:
        if self.session_factory is None:
            return self.list_site_summaries(tenant_id=tenant_id, sites=sites)
        summaries: list[LinkSiteSummaryRecord] = []
        for site in sites:
            site_id = cast(UUID, site["id"])
            connections = await self.alist_connections(
                tenant_id=tenant_id,
                site_id=site_id,
            )
            budget = await self.aget_budget(tenant_id=tenant_id, site_id=site_id)
            active_connection = _select_connection(
                connections,
                priority_lane="bulk",
                remaining_budget_bytes=(
                    budget.bulk_daily_bytes if budget is not None else 0
                ),
            )
            latest_probe = await self.alatest_probe(
                tenant_id=tenant_id,
                site_id=site_id,
            )
            queue = await self.alist_queue(tenant_id=tenant_id, site_id=site_id)
            last_sync_at = await self.alast_successful_transfer_at(
                tenant_id=tenant_id,
                site_id=site_id,
            )
            passport = await self.abuild_passport(tenant_id=tenant_id, site_id=site_id)
            summaries.append(
                LinkSiteSummaryRecord(
                    site_id=site_id,
                    site_name=str(site["name"]),
                    site_tz=str(site.get("tz", "UTC")),
                    link_state=self.derive_link_state(latest_probe),
                    active_connection=active_connection,
                    connection_count=len(connections),
                    metered_connection_count=sum(
                        1 for connection in connections if connection.metered
                    ),
                    latest_probe=latest_probe,
                    queue_depth=self.queue_depth_by_lane(queue),
                    queued_bytes=sum(
                        item.byte_size
                        for item in queue
                        if item.status not in {"paused", "succeeded"}
                    ),
                    budget=budget,
                    last_sync_at=last_sync_at,
                    passport_hash=passport.passport_hash,
                )
            )
        return summaries

    def enqueue_transfer(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        priority_lane: LinkPriorityLane,
        byte_size: int,
        source_object_type: str,
        source_object_id: UUID,
        camera_id: UUID | None = None,
        incident_id: UUID | None = None,
        evidence_artifact_id: UUID | None = None,
    ) -> LinkQueueItemRecord:
        self._ensure_memory_mode()
        _validate_priority_lane(priority_lane)
        item = self._make_queue_item(
            tenant_id=tenant_id,
            site_id=site_id,
            priority_lane=priority_lane,
            byte_size=byte_size,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            camera_id=camera_id,
            incident_id=incident_id,
            evidence_artifact_id=evidence_artifact_id,
        )
        self._queue_items[item.id] = item
        return item

    async def aenqueue_transfer(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        priority_lane: LinkPriorityLane,
        byte_size: int,
        source_object_type: str,
        source_object_id: UUID,
        camera_id: UUID | None = None,
        incident_id: UUID | None = None,
        evidence_artifact_id: UUID | None = None,
    ) -> LinkQueueItemRecord:
        _validate_priority_lane(priority_lane)
        if self.session_factory is None:
            return self.enqueue_transfer(
                tenant_id=tenant_id,
                site_id=site_id,
                priority_lane=priority_lane,
                byte_size=byte_size,
                source_object_type=source_object_type,
                source_object_id=source_object_id,
                camera_id=camera_id,
                incident_id=incident_id,
                evidence_artifact_id=evidence_artifact_id,
            )
        now = _now()
        queue_item = LinkQueueItem(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            incident_id=incident_id,
            evidence_artifact_id=evidence_artifact_id,
            priority_lane=priority_lane,
            byte_size=byte_size,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            status="queued",
            pause_reason=None,
            paused_at=None,
            last_successful_transfer_at=None,
            created_at=now,
            updated_at=now,
        )
        async with self.session_factory() as session:
            session.add(queue_item)
            await session.commit()
            await session.refresh(queue_item)
        return _queue_item_record(queue_item)

    def make_queue_item_for_test(
        self,
        *,
        priority_lane: LinkPriorityLane,
        byte_size: int,
    ) -> LinkQueueItemRecord:
        self._ensure_memory_mode()
        _validate_priority_lane(priority_lane)
        item = self._make_queue_item(
            tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
            site_id=UUID("00000000-0000-4000-8000-000000000002"),
            priority_lane=priority_lane,
            byte_size=byte_size,
            source_object_type="test_object",
            source_object_id=uuid4(),
        )
        self._queue_items[item.id] = item
        return item

    def _make_queue_item(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        priority_lane: LinkPriorityLane,
        byte_size: int,
        source_object_type: str,
        source_object_id: UUID,
        camera_id: UUID | None = None,
        incident_id: UUID | None = None,
        evidence_artifact_id: UUID | None = None,
    ) -> LinkQueueItemRecord:
        now = _now()
        return LinkQueueItemRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            priority_lane=priority_lane,
            byte_size=byte_size,
            source_object_type=source_object_type,
            source_object_id=source_object_id,
            status="queued",
            created_at=now,
            updated_at=now,
            camera_id=camera_id,
            incident_id=incident_id,
            evidence_artifact_id=evidence_artifact_id,
        )

    def record_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID | None = None,
        latency_ms: int,
        throughput_mbps: float,
        packet_loss_percent: float,
        reachable: bool,
        source: str,
        target_id: str | None = None,
        target_label: str | None = None,
        target_address: str | None = None,
        probe_type: LinkProbeType | None = None,
        source_type: LinkProbeSourceType = "manual",
        source_label: str | None = None,
        sample_kind: LinkProbeSampleKind = "manual",
        measurement_metadata: Mapping[str, object] | None = None,
    ) -> LinkHealthProbeRecord:
        self._ensure_memory_mode()
        if connection_id is not None:
            connection = self.get_connection(
                tenant_id=tenant_id,
                site_id=site_id,
                connection_id=connection_id,
            )
            if connection is None:
                raise ValueError("Connection not found.")
        probe = LinkHealthProbeRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            connection_id=connection_id,
            latency_ms=latency_ms,
            throughput_mbps=throughput_mbps,
            packet_loss_percent=packet_loss_percent,
            reachable=reachable,
            source=source,
            recorded_at=_now(),
            target_id=target_id,
            target_label=target_label,
            target_address=target_address,
            probe_type=probe_type,
            source_type=source_type,
            source_label=source_label,
            sample_kind=sample_kind,
            measurement_metadata=dict(measurement_metadata or {}),
        )
        self._probes.append(probe)
        return probe

    async def arecord_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        connection_id: UUID | None = None,
        latency_ms: int,
        throughput_mbps: float,
        packet_loss_percent: float,
        reachable: bool,
        source: str,
        target_id: str | None = None,
        target_label: str | None = None,
        target_address: str | None = None,
        probe_type: LinkProbeType | None = None,
        source_type: LinkProbeSourceType = "manual",
        source_label: str | None = None,
        sample_kind: LinkProbeSampleKind = "manual",
        measurement_metadata: Mapping[str, object] | None = None,
    ) -> LinkHealthProbeRecord:
        if connection_id is not None:
            connection = await self.aget_connection(
                tenant_id=tenant_id,
                site_id=site_id,
                connection_id=connection_id,
            )
            if connection is None:
                raise ValueError("Connection not found.")
        if self.session_factory is None:
            return self.record_probe(
                tenant_id=tenant_id,
                site_id=site_id,
                connection_id=connection_id,
                latency_ms=latency_ms,
                throughput_mbps=throughput_mbps,
                packet_loss_percent=packet_loss_percent,
                reachable=reachable,
                source=source,
                target_id=target_id,
                target_label=target_label,
                target_address=target_address,
                probe_type=probe_type,
                source_type=source_type,
                source_label=source_label,
                sample_kind=sample_kind,
                measurement_metadata=measurement_metadata,
            )
        probe = LinkHealthProbe(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            connection_id=connection_id,
            latency_ms=latency_ms,
            throughput_mbps=throughput_mbps,
            packet_loss_percent=packet_loss_percent,
            reachable=reachable,
            source=source,
            recorded_at=_now(),
            target_id=target_id,
            target_label=target_label,
            target_address=target_address,
            probe_type=probe_type,
            source_type=source_type,
            source_label=source_label,
            sample_kind=sample_kind,
            measurement_metadata=dict(measurement_metadata or {}),
        )
        async with self.session_factory() as session:
            session.add(probe)
            await session.commit()
            await session.refresh(probe)
        return _probe_record(probe)

    def list_probes(self, *, tenant_id: UUID, site_id: UUID) -> list[LinkHealthProbeRecord]:
        self._ensure_memory_mode()
        return [
            probe
            for probe in self._probes
            if probe.tenant_id == tenant_id
            and probe.site_id == site_id
            and probe.deleted_at is None
        ]

    def delete_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        probe_id: UUID,
    ) -> LinkHealthProbeRecord | None:
        self._ensure_memory_mode()
        deleted_at = _now()
        for index, probe in enumerate(self._probes):
            if probe.id == probe_id and probe.tenant_id == tenant_id and probe.site_id == site_id:
                deleted = replace(probe, deleted_at=deleted_at)
                self._probes[index] = deleted
                return deleted
        return None

    async def adelete_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        probe_id: UUID,
    ) -> LinkHealthProbeRecord | None:
        if self.session_factory is None:
            return self.delete_probe(
                tenant_id=tenant_id,
                site_id=site_id,
                probe_id=probe_id,
            )
        async with self.session_factory() as session:
            row = await session.get(LinkHealthProbe, probe_id)
            if row is None or row.tenant_id != tenant_id or row.site_id != site_id:
                return None
            row.deleted_at = _now()
            await session.commit()
            await session.refresh(row)
        return _probe_record(row)

    async def alist_probes(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> list[LinkHealthProbeRecord]:
        if self.session_factory is None:
            return self.list_probes(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as session:
            probes = await self._list_probe_rows(session, tenant_id=tenant_id, site_id=site_id)
        return [_probe_record(probe) for probe in probes]

    def latest_probe(self, *, tenant_id: UUID, site_id: UUID) -> LinkHealthProbeRecord | None:
        self._ensure_memory_mode()
        probes = self.list_probes(tenant_id=tenant_id, site_id=site_id)
        if not probes:
            return None
        return max(probes, key=lambda probe: probe.recorded_at)

    async def alatest_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> LinkHealthProbeRecord | None:
        probes = await self.alist_probes(tenant_id=tenant_id, site_id=site_id)
        if not probes:
            return None
        return max(probes, key=lambda probe: probe.recorded_at)

    def get_policy(self, *, tenant_id: UUID, site_id: UUID) -> JsonObject:
        self._ensure_memory_mode()
        return self._policies.get((tenant_id, site_id), _default_policy())

    def put_policy(self, *, tenant_id: UUID, site_id: UUID, policy: JsonObject) -> JsonObject:
        self._ensure_memory_mode()
        validated_policy = _validate_policy(policy)
        self._policies[(tenant_id, site_id)] = validated_policy
        return validated_policy

    async def aget_policy(self, *, tenant_id: UUID, site_id: UUID) -> JsonObject:
        if self.session_factory is None:
            return self.get_policy(tenant_id=tenant_id, site_id=site_id)
        async with self.session_factory() as session:
            budget = await self._find_budget_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            if budget is None or not budget.policy:
                return _default_policy()
            return dict(budget.policy)

    async def aput_policy(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        policy: JsonObject,
    ) -> JsonObject:
        if self.session_factory is None:
            return self.put_policy(tenant_id=tenant_id, site_id=site_id, policy=policy)
        async with self.session_factory() as session:
            budget = await self._find_budget_row(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            if budget is None:
                raise ValueError("Link budget not found.")
            validated_policy = _validate_policy(policy)
            budget.policy = validated_policy
            budget.updated_at = _now()
            await session.commit()
        return validated_policy

    def list_queue(
        self,
        *,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> list[LinkQueueItemRecord]:
        self._ensure_memory_mode()
        items = list(self._queue_items.values())
        if tenant_id is not None:
            items = [item for item in items if item.tenant_id == tenant_id]
        if site_id is not None:
            items = [item for item in items if item.site_id == site_id]
        if incident_id is not None:
            items = [item for item in items if item.incident_id == incident_id]
        return self.sort_queue(items)

    async def alist_queue(
        self,
        *,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> list[LinkQueueItemRecord]:
        if self.session_factory is None:
            return self.list_queue(tenant_id=tenant_id, site_id=site_id, incident_id=incident_id)
        async with self.session_factory() as session:
            rows = await self._list_queue_rows(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
                incident_id=incident_id,
            )
        return self.sort_queue([_queue_item_record(row) for row in rows])

    def sort_queue(
        self,
        items: Sequence[LinkQueueItemRecord],
    ) -> list[LinkQueueItemRecord]:
        return sorted(
            items,
            key=lambda item: (LINK_PRIORITY_ORDER[item.priority_lane], item.created_at),
        )

    def apply_backpressure(
        self,
        *,
        link_state: LinkState,
        remaining_daily_bulk_bytes: int,
        queue_depth_by_lane: Mapping[LinkPriorityLane, int],
    ) -> BackpressureDecision:
        _validate_link_state(link_state)
        lanes = set(queue_depth_by_lane)
        if link_state == "dark":
            return BackpressureDecision(
                paused_lanes=lanes - {"safety"},
                allowed_lanes=lanes & {"safety"},
                reason="link_dark",
            )
        if link_state in {"degraded", "recovering"} or remaining_daily_bulk_bytes <= 0:
            return BackpressureDecision(
                paused_lanes=lanes & {"telemetry", "bulk"},
                allowed_lanes=lanes & {"safety", "evidence"},
                reason="degraded_link_or_budget_exhausted",
            )
        return BackpressureDecision(
            paused_lanes=set(),
            allowed_lanes=lanes,
            reason="link_healthy",
        )

    def record_transfer_attempt(
        self,
        *,
        queue_item_id: UUID,
        status: str,
        bytes_transferred: int,
        resume_token: str | None = None,
        interruption_reason: str | None = None,
    ) -> LinkTransferAttemptRecord:
        self._ensure_memory_mode()
        _validate_transfer_attempt_status(status)
        queue_item = self.get_queue_item(queue_item_id)
        now = _now()
        attempt = LinkTransferAttemptRecord(
            id=uuid4(),
            queue_item_id=queue_item_id,
            status=status,
            bytes_transferred=bytes_transferred,
            resume_token=resume_token,
            interruption_reason=interruption_reason,
            created_at=now,
        )
        self._attempts[attempt.id] = attempt
        queue_item.status = status
        queue_item.updated_at = now
        if status == "succeeded":
            queue_item.last_successful_transfer_at = now
        self._queue_items[queue_item.id] = queue_item
        return attempt

    async def arecord_transfer_attempt(
        self,
        *,
        queue_item_id: UUID,
        status: str,
        bytes_transferred: int,
        resume_token: str | None = None,
        interruption_reason: str | None = None,
    ) -> LinkTransferAttemptRecord:
        _validate_transfer_attempt_status(status)
        if self.session_factory is None:
            return self.record_transfer_attempt(
                queue_item_id=queue_item_id,
                status=status,
                bytes_transferred=bytes_transferred,
                resume_token=resume_token,
                interruption_reason=interruption_reason,
            )
        async with self.session_factory() as session:
            queue_item = await session.get(LinkQueueItem, queue_item_id)
            if queue_item is None:
                raise ValueError("Queue item not found.")
            now = _now()
            attempt = LinkTransferAttempt(
                id=uuid4(),
                queue_item_id=queue_item_id,
                status=status,
                bytes_transferred=bytes_transferred,
                resume_token=resume_token,
                interruption_reason=interruption_reason,
                created_at=now,
            )
            session.add(attempt)
            queue_item.status = status
            queue_item.updated_at = now
            if status == "succeeded":
                queue_item.last_successful_transfer_at = now
            await session.commit()
            await session.refresh(attempt)
            await session.refresh(queue_item)
        return _attempt_record(attempt)

    def get_queue_item(self, queue_item_id: UUID) -> LinkQueueItemRecord:
        self._ensure_memory_mode()
        try:
            return self._queue_items[queue_item_id]
        except KeyError as exc:
            raise ValueError("Queue item not found.") from exc

    async def aget_queue_item(self, queue_item_id: UUID) -> LinkQueueItemRecord:
        if self.session_factory is None:
            return self.get_queue_item(queue_item_id)
        async with self.session_factory() as session:
            queue_item = await session.get(LinkQueueItem, queue_item_id)
            if queue_item is None:
                raise ValueError("Queue item not found.")
            return _queue_item_record(queue_item)

    def pause_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
        reason: str = "manual_pause",
    ) -> LinkQueueItemRecord | None:
        self._ensure_memory_mode()
        item = self._queue_items.get(queue_item_id)
        if item is None or item.tenant_id != tenant_id:
            return None
        now = _now()
        item.status = "paused"
        item.pause_reason = reason
        item.paused_at = now
        item.updated_at = now
        return item

    async def apause_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
        reason: str = "manual_pause",
    ) -> LinkQueueItemRecord | None:
        if self.session_factory is None:
            return self.pause_queue_item(
                tenant_id=tenant_id,
                queue_item_id=queue_item_id,
                reason=reason,
            )
        return await self._update_queue_status(
            tenant_id=tenant_id,
            queue_item_id=queue_item_id,
            status="paused",
            pause_reason=reason,
        )

    def resume_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
    ) -> LinkQueueItemRecord | None:
        self._ensure_memory_mode()
        item = self._queue_items.get(queue_item_id)
        if item is None or item.tenant_id != tenant_id:
            return None
        item.status = "queued"
        item.pause_reason = None
        item.paused_at = None
        item.updated_at = _now()
        return item

    async def aresume_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
    ) -> LinkQueueItemRecord | None:
        if self.session_factory is None:
            return self.resume_queue_item(tenant_id=tenant_id, queue_item_id=queue_item_id)
        return await self._update_queue_status(
            tenant_id=tenant_id,
            queue_item_id=queue_item_id,
            status="queued",
            pause_reason=None,
        )

    def retry_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
    ) -> LinkQueueItemRecord | None:
        self._ensure_memory_mode()
        item = self._queue_items.get(queue_item_id)
        if item is None or item.tenant_id != tenant_id:
            return None
        item.status = "queued"
        item.updated_at = _now()
        return item

    async def aretry_queue_item(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
    ) -> LinkQueueItemRecord | None:
        if self.session_factory is None:
            return self.retry_queue_item(tenant_id=tenant_id, queue_item_id=queue_item_id)
        return await self._update_queue_status(
            tenant_id=tenant_id,
            queue_item_id=queue_item_id,
            status="queued",
            pause_reason=None,
        )

    def build_passport(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        camera_id: UUID | None = None,
        incident_id: UUID | None = None,
        evidence_artifact_id: UUID | None = None,
    ) -> LinkPassportSnapshotRecord:
        self._ensure_memory_mode()
        budget = self.get_budget(tenant_id=tenant_id, site_id=site_id)
        connections = self.list_connections(tenant_id=tenant_id, site_id=site_id)
        selected_connection = _select_connection(
            connections,
            priority_lane="bulk",
            remaining_budget_bytes=budget.bulk_daily_bytes if budget is not None else 0,
        )
        latest_probe = self.latest_probe(tenant_id=tenant_id, site_id=site_id)
        queue = self.list_queue(tenant_id=tenant_id, site_id=site_id, incident_id=incident_id)
        queue_depth = self.queue_depth_by_lane(queue)
        link_state = self.derive_link_state(latest_probe)
        last_sync_at = self.last_successful_transfer_at(
            tenant_id=tenant_id,
            site_id=site_id,
            incident_id=incident_id,
        )
        payload = {
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "site_id": str(site_id),
            "camera_id": str(camera_id) if camera_id is not None else None,
            "incident_id": str(incident_id) if incident_id is not None else None,
            "evidence_artifact_id": (
                str(evidence_artifact_id) if evidence_artifact_id is not None else None
            ),
            "pack_id": None,
            "link_state": link_state,
            "active_connection": (
                _connection_payload(selected_connection)
                if selected_connection is not None
                else None
            ),
            "connections": [_connection_payload(connection) for connection in connections],
            "budget": _budget_payload(budget),
            "queue_depth": queue_depth,
            "latest_probe": _probe_payload(latest_probe),
            "last_sync_at": last_sync_at.isoformat() if last_sync_at is not None else None,
        }
        passport = LinkPassportSnapshotRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            incident_id=incident_id,
            evidence_artifact_id=evidence_artifact_id,
            pack_id=None,
            link_state=link_state,
            passport_hash=self.hash_passport_payload(payload),
            payload=payload,
            created_at=_now(),
            last_sync_at=last_sync_at,
        )
        self._passports.append(passport)
        return passport

    async def abuild_passport(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        camera_id: UUID | None = None,
        incident_id: UUID | None = None,
        evidence_artifact_id: UUID | None = None,
    ) -> LinkPassportSnapshotRecord:
        if self.session_factory is None:
            return self.build_passport(
                tenant_id=tenant_id,
                site_id=site_id,
                camera_id=camera_id,
                incident_id=incident_id,
                evidence_artifact_id=evidence_artifact_id,
            )
        budget = await self.aget_budget(tenant_id=tenant_id, site_id=site_id)
        connections = await self.alist_connections(tenant_id=tenant_id, site_id=site_id)
        selected_connection = _select_connection(
            connections,
            priority_lane="bulk",
            remaining_budget_bytes=budget.bulk_daily_bytes if budget is not None else 0,
        )
        latest_probe = await self.alatest_probe(tenant_id=tenant_id, site_id=site_id)
        queue = await self.alist_queue(
            tenant_id=tenant_id,
            site_id=site_id,
            incident_id=incident_id,
        )
        queue_depth = self.queue_depth_by_lane(queue)
        link_state = self.derive_link_state(latest_probe)
        last_sync_at = await self.alast_successful_transfer_at(
            tenant_id=tenant_id,
            site_id=site_id,
            incident_id=incident_id,
        )
        payload = {
            "schema_version": 1,
            "tenant_id": str(tenant_id),
            "site_id": str(site_id),
            "camera_id": str(camera_id) if camera_id is not None else None,
            "incident_id": str(incident_id) if incident_id is not None else None,
            "evidence_artifact_id": (
                str(evidence_artifact_id) if evidence_artifact_id is not None else None
            ),
            "pack_id": None,
            "link_state": link_state,
            "active_connection": (
                _connection_payload(selected_connection)
                if selected_connection is not None
                else None
            ),
            "connections": [_connection_payload(connection) for connection in connections],
            "budget": _budget_payload(budget),
            "queue_depth": queue_depth,
            "latest_probe": _probe_payload(latest_probe),
            "last_sync_at": last_sync_at.isoformat() if last_sync_at is not None else None,
        }
        passport_hash = self.hash_passport_payload(payload)
        now = _now()
        passport = LinkPassportSnapshot(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            camera_id=camera_id,
            incident_id=incident_id,
            evidence_artifact_id=evidence_artifact_id,
            pack_id=None,
            link_state=link_state,
            passport_hash=passport_hash,
            passport=payload,
            last_sync_at=last_sync_at,
            created_at=now,
        )
        async with self.session_factory() as session:
            existing = await self._find_passport_row_by_hash(session, passport_hash)
            if existing is not None:
                return _passport_record(existing)
            session.add(passport)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await self._find_passport_row_by_hash(session, passport_hash)
                if existing is not None:
                    return _passport_record(existing)
                raise
            await session.refresh(passport)
        return _passport_record(passport)

    def build_incident_passport(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
    ) -> LinkPassportSnapshotRecord | None:
        self._ensure_memory_mode()
        item = next(
            (
                queue_item
                for queue_item in self._queue_items.values()
                if queue_item.tenant_id == tenant_id and queue_item.incident_id == incident_id
            ),
            None,
        )
        if item is None:
            return None
        return self.build_passport(
            tenant_id=tenant_id,
            site_id=item.site_id,
            camera_id=item.camera_id,
            incident_id=incident_id,
            evidence_artifact_id=item.evidence_artifact_id,
        )

    async def abuild_incident_passport(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
    ) -> LinkPassportSnapshotRecord | None:
        queue = await self.alist_queue(tenant_id=tenant_id, incident_id=incident_id)
        if not queue:
            return None
        item = queue[0]
        return await self.abuild_passport(
            tenant_id=tenant_id,
            site_id=item.site_id,
            camera_id=item.camera_id,
            incident_id=incident_id,
            evidence_artifact_id=item.evidence_artifact_id,
        )

    def queue_depth_by_lane(
        self,
        items: Sequence[LinkQueueItemRecord],
    ) -> dict[LinkPriorityLane, int]:
        return {
            lane: sum(
                1
                for item in items
                if item.priority_lane == lane and item.status not in {"paused", "succeeded"}
            )
            for lane in LINK_PRIORITY_ORDER
        }

    def last_successful_transfer_at(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        incident_id: UUID | None = None,
    ) -> datetime | None:
        self._ensure_memory_mode()
        transfers = [
            item.last_successful_transfer_at
            for item in self._queue_items.values()
            if item.tenant_id == tenant_id
            and item.site_id == site_id
            and (incident_id is None or item.incident_id == incident_id)
            and item.last_successful_transfer_at is not None
        ]
        if not transfers:
            return None
        return max(transfers)

    async def alast_successful_transfer_at(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        incident_id: UUID | None = None,
    ) -> datetime | None:
        if self.session_factory is None:
            return self.last_successful_transfer_at(
                tenant_id=tenant_id,
                site_id=site_id,
                incident_id=incident_id,
            )
        queue = await self.alist_queue(
            tenant_id=tenant_id,
            site_id=site_id,
            incident_id=incident_id,
        )
        transfers = [
            item.last_successful_transfer_at
            for item in queue
            if item.last_successful_transfer_at is not None
        ]
        if not transfers:
            return None
        return max(transfers)

    def derive_link_state(self, probe: LinkHealthProbeRecord | None) -> LinkState:
        if probe is None:
            return "unknown"
        if not probe.reachable:
            return "dark"
        if (
            probe.latency_ms >= 500
            or probe.packet_loss_percent >= 0.5
            or (
                _probe_throughput_measured(probe)
                and probe.throughput_mbps < 10.0
            )
        ):
            return "degraded"
        return "healthy"

    def hash_passport_payload(self, payload: Mapping[str, object]) -> str:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    async def _find_budget_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> LinkBudget | None:
        result = await session.execute(
            select(LinkBudget)
            .where(LinkBudget.tenant_id == tenant_id, LinkBudget.site_id == site_id)
            .limit(1)
        )
        return result.scalars().first()

    async def _list_probe_rows(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> list[LinkHealthProbe]:
        result = await session.execute(
            select(LinkHealthProbe)
            .where(
                LinkHealthProbe.tenant_id == tenant_id,
                LinkHealthProbe.site_id == site_id,
                LinkHealthProbe.deleted_at.is_(None),
            )
            .order_by(LinkHealthProbe.recorded_at.desc())
        )
        return cast(list[LinkHealthProbe], result.scalars().all())

    async def _list_queue_rows(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> list[LinkQueueItem]:
        statement = select(LinkQueueItem)
        if tenant_id is None and site_id is None and incident_id is None:
            raise ValueError("Session-backed queue listing requires at least one scope.")
        if tenant_id is not None:
            statement = statement.where(LinkQueueItem.tenant_id == tenant_id)
        if site_id is not None:
            statement = statement.where(LinkQueueItem.site_id == site_id)
        if incident_id is not None:
            statement = statement.where(LinkQueueItem.incident_id == incident_id)
        result = await session.execute(statement.order_by(LinkQueueItem.created_at))
        return cast(list[LinkQueueItem], result.scalars().all())

    async def _find_passport_row_by_hash(
        self,
        session: AsyncSession,
        passport_hash: str,
    ) -> LinkPassportSnapshot | None:
        result = await session.execute(
            select(LinkPassportSnapshot)
            .where(LinkPassportSnapshot.passport_hash == passport_hash)
            .limit(1)
        )
        return result.scalars().first()

    async def _update_queue_status(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
        status: str,
        pause_reason: str | None,
    ) -> LinkQueueItemRecord | None:
        _validate_queue_status(status)
        if self.session_factory is None:
            return None
        async with self.session_factory() as session:
            queue_item = await session.get(LinkQueueItem, queue_item_id)
            if queue_item is None or queue_item.tenant_id != tenant_id:
                return None
            now = _now()
            queue_item.status = status
            queue_item.pause_reason = pause_reason
            queue_item.paused_at = now if status == "paused" else None
            queue_item.updated_at = now
            await session.commit()
            await session.refresh(queue_item)
            return _queue_item_record(queue_item)

    def _ensure_memory_mode(self) -> None:
        if self.session_factory is not None:
            raise RuntimeError("Use async LinkService methods when session_factory is configured.")


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _validate_priority_lane(priority_lane: str) -> None:
    if priority_lane not in LINK_PRIORITY_ORDER:
        raise ValueError(f"Invalid link priority lane: {priority_lane}")


def _validate_link_state(link_state: str) -> None:
    if link_state not in LINK_STATES:
        raise ValueError(f"Invalid link state: {link_state}")


def _validate_connection_values(
    *,
    label: str,
    transport_kind: str,
    status: str,
    priority_rank: int,
    availability_scope: str,
) -> None:
    if not label.strip():
        raise ValueError("Connection label is required.")
    if transport_kind not in LINK_TRANSPORT_KINDS:
        raise ValueError(f"Invalid link transport kind: {transport_kind}")
    if status not in LINK_CONNECTION_STATUSES:
        raise ValueError(f"Invalid link connection status: {status}")
    if availability_scope not in LINK_AVAILABILITY_SCOPES:
        raise ValueError(f"Invalid link availability scope: {availability_scope}")
    if priority_rank < 0:
        raise ValueError("Connection priority rank must be non-negative.")


def _validate_queue_status(status: str) -> None:
    if status not in QUEUE_STATUSES:
        raise ValueError(f"Invalid queue status: {status}")


def _validate_transfer_attempt_status(status: str) -> None:
    if status not in TRANSFER_ATTEMPT_STATUSES:
        raise ValueError(f"Invalid transfer status: {status}")


def _default_policy() -> JsonObject:
    return {
        "priority_order": list(LINK_PRIORITY_ORDER),
        "backpressure": {
            "degraded_pauses": ["telemetry", "bulk"],
            "dark_allows": ["safety"],
            "pause_bulk_when_daily_budget_exhausted": True,
            "avoid_metered_for_bulk_when_budget_exhausted": True,
        },
    }


def _validate_policy(policy: JsonObject) -> JsonObject:
    validated = dict(policy)
    priority_order = validated.get("priority_order")
    if priority_order is not None:
        _validate_policy_lanes(priority_order)

    backpressure = validated.get("backpressure")
    if isinstance(backpressure, Mapping):
        backpressure_copy = dict(backpressure)
        degraded_pauses = backpressure_copy.get("degraded_pauses")
        if degraded_pauses is not None:
            _validate_policy_lanes(degraded_pauses)
        dark_allows = backpressure_copy.get("dark_allows")
        if dark_allows is not None:
            _validate_policy_lanes(dark_allows)
        validated["backpressure"] = backpressure_copy

    return validated


def _validate_policy_lanes(value: object) -> None:
    if not isinstance(value, list):
        raise ValueError("Invalid link policy lanes.")
    for lane in value:
        if lane not in LINK_PRIORITY_ORDER:
            raise ValueError(f"Invalid link policy lane: {lane}")


def _budget_record(budget: LinkBudget) -> LinkBudgetSnapshot:
    return LinkBudgetSnapshot(
        id=budget.id,
        tenant_id=budget.tenant_id,
        site_id=budget.site_id,
        monthly_bytes=budget.monthly_bytes,
        bulk_daily_bytes=budget.bulk_daily_bytes,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _connection_record(connection: LinkConnection) -> LinkConnectionRecord:
    return LinkConnectionRecord(
        id=connection.id,
        tenant_id=connection.tenant_id,
        site_id=connection.site_id,
        label=connection.label,
        transport_kind=cast(LinkTransportKind, connection.transport_kind),
        provider=connection.provider,
        status=cast(LinkConnectionStatus, connection.status),
        priority_rank=connection.priority_rank,
        availability_scope=cast(LinkAvailabilityScope, connection.availability_scope),
        metered=connection.metered,
        monthly_bytes=connection.monthly_bytes,
        bulk_daily_bytes=connection.bulk_daily_bytes,
        expected_downlink_mbps=connection.expected_downlink_mbps,
        expected_uplink_mbps=connection.expected_uplink_mbps,
        expected_latency_ms=connection.expected_latency_ms,
        packet_loss_percent=connection.packet_loss_percent,
        last_seen_at=connection.last_seen_at,
        metadata=dict(connection.connection_metadata or {}),
        created_at=connection.created_at,
        updated_at=connection.updated_at,
    )


def _metadata_targets(metadata: Mapping[str, object]) -> list[JsonObject]:
    targets = metadata.get("monitoring_targets")
    if not isinstance(targets, list):
        return []
    return [dict(target) for target in targets if isinstance(target, Mapping)]


def _queue_item_record(item: LinkQueueItem) -> LinkQueueItemRecord:
    return LinkQueueItemRecord(
        id=item.id,
        tenant_id=item.tenant_id,
        site_id=item.site_id,
        camera_id=item.camera_id,
        incident_id=item.incident_id,
        evidence_artifact_id=item.evidence_artifact_id,
        priority_lane=cast(LinkPriorityLane, item.priority_lane),
        byte_size=item.byte_size,
        source_object_type=item.source_object_type,
        source_object_id=item.source_object_id,
        status=item.status,
        pause_reason=item.pause_reason,
        paused_at=item.paused_at,
        last_successful_transfer_at=item.last_successful_transfer_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _attempt_record(attempt: LinkTransferAttempt) -> LinkTransferAttemptRecord:
    return LinkTransferAttemptRecord(
        id=attempt.id,
        queue_item_id=attempt.queue_item_id,
        status=attempt.status,
        bytes_transferred=attempt.bytes_transferred,
        resume_token=attempt.resume_token,
        interruption_reason=attempt.interruption_reason,
        created_at=attempt.created_at,
    )


def _probe_record(probe: LinkHealthProbe) -> LinkHealthProbeRecord:
    return LinkHealthProbeRecord(
        id=probe.id,
        tenant_id=probe.tenant_id,
        site_id=probe.site_id,
        connection_id=probe.connection_id,
        latency_ms=probe.latency_ms,
        throughput_mbps=probe.throughput_mbps,
        packet_loss_percent=probe.packet_loss_percent,
        reachable=probe.reachable,
        source=probe.source,
        recorded_at=probe.recorded_at,
        target_id=probe.target_id,
        target_label=probe.target_label,
        target_address=probe.target_address,
        probe_type=cast(LinkProbeType | None, probe.probe_type),
        source_type=cast(LinkProbeSourceType, probe.source_type),
        source_label=probe.source_label,
        sample_kind=cast(LinkProbeSampleKind, probe.sample_kind),
        deleted_at=probe.deleted_at,
        measurement_metadata=dict(probe.measurement_metadata or {}),
    )


def _passport_record(passport: LinkPassportSnapshot) -> LinkPassportSnapshotRecord:
    return LinkPassportSnapshotRecord(
        id=passport.id,
        tenant_id=passport.tenant_id,
        site_id=passport.site_id,
        camera_id=passport.camera_id,
        incident_id=passport.incident_id,
        evidence_artifact_id=passport.evidence_artifact_id,
        pack_id=passport.pack_id,
        link_state=cast(LinkState, passport.link_state),
        passport_hash=passport.passport_hash,
        payload=dict(passport.passport),
        created_at=passport.created_at,
        last_sync_at=passport.last_sync_at,
    )


def _budget_payload(budget: LinkBudgetSnapshot | None) -> JsonObject | None:
    if budget is None:
        return None
    return {
        "monthly_bytes": budget.monthly_bytes,
        "bulk_daily_bytes": budget.bulk_daily_bytes,
        "updated_at": budget.updated_at.isoformat(),
    }


def _connection_payload(connection: LinkConnectionRecord) -> JsonObject:
    return {
        "id": str(connection.id),
        "tenant_id": str(connection.tenant_id),
        "site_id": str(connection.site_id),
        "label": connection.label,
        "transport_kind": connection.transport_kind,
        "provider": connection.provider,
        "status": connection.status,
        "priority_rank": connection.priority_rank,
        "availability_scope": connection.availability_scope,
        "metered": connection.metered,
        "monthly_bytes": connection.monthly_bytes,
        "bulk_daily_bytes": connection.bulk_daily_bytes,
        "expected_downlink_mbps": connection.expected_downlink_mbps,
        "expected_uplink_mbps": connection.expected_uplink_mbps,
        "expected_latency_ms": connection.expected_latency_ms,
        "packet_loss_percent": connection.packet_loss_percent,
        "last_seen_at": connection.last_seen_at.isoformat()
        if connection.last_seen_at is not None
        else None,
        "metadata": connection.metadata,
        "created_at": connection.created_at.isoformat(),
        "updated_at": connection.updated_at.isoformat(),
    }


def _probe_payload(probe: LinkHealthProbeRecord | None) -> JsonObject | None:
    if probe is None:
        return None
    payload: JsonObject = {
        "latency_ms": probe.latency_ms,
        "throughput_mbps": probe.throughput_mbps,
        "packet_loss_percent": probe.packet_loss_percent,
        "reachable": probe.reachable,
        "source": probe.source,
        "recorded_at": probe.recorded_at.isoformat(),
        "target_id": probe.target_id,
        "target_label": probe.target_label,
        "target_address": probe.target_address,
        "probe_type": probe.probe_type,
        "source_type": probe.source_type,
        "source_label": probe.source_label,
        "sample_kind": probe.sample_kind,
        "deleted_at": probe.deleted_at.isoformat() if probe.deleted_at is not None else None,
        "measurement_metadata": probe.measurement_metadata,
    }
    if probe.connection_id is not None:
        payload["connection_id"] = str(probe.connection_id)
    return payload


def _probe_throughput_measured(probe: LinkHealthProbeRecord) -> bool:
    if probe.throughput_mbps > 0:
        return True
    return probe.source_type != "backend_synthetic"


def _sort_connections(
    connections: Sequence[LinkConnectionRecord],
) -> list[LinkConnectionRecord]:
    return sorted(
        connections,
        key=lambda connection: (
            connection.priority_rank,
            LINK_CONNECTION_STATUS_ORDER[connection.status],
            connection.created_at,
            str(connection.id),
        ),
    )


def _select_connection(
    connections: Sequence[LinkConnectionRecord],
    *,
    priority_lane: LinkPriorityLane,
    remaining_budget_bytes: int,
) -> LinkConnectionRecord | None:
    _validate_priority_lane(priority_lane)
    usable = [
        connection
        for connection in connections
        if connection.status in LINK_USABLE_CONNECTION_STATUSES
    ]
    if not usable:
        return None
    return min(
        usable,
        key=lambda connection: (
            LINK_CONNECTION_STATUS_ORDER[connection.status],
            priority_lane == "bulk" and connection.metered and remaining_budget_bytes <= 0,
            connection.priority_rank,
            connection.created_at,
            str(connection.id),
        ),
    )
