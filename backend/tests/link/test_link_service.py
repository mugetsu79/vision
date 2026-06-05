from __future__ import annotations

from uuid import UUID

import pytest

from argus.link.service import LinkService
from argus.link.tables import (
    LinkBudget,
    LinkHealthProbe,
    LinkPassportSnapshot,
    LinkQueueItem,
    LinkTransferAttempt,
)


@pytest.fixture
def link_service() -> LinkService:
    return LinkService()


def test_packless_site_budget_queue_and_passport_flow(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")

    budget = link_service.upsert_budget(
        tenant_id=tenant_id,
        site_id=site_id,
        monthly_bytes=50_000_000_000,
        bulk_daily_bytes=5_000_000_000,
    )
    link_service.record_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=620,
        throughput_mbps=8.5,
        packet_loss_percent=0.8,
        reachable=True,
        source="packless-lab",
    )
    item = link_service.enqueue_transfer(
        tenant_id=tenant_id,
        site_id=site_id,
        priority_lane="evidence",
        byte_size=2048,
        source_object_type="evidence_artifact",
        source_object_id=UUID("00000000-0000-4000-8000-000000000003"),
    )
    passport = link_service.build_passport(tenant_id=tenant_id, site_id=site_id)

    assert budget.site_id == site_id
    assert item.priority_lane == "evidence"
    assert passport.site_id == site_id
    assert passport.pack_id is None
    assert passport.link_state in {"healthy", "degraded", "recovering", "port_wifi"}


def test_link_passport_carries_core_optional_identifiers(link_service: LinkService) -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")
    camera_id = UUID("00000000-0000-4000-8000-000000000003")
    incident_id = UUID("00000000-0000-4000-8000-000000000004")
    evidence_artifact_id = UUID("00000000-0000-4000-8000-000000000005")

    passport = link_service.build_passport(
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        incident_id=incident_id,
        evidence_artifact_id=evidence_artifact_id,
    )

    assert passport.camera_id == camera_id
    assert passport.incident_id == incident_id
    assert passport.evidence_artifact_id == evidence_artifact_id
    assert passport.payload["camera_id"] == str(camera_id)
    assert passport.payload["incident_id"] == str(incident_id)
    assert passport.payload["evidence_artifact_id"] == str(evidence_artifact_id)


@pytest.mark.asyncio
async def test_session_backed_link_service_persists_core_state() -> None:
    tenant_id = UUID("00000000-0000-4000-8000-000000000001")
    site_id = UUID("00000000-0000-4000-8000-000000000002")
    camera_id = UUID("00000000-0000-4000-8000-000000000003")
    incident_id = UUID("00000000-0000-4000-8000-000000000004")
    evidence_artifact_id = UUID("00000000-0000-4000-8000-000000000005")
    source_object_id = UUID("00000000-0000-4000-8000-000000000006")
    session_factory = _PersistentLinkSessionFactory()
    service = LinkService(session_factory)

    budget = await service.aupsert_budget(
        tenant_id=tenant_id,
        site_id=site_id,
        monthly_bytes=50_000_000_000,
        bulk_daily_bytes=5_000_000_000,
    )
    await service.arecord_probe(
        tenant_id=tenant_id,
        site_id=site_id,
        latency_ms=120,
        throughput_mbps=42.0,
        packet_loss_percent=0.1,
        reachable=True,
        source="packless-lab",
    )
    item = await service.aenqueue_transfer(
        tenant_id=tenant_id,
        site_id=site_id,
        priority_lane="evidence",
        byte_size=4096,
        source_object_type="evidence_artifact",
        source_object_id=source_object_id,
        camera_id=camera_id,
        incident_id=incident_id,
        evidence_artifact_id=evidence_artifact_id,
    )
    await service.arecord_transfer_attempt(
        queue_item_id=item.id,
        status="succeeded",
        bytes_transferred=4096,
        resume_token="object-part-1",
    )
    first_passport = await service.abuild_passport(
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        incident_id=incident_id,
        evidence_artifact_id=evidence_artifact_id,
    )

    restored = LinkService(session_factory)
    restored_budget = await restored.aget_budget(tenant_id=tenant_id, site_id=site_id)
    restored_queue = await restored.alist_queue(tenant_id=tenant_id, site_id=site_id)
    restored_probes = await restored.alist_probes(tenant_id=tenant_id, site_id=site_id)
    restored_passport = await restored.abuild_passport(
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        incident_id=incident_id,
        evidence_artifact_id=evidence_artifact_id,
    )
    duplicate_passport = await restored.abuild_passport(
        tenant_id=tenant_id,
        site_id=site_id,
        camera_id=camera_id,
        incident_id=incident_id,
        evidence_artifact_id=evidence_artifact_id,
    )

    assert restored_budget is not None
    assert restored_budget.id == budget.id
    assert restored_queue[0].id == item.id
    assert restored_queue[0].last_successful_transfer_at is not None
    assert restored_probes[0].source == "packless-lab"
    assert restored_passport.payload["budget"] is not None
    assert restored_passport.payload["latest_probe"] is not None
    assert restored_passport.last_sync_at is not None
    assert first_passport.passport_hash == restored_passport.passport_hash
    assert duplicate_passport.id == first_passport.id
    assert len(session_factory.rows[LinkPassportSnapshot]) == 1


def test_priority_order_is_safety_evidence_telemetry_bulk(link_service: LinkService) -> None:
    items = [
        link_service.make_queue_item_for_test(priority_lane="bulk", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="telemetry", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="safety", byte_size=100),
        link_service.make_queue_item_for_test(priority_lane="evidence", byte_size=100),
    ]
    assert [item.priority_lane for item in link_service.sort_queue(items)] == [
        "safety",
        "evidence",
        "telemetry",
        "bulk",
    ]


def test_degraded_budget_backpressures_lower_priority_lanes(link_service: LinkService) -> None:
    decision = link_service.apply_backpressure(
        link_state="degraded",
        remaining_daily_bulk_bytes=0,
        queue_depth_by_lane={"safety": 1, "evidence": 3, "telemetry": 10, "bulk": 20},
    )
    assert decision.paused_lanes == {"telemetry", "bulk"}
    assert decision.allowed_lanes == {"safety", "evidence"}
    assert decision.reason == "degraded_link_or_budget_exhausted"


def test_resume_records_offsets_and_last_successful_transfer(link_service: LinkService) -> None:
    queue_item = link_service.make_queue_item_for_test(priority_lane="evidence", byte_size=4096)
    attempt = link_service.record_transfer_attempt(
        queue_item_id=queue_item.id,
        status="interrupted",
        bytes_transferred=2048,
        resume_token="object-part-2",
        interruption_reason="link_dark",
    )
    resumed = link_service.record_transfer_attempt(
        queue_item_id=queue_item.id,
        status="succeeded",
        bytes_transferred=4096,
        resume_token=attempt.resume_token,
    )
    assert resumed.bytes_transferred == 4096
    assert resumed.resume_token == "object-part-2"
    assert link_service.get_queue_item(queue_item.id).last_successful_transfer_at is not None


def test_link_passport_hash_is_stable_for_canonical_payload(link_service: LinkService) -> None:
    first = link_service.hash_passport_payload({"b": 2, "a": {"z": 1, "y": 2}})
    second = link_service.hash_passport_payload({"a": {"y": 2, "z": 1}, "b": 2})
    assert first == second


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows

    def first(self) -> object | None:
        return self.rows[0] if self.rows else None


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self.rows)

    def scalar_one_or_none(self) -> object | None:
        return self.rows[0] if self.rows else None


class _PersistentLinkSession:
    def __init__(self, rows: dict[type[object], list[object]]) -> None:
        self.rows = rows

    async def __aenter__(self) -> _PersistentLinkSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: object) -> None:
        self.rows.setdefault(type(row), []).append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None

    async def get(self, model_cls: type[object], object_id: object) -> object | None:
        return next(
            (row for row in self.rows.get(model_cls, []) if getattr(row, "id", None) == object_id),
            None,
        )

    async def execute(self, statement: object) -> _Result:
        entity = statement.column_descriptions[0]["entity"]
        rows = list(self.rows.get(entity, []))
        return _Result(rows)


class _PersistentLinkSessionFactory:
    def __init__(self) -> None:
        self.rows: dict[type[object], list[object]] = {
            LinkBudget: [],
            LinkHealthProbe: [],
            LinkQueueItem: [],
            LinkTransferAttempt: [],
            LinkPassportSnapshot: [],
        }

    def __call__(self) -> _PersistentLinkSession:
        return _PersistentLinkSession(self.rows)
