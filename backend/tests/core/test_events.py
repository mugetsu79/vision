from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from pydantic import BaseModel

from traffic_monitor.core.config import Settings
from traffic_monitor.core.events import EventMessage, NatsJetStreamClient


class CameraCommand(BaseModel):
    command: str


@pytest.mark.asyncio
async def test_publish_and_receive_message_via_nats() -> None:
    settings = Settings(
        _env_file=None,
        nats_url=os.getenv("TRAFFIC_MONITOR_TEST_NATS_URL", "nats://127.0.0.1:4222"),
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
