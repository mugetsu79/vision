from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient, MockTransport, Request, Response
from pydantic import BaseModel

from traffic_monitor.inference.publisher import (
    HttpPublisher,
    NatsPublisher,
    ResilientPublisher,
    TelemetryFrame,
    TelemetryTrack,
)
from traffic_monitor.streaming.mediamtx import PublishProfile, StreamMode


class _FailingNatsClient:
    async def publish(self, subject: str, payload: BaseModel) -> None:
        raise RuntimeError("nats offline")


class _RecordingNatsClient:
    def __init__(self) -> None:
        self.messages: list[tuple[str, BaseModel]] = []

    async def publish(self, subject: str, payload: BaseModel) -> None:
        self.messages.append((subject, payload))


def _telemetry_frame() -> TelemetryFrame:
    camera_id = uuid4()
    return TelemetryFrame(
        camera_id=camera_id,
        ts=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
        profile=PublishProfile.CENTRAL_GPU,
        stream_mode=StreamMode.ANNOTATED_WHIP,
        counts={"car": 1},
        tracks=[
            TelemetryTrack(
                class_name="car",
                confidence=0.96,
                bbox={"x1": 12.0, "y1": 24.0, "x2": 48.0, "y2": 66.0},
                track_id=7,
            )
        ],
    )


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
