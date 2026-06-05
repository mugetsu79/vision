from __future__ import annotations

from uuid import UUID

import pytest

from argus.link.service import LinkService


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
