from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js import api as js_api
from nats.js import errors as js_errors
from opentelemetry import trace
from pydantic import BaseModel

from argus.core.config import Settings

MessageHandler = Callable[["EventMessage"], Awaitable[None]]


@dataclass(slots=True)
class EventMessage:
    subject: str
    data: str
    headers: dict[str, str]


STREAM_DEFINITIONS = (
    js_api.StreamConfig(
        name="ARGUS_TRACKING",
        subjects=["evt.tracking.*"],
        description="Tracking telemetry events",
    ),
    js_api.StreamConfig(
        name="ARGUS_CAMERA_COMMANDS",
        subjects=["cmd.camera.*"],
        description="Camera control messages",
    ),
    js_api.StreamConfig(
        name="ARGUS_EDGE_HEARTBEATS",
        subjects=["edge.heartbeat.*"],
        description="Edge node heartbeat messages",
    ),
)


class NatsJetStreamClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: NATS | None = None
        self._jetstream: JetStreamContext | None = None
        self._manager: Any | None = None
        self._tracer = trace.get_tracer("argus.events")

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    async def connect(self) -> None:
        if self.is_connected:
            return

        connect_options: dict[str, Any] = {
            "servers": [self.settings.nats_url],
            "connect_timeout": self.settings.nats_connect_timeout_seconds,
        }
        if self.settings.nats_nkey_seed is not None:
            connect_options["nkeys_seed"] = self.settings.nats_nkey_seed.get_secret_value()

        self._client = await nats.connect(**connect_options)
        self._jetstream = self._client.jetstream()
        self._manager = self._client.jsm()
        await self.ensure_streams()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
        self._client = None
        self._jetstream = None
        self._manager = None

    async def ensure_streams(self) -> None:
        manager = self._require_manager()

        for stream_config in STREAM_DEFINITIONS:
            if stream_config.name is None:  # pragma: no cover - defensive branch
                continue
            try:
                await manager.stream_info(stream_config.name)
            except js_errors.NotFoundError:
                await manager.add_stream(stream_config)
            else:
                await manager.update_stream(stream_config)

    async def publish(self, subject: str, payload: BaseModel) -> None:
        jetstream = self._require_jetstream()

        with self._tracer.start_as_current_span("nats.publish") as span:
            span.set_attribute("messaging.system", "nats")
            span.set_attribute("messaging.destination.name", subject)
            await jetstream.publish(subject, payload.model_dump_json().encode("utf-8"))

    async def subscribe(self, subject: str, handler: MessageHandler) -> Any:
        jetstream = self._require_jetstream()

        async def callback(message: Msg) -> None:
            with self._tracer.start_as_current_span("nats.consume") as span:
                span.set_attribute("messaging.system", "nats")
                span.set_attribute("messaging.destination.name", message.subject)
                await handler(
                    EventMessage(
                        subject=message.subject,
                        data=message.data.decode("utf-8"),
                        headers=dict(message.headers or {}),
                    )
                )
                await message.ack()

        return await jetstream.subscribe(subject, cb=callback, manual_ack=True)

    def _require_jetstream(self) -> JetStreamContext:
        if self._jetstream is None:
            raise RuntimeError("NATS JetStream client is not connected.")
        return self._jetstream

    def _require_manager(self) -> Any:
        if self._manager is None:
            raise RuntimeError("NATS JetStream manager is not connected.")
        return self._manager
