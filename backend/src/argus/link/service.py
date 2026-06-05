from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID, uuid4

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

    def list_probes(self, *, tenant_id: UUID, site_id: UUID) -> list[LinkHealthProbeRecord]:
        return [
            probe
            for probe in self._probes
            if probe.tenant_id == tenant_id and probe.site_id == site_id
        ]

    def latest_probe(self, *, tenant_id: UUID, site_id: UUID) -> LinkHealthProbeRecord | None:
        probes = self.list_probes(tenant_id=tenant_id, site_id=site_id)
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

    def get_queue_item(self, queue_item_id: UUID) -> LinkQueueItemRecord:
        try:
            return self._queue_items[queue_item_id]
        except KeyError as exc:
            raise ValueError("Queue item not found.") from exc

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

    def build_passport(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        incident_id: UUID | None = None,
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
            "incident_id": str(incident_id) if incident_id is not None else None,
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
            pack_id=None,
            link_state=link_state,
            passport_hash=self.hash_passport_payload(payload),
            payload=payload,
            created_at=_now(),
            last_sync_at=last_sync_at,
        )
        self._passports.append(passport)
        return passport

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
            incident_id=incident_id,
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


def _now() -> datetime:
    return datetime.now(tz=UTC)


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
