from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from pydantic import BaseModel

from argus.core.config import Settings
from argus.core.events import STREAM_DEFINITIONS, EventMessage, NatsJetStreamClient


class CameraCommand(BaseModel):
    command: str


class _RecordingRawNatsClient:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))


class _RecordingJetStream:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    async def publish(self, subject: str, payload: bytes) -> None:
        self.published.append((subject, payload))


def test_stream_definitions_include_rule_events() -> None:
    subjects = {
        subject
        for stream in STREAM_DEFINITIONS
        for subject in stream.subjects
    }

    assert "evt.rule.*" in subjects


def test_stream_definitions_include_live_edge_and_worker_tracking_events() -> None:
    subjects = {
        subject
        for stream in STREAM_DEFINITIONS
        for subject in stream.subjects
    }

    assert "evt.tracking.*" in subjects
    assert "evt.edge.tracking.*" in subjects
    assert "evt.worker.tracking.*" in subjects


@pytest.mark.asyncio
async def test_publish_bytes_uses_raw_nats_client_when_streams_are_unmanaged() -> None:
    settings = Settings(
        _env_file=None,
        nats_manage_streams=False,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    events_client = NatsJetStreamClient(settings)
    raw_client = _RecordingRawNatsClient()
    events_client._client = raw_client  # type: ignore[assignment]
    payload = b'{"command":"reload"}'

    await events_client.publish_bytes("cmd.camera.test", payload)

    assert raw_client.published == [("cmd.camera.test", payload)]


@pytest.mark.asyncio
async def test_publish_bytes_uses_jetstream_when_streams_are_managed() -> None:
    settings = Settings(
        _env_file=None,
        nats_manage_streams=True,
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    events_client = NatsJetStreamClient(settings)
    jetstream = _RecordingJetStream()
    events_client._jetstream = jetstream  # type: ignore[assignment]
    payload = b'{"command":"reload"}'

    await events_client.publish_bytes("cmd.camera.test", payload)

    assert jetstream.published == [("cmd.camera.test", payload)]


@pytest.mark.asyncio
async def test_publish_and_receive_message_via_nats() -> None:
    settings = Settings(
        _env_file=None,
        nats_url=os.getenv("ARGUS_TEST_NATS_URL", "nats://127.0.0.1:4222"),
        rtsp_encryption_key="argus-dev-rtsp-key",
    )
    events_client = NatsJetStreamClient(settings)

    try:
        await events_client.connect()
    except Exception as exc:  # pragma: no cover - integration guard
        pytest.skip(f"NATS is not available for Prompt 2 verification: {exc}")

    received_message: asyncio.Future[EventMessage] = asyncio.get_running_loop().create_future()
    camera_id = str(uuid.uuid4())
    subject = f"cmd.camera.{camera_id}"

    async def handle_message(message: EventMessage) -> None:
        if not received_message.done():
            received_message.set_result(message)

    subscription = await events_client.subscribe(subject, handle_message)

    await events_client.publish(subject, CameraCommand(command="reload"))
    message = await asyncio.wait_for(received_message, timeout=5)

    assert message.subject == subject
    assert CameraCommand.model_validate_json(message.data).command == "reload"

    await subscription.unsubscribe()
    await events_client.close()
