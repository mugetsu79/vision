from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from pydantic import BaseModel

from argus.inference.publisher import (
    BufferedTelemetryPublisher,
    HttpPublisher,
    NatsPublisher,
    ResilientPublisher,
    TelemetryFrame,
    TelemetryTrack,
)
from argus.streaming.mediamtx import PublishProfile, StreamMode


class _FailingNatsClient:
    async def publish(self, subject: str, payload: BaseModel) -> None:
        raise RuntimeError("nats offline")


class _RecordingNatsClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, BaseModel]] = []

    async def publish(self, subject: str, payload: BaseModel) -> None:
        self.messages.append((subject, payload))


class _BlockingPublisher:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.frames: list[TelemetryFrame] = []

    async def publish(self, frame: TelemetryFrame) -> None:
        self.started.set()
        await self.release.wait()
        self.frames.append(frame)

    async def close(self) -> None:
        return None


class _NeverPublisher:
    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def publish(self, frame: TelemetryFrame) -> None:
        del frame
        self.started.set()
        await asyncio.Event().wait()

    async def close(self) -> None:
        return None


def _telemetry_frame(track_id: int = 7) -> TelemetryFrame:
    camera_id = uuid4()
    return TelemetryFrame(
        camera_id=camera_id,
        ts=datetime(2026, 4, 18, 12, 0, track_id, tzinfo=UTC),
        profile=PublishProfile.CENTRAL_GPU,
        stream_mode=StreamMode.ANNOTATED_WHIP,
        counts={"car": 1},
        tracks=[
            TelemetryTrack(
                class_name="car",
                confidence=0.96,
                bbox={"x1": 12.0, "y1": 24.0, "x2": 48.0, "y2": 66.0},
                track_id=track_id,
            )
        ],
    )


def test_telemetry_track_lifecycle_fields_are_optional_for_legacy_frames() -> None:
    track = TelemetryTrack(
        class_name="person",
        confidence=0.96,
        bbox={"x1": 12.0, "y1": 24.0, "x2": 48.0, "y2": 66.0},
        track_id=7,
    )

    assert track.stable_track_id is None
    assert track.source_track_id is None
    assert track.track_state is None
    assert track.last_seen_age_ms is None
    assert track.model_dump()["track_state"] is None


@pytest.mark.asyncio
async def test_nats_publisher_routes_frame_to_camera_subject() -> None:
    client = _RecordingNatsClient()
    publisher = NatsPublisher(client)
    frame = _telemetry_frame()

    await publisher.publish(frame)

    assert client.messages[0][0] == f"evt.tracking.{frame.camera_id}"
    assert client.messages[0][1] == frame


@pytest.mark.asyncio
async def test_http_publisher_batches_frames_with_half_second_flush() -> None:
    posted_batches: list[list[dict[str, object]]] = []
    clock_values = iter([0.0, 0.0, 0.51, 0.51, 1.02, 1.02])

    async def handler(request: Request) -> Response:
        posted_batches.append(json.loads(request.content.decode("utf-8"))["events"])
        return Response(202, json={"accepted": True})

    publisher = HttpPublisher(
        url="http://backend.internal/api/v1/edge/telemetry",
        http_client=AsyncClient(transport=MockTransport(handler)),
        monotonic=lambda: next(clock_values),
    )

    await publisher.publish(_telemetry_frame())
    await publisher.publish(_telemetry_frame())
    await publisher.close()

    assert len(posted_batches) == 1
    assert len(posted_batches[0]) == 2


@pytest.mark.asyncio
async def test_resilient_publisher_falls_back_to_http_when_nats_is_unreachable() -> None:
    batches: list[list[dict[str, object]]] = []

    async def handler(request: Request) -> Response:
        batches.append(json.loads(request.content.decode("utf-8"))["events"])
        return Response(202, json={"accepted": True})

    resilient = ResilientPublisher(
        primary=NatsPublisher(_FailingNatsClient()),
        fallback=HttpPublisher(
            url="http://backend.internal/api/v1/edge/telemetry",
            http_client=AsyncClient(transport=MockTransport(handler)),
            monotonic=lambda: 1.0,
        ),
    )

    await resilient.publish(_telemetry_frame())
    await resilient.close()

    assert len(batches) == 1
    assert len(batches[0]) == 1


@pytest.mark.asyncio
async def test_buffered_telemetry_publisher_returns_while_transport_is_blocked() -> None:
    blocking = _BlockingPublisher()
    publisher = BufferedTelemetryPublisher(
        blocking,
        max_queue_size=4,
        shutdown_timeout_seconds=1.0,
    )
    frame = _telemetry_frame()

    try:
        await asyncio.wait_for(publisher.publish(frame), timeout=0.2)
        await asyncio.wait_for(blocking.started.wait(), timeout=0.2)

        assert blocking.frames == []
    finally:
        blocking.release.set()
        await publisher.close()

    assert blocking.frames == [frame]


@pytest.mark.asyncio
async def test_buffered_telemetry_publisher_drops_oldest_queued_live_frame() -> None:
    blocking = _BlockingPublisher()
    publisher = BufferedTelemetryPublisher(
        blocking,
        max_queue_size=1,
        shutdown_timeout_seconds=1.0,
    )
    first = _telemetry_frame(1)
    stale = _telemetry_frame(2)
    latest = _telemetry_frame(3)

    try:
        await publisher.publish(first)
        await asyncio.wait_for(blocking.started.wait(), timeout=0.2)
        await publisher.publish(stale)
        await publisher.publish(latest)
    finally:
        blocking.release.set()
        await publisher.close()

    assert blocking.frames == [first, latest]
    assert publisher.dropped_frames == 1


@pytest.mark.asyncio
async def test_buffered_telemetry_publisher_times_out_stuck_transport(
    caplog: pytest.LogCaptureFixture,
) -> None:
    never = _NeverPublisher()
    publisher = BufferedTelemetryPublisher(
        never,
        max_queue_size=2,
        publish_timeout_seconds=0.01,
        shutdown_timeout_seconds=1.0,
    )
    caplog.set_level(logging.WARNING, logger="argus.inference.publisher")

    await publisher.publish(_telemetry_frame())
    await asyncio.wait_for(never.started.wait(), timeout=0.2)
    await asyncio.sleep(0.05)
    await publisher.close()

    assert any(
        "Timed out publishing live telemetry frame" in record.message
        for record in caplog.records
    )


@pytest.mark.asyncio
async def test_buffered_telemetry_publisher_throttles_drop_warnings(
    caplog: pytest.LogCaptureFixture,
) -> None:
    blocking = _BlockingPublisher()
    publisher = BufferedTelemetryPublisher(
        blocking,
        max_queue_size=1,
        shutdown_timeout_seconds=1.0,
        drop_log_interval_frames=3,
    )
    caplog.set_level(logging.WARNING, logger="argus.inference.publisher")

    try:
        await publisher.publish(_telemetry_frame(1))
        await asyncio.wait_for(blocking.started.wait(), timeout=0.2)
        for track_id in range(2, 7):
            await publisher.publish(_telemetry_frame(track_id))
    finally:
        blocking.release.set()
        await publisher.close()

    drop_warnings = [
        record
        for record in caplog.records
        if "Dropped oldest live telemetry frame" in record.message
    ]
    assert publisher.dropped_frames == 4
    assert len(drop_warnings) == 2
