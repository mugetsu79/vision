from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4, uuid5

import pytest
from nats.js import api as js_api

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.events import EventMessage
from argus.core.security import AuthenticatedUser
from argus.inference.publisher import TelemetryFrame, TelemetryTrack, WorkerOrigin
from argus.models.enums import RoleEnum
from argus.models.tables import TrackingFrame
from argus.services import app as app_services
from argus.services.app import NatsTelemetryService
from argus.streaming.mediamtx import PublishProfile, StreamMode


class _FakeSubscription:
    def __init__(self) -> None:
        self.unsubscribed = False

    async def unsubscribe(self) -> None:
        self.unsubscribed = True
        return None


class _FakeEventClient:
    def __init__(self) -> None:
        self.subscribe_calls: list[dict[str, Any]] = []
        self.published: list[tuple[str, Any]] = []

    async def subscribe(self, subject: str, handler: Any, **kwargs: Any) -> _FakeSubscription:
        self.subscribe_calls.append(
            {
                "subject": subject,
                "handler": handler,
                "kwargs": kwargs,
            }
        )
        return _FakeSubscription()

    async def publish(self, subject: str, payload: Any) -> None:
        self.published.append((subject, payload))


class _FailingPublishEventClient(_FakeEventClient):
    async def publish(self, subject: str, payload: Any) -> None:
        await super().publish(subject, payload)
        raise RuntimeError("publish failed")


class _FailingSecondSubscribeEventClient(_FakeEventClient):
    def __init__(self) -> None:
        super().__init__()
        self.first_subscription = _FakeSubscription()

    async def subscribe(self, subject: str, handler: Any, **kwargs: Any) -> _FakeSubscription:
        await super().subscribe(subject, handler, **kwargs)
        if len(self.subscribe_calls) == 1:
            return self.first_subscription
        raise RuntimeError("boom")


class _PersistExecuteResult:
    def __init__(
        self,
        *,
        scalar_one_or_none: Any = None,
        scalars: list[Any] | None = None,
    ) -> None:
        self._scalar_one_or_none = scalar_one_or_none
        self._scalars = scalars or []

    def scalar_one_or_none(self) -> Any:
        return self._scalar_one_or_none

    def scalars(self) -> _PersistExecuteResult:
        return self

    def all(self) -> list[Any]:
        return self._scalars


class _PersistSession:
    def __init__(
        self,
        execute_results: list[_PersistExecuteResult],
        *,
        scalar_result: Any = None,
    ) -> None:
        self._execute_results = execute_results
        self.scalar_result = scalar_result
        self.execute_statements: list[Any] = []
        self.scalar_statements: list[Any] = []
        self.commits = 0

    async def __aenter__(self) -> _PersistSession:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def execute(self, statement: Any) -> _PersistExecuteResult:
        self.execute_statements.append(statement)
        return self._execute_results.pop(0)

    async def scalar(self, statement: Any) -> Any:
        self.scalar_statements.append(statement)
        return self.scalar_result

    async def commit(self) -> None:
        self.commits += 1


def _tenant_context() -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


async def _expect_no_frame(subscription: Any) -> None:
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(subscription.receive(), timeout=0.01)


@pytest.mark.asyncio
async def test_telemetry_subscription_only_receives_new_frames() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    allowed_camera_id = uuid4()

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {allowed_camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]
    tenant_context = TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )

    subscription = await service.subscribe(tenant_context)

    assert event_client.subscribe_calls[0]["subject"] == "evt.tracking.*"
    assert (
        event_client.subscribe_calls[0]["kwargs"]["deliver_policy"]
        is js_api.DeliverPolicy.NEW
    )

    await subscription.close()


@pytest.mark.asyncio
async def test_telemetry_subscribers_share_one_nats_subscription() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    allowed_camera_id = uuid4()

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {allowed_camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]

    first = await service.subscribe(_tenant_context())
    second = await service.subscribe(_tenant_context())

    assert len(event_client.subscribe_calls) == 1
    assert event_client.subscribe_calls[0]["subject"] == "evt.tracking.*"
    assert (
        event_client.subscribe_calls[0]["kwargs"]["deliver_policy"]
        is js_api.DeliverPolicy.NEW
    )

    await first.close()
    await second.close()


@pytest.mark.asyncio
async def test_telemetry_shared_handler_parses_once_and_fans_out_to_allowed_subscribers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {frame.camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]
    original_model_validate_json = TelemetryFrame.model_validate_json
    parse_count = 0

    def count_model_validate_json(cls: type[TelemetryFrame], data: str) -> TelemetryFrame:
        nonlocal parse_count
        parse_count += 1
        return original_model_validate_json(data)

    monkeypatch.setattr(
        TelemetryFrame,
        "model_validate_json",
        classmethod(count_model_validate_json),
    )

    first = await service.subscribe(_tenant_context())
    second = await service.subscribe(_tenant_context())
    handler = event_client.subscribe_calls[0]["handler"]

    await handler(
        EventMessage(
            subject=f"evt.tracking.{frame.camera_id}",
            data=frame.model_dump_json(),
            headers={},
        )
    )

    assert await asyncio.wait_for(first.receive(), timeout=0.1) == frame
    assert await asyncio.wait_for(second.receive(), timeout=0.1) == frame
    assert parse_count == 1

    await first.close()
    await second.close()


@pytest.mark.asyncio
async def test_telemetry_fanout_filters_frames_per_subscriber_camera_scope() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    first_tenant = _tenant_context()
    second_tenant = _tenant_context()
    first_frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    second_frame = first_frame.model_copy(
        update={"camera_id": uuid4(), "frame_id": uuid4()}
    )
    allowed_by_tenant = {
        first_tenant.tenant_id: {first_frame.camera_id},
        second_tenant.tenant_id: {second_frame.camera_id},
    }

    async def camera_ids_for_tenant(tenant_context: TenantContext) -> set[Any]:
        return allowed_by_tenant[tenant_context.tenant_id]

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]

    first = await service.subscribe(first_tenant)
    second = await service.subscribe(second_tenant)

    await service.publish_live_for_test(first_frame)

    assert await asyncio.wait_for(first.receive(), timeout=0.1) == first_frame
    await _expect_no_frame(second)

    await service.publish_live_for_test(second_frame)

    assert await asyncio.wait_for(second.receive(), timeout=0.1) == second_frame
    await _expect_no_frame(first)

    await first.close()
    await second.close()


@pytest.mark.asyncio
async def test_telemetry_fanout_coalesces_slow_subscriber_to_latest_frame() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(
            _env_file=None,
            enable_startup_services=False,
            websocket_telemetry_buffer_size=1,
        ),
    )
    first_frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    latest_frame = first_frame.model_copy(update={"frame_id": uuid4(), "frame_sequence": 43})

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {first_frame.camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]
    subscription = await service.subscribe(_tenant_context())

    await service.publish_live_for_test(first_frame)
    await service.publish_live_for_test(latest_frame)

    assert await asyncio.wait_for(subscription.receive(), timeout=0.1) == latest_frame
    await _expect_no_frame(subscription)

    await subscription.close()


@pytest.mark.asyncio
async def test_telemetry_subscription_close_unregisters_from_shared_fanout() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {frame.camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]
    closed = await service.subscribe(_tenant_context())
    active = await service.subscribe(_tenant_context())

    await closed.close()
    await service.publish_live_for_test(frame)

    await _expect_no_frame(closed)
    assert await asyncio.wait_for(active.receive(), timeout=0.1) == frame

    await active.close()


@pytest.mark.asyncio
async def test_telemetry_fanout_reopens_after_all_subscribers_close() -> None:
    event_client = _FakeEventClient()
    service = NatsTelemetryService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)

    async def camera_ids_for_tenant(_tenant_context: TenantContext) -> set[Any]:
        return {frame.camera_id}

    service._camera_ids_for_tenant = camera_ids_for_tenant  # type: ignore[method-assign]

    first = await service.subscribe(_tenant_context())
    await first.close()
    second = await service.subscribe(_tenant_context())

    assert len(event_client.subscribe_calls) == 1

    await service.publish_live_for_test(frame)

    await _expect_no_frame(first)
    assert await asyncio.wait_for(second.receive(), timeout=0.1) == frame

    await second.close()


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_consumes_worker_nats_persists_then_broadcasts_once() -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    persisted: list[TelemetryFrame] = []
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        persisted.append(frame_to_persist)
        assert telemetry_transport == "worker_nats"
        return app_services.FramePersistResult(
            frames_inserted=1,
            tracks_inserted=len(frame_to_persist.tracks),
            accepted=True,
            needs_live_broadcast=True,
        )

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    await service.start()

    worker_call = next(
        call
        for call in event_client.subscribe_calls
        if call["subject"] == "evt.worker.tracking.*"
    )
    assert worker_call["kwargs"]["deliver_policy"] is js_api.DeliverPolicy.NEW
    assert worker_call["kwargs"]["durable"] == "argus-worker-telemetry-ingest"
    assert worker_call["kwargs"]["stream"] == "ARGUS_TRACKING"

    await worker_call["handler"](
        EventMessage(
            subject=f"evt.worker.tracking.{frame.camera_id}",
            data=frame.model_dump_json(),
            headers={},
        )
    )

    assert persisted == [frame]
    assert marked_broadcasted == [frame]
    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_keeps_frame_live_eligible_when_publish_fails(
) -> None:
    event_client = _FailingPublishEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        _frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        assert telemetry_transport == "edge_nats"
        return app_services.FramePersistResult(
            frames_inserted=1,
            tracks_inserted=1,
            accepted=True,
            needs_live_broadcast=True,
        )

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="publish failed"):
        await service.ingest_frame(frame, source="edge_nats")

    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]
    assert marked_broadcasted == []


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_redelivery_publishes_persisted_unbroadcasted_frame(
) -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        _frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        assert telemetry_transport == "edge_nats"
        return app_services.FramePersistResult(
            frames_inserted=0,
            tracks_inserted=0,
            accepted=False,
            needs_live_broadcast=True,
        )

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    result = await service.ingest_frame(frame, source="edge_nats")

    assert result == {
        "frames_inserted": 0,
        "tracks_inserted": 0,
        "broadcasted": 1,
        "duplicates": 0,
    }
    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]
    assert marked_broadcasted == [frame]


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_already_broadcasted_duplicate_skips_live_publish(
) -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        _frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        assert telemetry_transport == "http"
        return app_services.FramePersistResult(
            frames_inserted=0,
            tracks_inserted=0,
            accepted=False,
            needs_live_broadcast=False,
        )

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    result = await service.ingest_frame(frame, source="http")

    assert result == {
        "frames_inserted": 0,
        "tracks_inserted": 0,
        "broadcasted": 0,
        "duplicates": 1,
    }
    assert event_client.published == []
    assert marked_broadcasted == []


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_deduplicates_http_fallback_after_edge_nats() -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    insert_results = iter(
        [
            app_services.FramePersistResult(
                frames_inserted=1,
                tracks_inserted=1,
                accepted=True,
                needs_live_broadcast=True,
            ),
            app_services.FramePersistResult(
                frames_inserted=0,
                tracks_inserted=0,
                accepted=False,
                needs_live_broadcast=False,
            ),
        ]
    )
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        _frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        assert telemetry_transport in {"edge_nats", "http"}
        return next(insert_results)

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    first = await service.ingest_frame(frame, source="edge_nats")
    second = await service.ingest_frame(frame, source="http")

    assert first == {
        "frames_inserted": 1,
        "tracks_inserted": 1,
        "broadcasted": 1,
        "duplicates": 0,
    }
    assert second == {
        "frames_inserted": 0,
        "tracks_inserted": 0,
        "broadcasted": 0,
        "duplicates": 1,
    }
    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]
    assert marked_broadcasted == [frame]


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_deduplicates_worker_retry_by_frame_id() -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    insert_results = iter(
        [
            app_services.FramePersistResult(
                frames_inserted=1,
                tracks_inserted=1,
                accepted=True,
                needs_live_broadcast=True,
            ),
            app_services.FramePersistResult(
                frames_inserted=0,
                tracks_inserted=0,
                accepted=False,
                needs_live_broadcast=False,
            ),
        ]
    )
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        _frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        assert telemetry_transport == "worker_nats"
        return next(insert_results)

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    first = await service.ingest_frame(frame, source="worker_nats")
    second = await service.ingest_frame(frame, source="worker_nats")

    assert first == {
        "frames_inserted": 1,
        "tracks_inserted": 1,
        "broadcasted": 1,
        "duplicates": 0,
    }
    assert second == {
        "frames_inserted": 0,
        "tracks_inserted": 0,
        "broadcasted": 0,
        "duplicates": 1,
    }
    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]
    assert marked_broadcasted == [frame]


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_start_subscribes_to_edge_and_worker_subjects() -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    await service.start()

    assert [call["subject"] for call in event_client.subscribe_calls] == [
        "evt.edge.tracking.*",
        "evt.worker.tracking.*",
    ]
    assert event_client.subscribe_calls[0]["kwargs"]["durable"] == "argus-edge-telemetry-ingest"
    assert (
        event_client.subscribe_calls[1]["kwargs"]["durable"]
        == "argus-worker-telemetry-ingest"
    )
    assert all(
        call["kwargs"]["stream"] == "ARGUS_TRACKING" for call in event_client.subscribe_calls
    )
    assert all(
        call["kwargs"]["deliver_policy"] is js_api.DeliverPolicy.NEW
        for call in event_client.subscribe_calls
    )


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_drops_invalid_retained_edge_frame_then_continues() -> None:
    event_client = _FakeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    persisted: list[TelemetryFrame] = []
    marked_broadcasted: list[TelemetryFrame] = []

    async def persist_frame(
        frame_to_persist: TelemetryFrame,
        *,
        telemetry_transport: str,
    ) -> app_services.FramePersistResult:
        persisted.append(frame_to_persist)
        assert telemetry_transport == "edge_nats"
        return app_services.FramePersistResult(
            frames_inserted=1,
            tracks_inserted=len(frame_to_persist.tracks),
            accepted=True,
            needs_live_broadcast=True,
        )

    async def mark_frame_broadcasted(frame_to_mark: TelemetryFrame) -> None:
        marked_broadcasted.append(frame_to_mark)

    service._persist_frame = persist_frame  # type: ignore[method-assign]
    service._mark_frame_broadcasted = mark_frame_broadcasted  # type: ignore[method-assign]

    await service.start()
    edge_call = next(
        call
        for call in event_client.subscribe_calls
        if call["subject"] == "evt.edge.tracking.*"
    )

    await edge_call["handler"](
        EventMessage(
            subject=f"evt.edge.tracking.{frame.camera_id}",
            data=json.dumps(
                {
                    "camera_id": str(frame.camera_id),
                    "counts": {},
                    "tracks": [],
                }
            ),
            headers={},
        )
    )
    await edge_call["handler"](
        EventMessage(
            subject=f"evt.edge.tracking.{frame.camera_id}",
            data=frame.model_dump_json(),
            headers={},
        )
    )

    assert persisted == [frame]
    assert marked_broadcasted == [frame]
    assert event_client.published == [(f"evt.tracking.{frame.camera_id}", frame)]


@pytest.mark.asyncio
async def test_worker_telemetry_ingest_start_unsubscribes_first_subscription_when_second_fails(
) -> None:
    event_client = _FailingSecondSubscribeEventClient()
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: None,
        event_client=event_client,  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    with pytest.raises(RuntimeError, match="boom"):
        await service.start()

    assert event_client.first_subscription.unsubscribed is True
    assert service._started is False
    assert service._subscriptions == []


def test_tracking_event_rows_for_frame_include_canonical_compatibility_fields() -> None:
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)

    rows = app_services._tracking_event_rows_for_frame(frame, telemetry_transport="worker_nats")

    assert rows == [
        {
            "id": uuid5(
                app_services.TRACKING_EVENT_ROW_UUID_NAMESPACE,
                (
                    f"{frame.camera_id}:{frame.frame_id}:{frame.ts.isoformat()}:"
                    f"{frame.tracks[0].track_id}:{frame.tracks[0].source_track_id}:"
                    f"{frame.tracks[0].stable_track_id}"
                ),
            ),
            "ts": frame.ts,
            "camera_id": frame.camera_id,
            "class_name": "car",
            "track_id": 7,
            "confidence": 0.91,
            "speed_kph": 31.5,
            "direction_deg": 90.0,
            "zone_id": "lane-a",
            "attributes": {"color": "blue"},
            "bbox": {"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0},
            "frame_id": frame.frame_id,
            "frame_sequence": frame.frame_sequence,
            "stable_track_id": 70,
            "source_track_id": 700,
            "track_state": "active",
            "last_seen_age_ms": 85,
            "telemetry_transport": "worker_nats",
            "worker_origin": WorkerOrigin.CENTRAL.value,
        }
    ]


def test_tracking_event_rows_for_frame_use_distinct_ids_for_distinct_frame_ids() -> None:
    frame_one = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    frame_two = frame_one.model_copy(update={"frame_id": uuid4()})

    row_one = app_services._tracking_event_rows_for_frame(
        frame_one,
        telemetry_transport="worker_nats",
    )[0]
    row_two = app_services._tracking_event_rows_for_frame(
        frame_two,
        telemetry_transport="worker_nats",
    )[0]

    assert frame_one.camera_id == frame_two.camera_id
    assert frame_one.ts == frame_two.ts
    assert frame_one.tracks[0].track_id == frame_two.tracks[0].track_id
    assert row_one["id"] != row_two["id"]


def test_tracking_frame_rows_start_live_broadcast_marker_unset() -> None:
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)

    row = app_services._tracking_frame_row_for_frame(
        frame,
        telemetry_transport="worker_nats",
    )

    assert row["live_broadcast_at"] is None
    assert TrackingFrame.__table__.c.live_broadcast_at.nullable is True


@pytest.mark.asyncio
async def test_persist_frame_new_insert_needs_live_broadcast() -> None:
    frame = _telemetry_frame(worker_origin=WorkerOrigin.CENTRAL)
    session = _PersistSession(
        [
            _PersistExecuteResult(scalar_one_or_none=frame.frame_id),
            _PersistExecuteResult(scalars=[frame.tracks[0].track_id]),
        ]
    )
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: session,  # type: ignore[arg-type]
        event_client=_FakeEventClient(),  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    result = await service._persist_frame(frame, telemetry_transport="worker_nats")

    assert result == app_services.FramePersistResult(
        frames_inserted=1,
        tracks_inserted=1,
        accepted=True,
        needs_live_broadcast=True,
    )
    assert len(session.execute_statements) == 2
    assert session.scalar_statements == []
    assert session.commits == 1


@pytest.mark.asyncio
async def test_persist_frame_conflict_with_unbroadcasted_marker_needs_live_broadcast(
) -> None:
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    session = _PersistSession([_PersistExecuteResult(scalar_one_or_none=None)])
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: session,  # type: ignore[arg-type]
        event_client=_FakeEventClient(),  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    result = await service._persist_frame(frame, telemetry_transport="edge_nats")

    assert result == app_services.FramePersistResult(
        frames_inserted=0,
        tracks_inserted=0,
        accepted=False,
        needs_live_broadcast=True,
    )
    assert len(session.execute_statements) == 1
    assert len(session.scalar_statements) == 1
    assert session.commits == 0


@pytest.mark.asyncio
async def test_persist_frame_conflict_with_broadcasted_marker_does_not_need_live_broadcast(
) -> None:
    frame = _telemetry_frame(worker_origin=WorkerOrigin.EDGE)
    session = _PersistSession(
        [_PersistExecuteResult(scalar_one_or_none=None)],
        scalar_result=datetime(2026, 6, 12, 12, 1, 0, tzinfo=UTC),
    )
    service = app_services.WorkerTelemetryIngestService(
        session_factory=lambda: session,  # type: ignore[arg-type]
        event_client=_FakeEventClient(),  # type: ignore[arg-type]
        settings=Settings(_env_file=None, enable_startup_services=False),
    )

    result = await service._persist_frame(frame, telemetry_transport="edge_nats")

    assert result == app_services.FramePersistResult(
        frames_inserted=0,
        tracks_inserted=0,
        accepted=False,
        needs_live_broadcast=False,
    )
    assert len(session.execute_statements) == 1
    assert len(session.scalar_statements) == 1
    assert session.commits == 0


@pytest.mark.asyncio
async def test_edge_service_ingest_telemetry_returns_legacy_inserted_from_canonical_counts(
) -> None:
    class _TelemetryIngestStub:
        async def ingest_envelope(self, payload: Any, *, source: str) -> dict[str, int]:
            assert source == "http"
            return {
                "frames_inserted": 2,
                "tracks_inserted": 5,
                "broadcasted": 2,
                "duplicates": 1,
            }

    service = app_services.EdgeService(
        session_factory=lambda: None,
        settings=Settings(_env_file=None, enable_startup_services=False),
        events=_FakeEventClient(),  # type: ignore[arg-type]
        audit_logger=object(),  # type: ignore[arg-type]
        telemetry_ingest=_TelemetryIngestStub(),  # type: ignore[arg-type]
    )

    result = await service.ingest_telemetry(app_services.TelemetryEnvelope(events=[]))

    assert result == {"inserted": 5}


def _telemetry_frame(
    *,
    worker_origin: WorkerOrigin,
) -> TelemetryFrame:
    camera_id = uuid4()
    return TelemetryFrame(
        frame_id=uuid4(),
        frame_sequence=42,
        worker_origin=worker_origin,
        camera_id=camera_id,
        ts=datetime(2026, 6, 12, 12, 0, 0, tzinfo=UTC),
        profile=PublishProfile.JETSON_NANO,
        stream_mode=StreamMode.FILTERED_PREVIEW,
        counts={"car": 1},
        tracks=[
            TelemetryTrack(
                class_name="car",
                confidence=0.91,
                bbox={"x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0},
                track_id=7,
                stable_track_id=70,
                track_state="active",
                last_seen_age_ms=85,
                source_track_id=700,
                speed_kph=31.5,
                direction_deg=90.0,
                zone_id="lane-a",
                attributes={"color": "blue"},
            )
        ],
    )
