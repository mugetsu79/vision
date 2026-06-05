from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.link.contracts import (
    LINK_PRIORITY_ORDER,
    BackpressureDecision,
    JsonObject,
    LinkBudgetSnapshot,
    LinkHealthProbeRecord,
    LinkPassportSnapshotRecord,
    LinkPriorityLane,
    LinkQueueItemRecord,
    LinkState,
    LinkTransferAttemptRecord,
)
from argus.link.tables import (
    LinkBudget,
    LinkHealthProbe,
    LinkPassportSnapshot,
    LinkQueueItem,
    LinkTransferAttempt,
)


class LinkService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession] | None = None) -> None:
        self.session_factory = session_factory
        self._budgets: dict[tuple[UUID, UUID], LinkBudgetSnapshot] = {}
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
        latency_ms: int,
        throughput_mbps: float,
        packet_loss_percent: float,
        reachable: bool,
        source: str,
    ) -> LinkHealthProbeRecord:
        probe = LinkHealthProbeRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            latency_ms=latency_ms,
            throughput_mbps=throughput_mbps,
            packet_loss_percent=packet_loss_percent,
            reachable=reachable,
            source=source,
            recorded_at=_now(),
        )
        self._probes.append(probe)
        return probe

    async def arecord_probe(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        latency_ms: int,
        throughput_mbps: float,
        packet_loss_percent: float,
        reachable: bool,
        source: str,
    ) -> LinkHealthProbeRecord:
        if self.session_factory is None:
            return self.record_probe(
                tenant_id=tenant_id,
                site_id=site_id,
                latency_ms=latency_ms,
                throughput_mbps=throughput_mbps,
                packet_loss_percent=packet_loss_percent,
                reachable=reachable,
                source=source,
            )
        probe = LinkHealthProbe(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            latency_ms=latency_ms,
            throughput_mbps=throughput_mbps,
            packet_loss_percent=packet_loss_percent,
            reachable=reachable,
            source=source,
            recorded_at=_now(),
        )
        async with self.session_factory() as session:
            session.add(probe)
            await session.commit()
            await session.refresh(probe)
        return _probe_record(probe)

    def list_probes(self, *, tenant_id: UUID, site_id: UUID) -> list[LinkHealthProbeRecord]:
        return [
            probe
            for probe in self._probes
            if probe.tenant_id == tenant_id and probe.site_id == site_id
        ]

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
        return self._policies.get(
            (tenant_id, site_id),
            {
                "priority_order": list(LINK_PRIORITY_ORDER),
                "backpressure": {
                    "degraded_pauses": ["telemetry", "bulk"],
                    "dark_allows": ["safety"],
                },
            },
        )

    def put_policy(self, *, tenant_id: UUID, site_id: UUID, policy: JsonObject) -> JsonObject:
        self._policies[(tenant_id, site_id)] = policy
        return policy

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
            now = _now()
            if budget is None:
                budget = LinkBudget(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    site_id=site_id,
                    monthly_bytes=0,
                    bulk_daily_bytes=0,
                    policy=policy,
                    created_at=now,
                    updated_at=now,
                )
                session.add(budget)
            else:
                budget.policy = policy
                budget.updated_at = now
            await session.commit()
        return policy

    def list_queue(
        self,
        *,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> list[LinkQueueItemRecord]:
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
        budget = self.get_budget(tenant_id=tenant_id, site_id=site_id)
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
            session.add(passport)
            await session.commit()
            await session.refresh(passport)
        return _passport_record(passport)

    def build_incident_passport(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
    ) -> LinkPassportSnapshotRecord | None:
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
            lane: sum(1 for item in items if item.priority_lane == lane)
            for lane in LINK_PRIORITY_ORDER
        }

    def last_successful_transfer_at(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        incident_id: UUID | None = None,
    ) -> datetime | None:
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
            return "healthy"
        if not probe.reachable:
            return "dark"
        if (
            probe.latency_ms >= 500
            or probe.packet_loss_percent >= 0.5
            or probe.throughput_mbps < 10.0
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
        result = await session.execute(select(LinkBudget))
        budgets = cast(list[LinkBudget], result.scalars().all())
        return next(
            (
                budget
                for budget in budgets
                if budget.tenant_id == tenant_id and budget.site_id == site_id
            ),
            None,
        )

    async def _list_probe_rows(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> list[LinkHealthProbe]:
        result = await session.execute(select(LinkHealthProbe))
        probes = cast(list[LinkHealthProbe], result.scalars().all())
        return [
            probe
            for probe in probes
            if probe.tenant_id == tenant_id and probe.site_id == site_id
        ]

    async def _list_queue_rows(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID | None = None,
        site_id: UUID | None = None,
        incident_id: UUID | None = None,
    ) -> list[LinkQueueItem]:
        result = await session.execute(select(LinkQueueItem))
        queue_items = cast(list[LinkQueueItem], result.scalars().all())
        if tenant_id is not None:
            queue_items = [item for item in queue_items if item.tenant_id == tenant_id]
        if site_id is not None:
            queue_items = [item for item in queue_items if item.site_id == site_id]
        if incident_id is not None:
            queue_items = [item for item in queue_items if item.incident_id == incident_id]
        return queue_items

    async def _update_queue_status(
        self,
        *,
        tenant_id: UUID,
        queue_item_id: UUID,
        status: str,
        pause_reason: str | None,
    ) -> LinkQueueItemRecord | None:
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


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _default_policy() -> JsonObject:
    return {
        "priority_order": list(LINK_PRIORITY_ORDER),
        "backpressure": {
            "degraded_pauses": ["telemetry", "bulk"],
            "dark_allows": ["safety"],
        },
    }


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
        latency_ms=probe.latency_ms,
        throughput_mbps=probe.throughput_mbps,
        packet_loss_percent=probe.packet_loss_percent,
        reachable=probe.reachable,
        source=probe.source,
        recorded_at=probe.recorded_at,
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


def _probe_payload(probe: LinkHealthProbeRecord | None) -> JsonObject | None:
    if probe is None:
        return None
    return {
        "latency_ms": probe.latency_ms,
        "throughput_mbps": probe.throughput_mbps,
        "packet_loss_percent": probe.packet_loss_percent,
        "reachable": probe.reachable,
        "source": probe.source,
        "recorded_at": probe.recorded_at.isoformat(),
    }
