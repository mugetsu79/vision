from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field

from traffic_monitor.streaming.mediamtx import PublishProfile, StreamMode

type MonotonicClock = Callable[[], float]


class TelemetryTrack(BaseModel):
    model_config = ConfigDict(frozen=True)

    class_name: str
    confidence: float
    bbox: dict[str, float]
    track_id: int
    speed_kph: float | None = None
    direction_deg: float | None = None
    zone_id: str | None = None
    attributes: dict[str, object] = Field(default_factory=dict)


class TelemetryFrame(BaseModel):
    model_config = ConfigDict(frozen=True)

    camera_id: UUID
    ts: datetime
    profile: PublishProfile
    stream_mode: StreamMode
    counts: dict[str, int]
    tracks: list[TelemetryTrack]


class TelemetryBatch(BaseModel):
    events: list[TelemetryFrame]


class SupportsNatsPublish(Protocol):
    async def publish(self, subject: str, payload: BaseModel) -> None: ...


class PublisherTransport(Protocol):
    async def publish(self, frame: TelemetryFrame) -> None: ...

    async def close(self) -> None: ...


class NatsPublisher:
    def __init__(
        self,
        client: SupportsNatsPublish,
        *,
        subject_prefix: str = "evt.tracking",
    ) -> None:
        self.client = client
        self.subject_prefix = subject_prefix.rstrip(".")

    async def publish(self, frame: TelemetryFrame) -> None:
        await self.client.publish(f"{self.subject_prefix}.{frame.camera_id}", frame)

    async def close(self) -> None:
        return None


class HttpPublisher:
    def __init__(
        self,
        *,
        url: str,
        http_client: httpx.AsyncClient | None = None,
        flush_interval_seconds: float = 0.5,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        self.url = url
        self.flush_interval_seconds = flush_interval_seconds
        self._monotonic = monotonic
        self._owned_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient()
        self._batch_started_at: float | None = None
        self._buffer: list[TelemetryFrame] = []

    async def publish(self, frame: TelemetryFrame) -> None:
        now = self._monotonic()
        if self._batch_started_at is None:
            self._batch_started_at = now
        self._buffer.append(frame)
        if now - self._batch_started_at >= self.flush_interval_seconds:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return
        payload = TelemetryBatch(events=list(self._buffer))
        response = await self._http_client.post(self.url, json=payload.model_dump(mode="json"))
        response.raise_for_status()
        self._buffer.clear()
        self._batch_started_at = None

    async def close(self) -> None:
        await self.flush()
        if self._owned_client:
            await self._http_client.aclose()


class ResilientPublisher:
    def __init__(self, *, primary: PublisherTransport, fallback: PublisherTransport) -> None:
        self.primary = primary
        self.fallback = fallback

    async def publish(self, frame: TelemetryFrame) -> None:
        try:
            await self.primary.publish(frame)
        except Exception:
            await self.fallback.publish(frame)

    async def close(self) -> None:
        await self.primary.close()
        await self.fallback.close()
