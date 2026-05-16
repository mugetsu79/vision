from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

import httpx
from pydantic import BaseModel, ConfigDict, Field

from argus.streaming.mediamtx import PublishProfile, StreamMode

MonotonicClock = Callable[[], float]
logger = logging.getLogger(__name__)
_TIMEOUT_ERRORS: tuple[type[BaseException], ...] = (TimeoutError,)
_asyncio_timeout_error = getattr(asyncio, "TimeoutError", None)
if (
    isinstance(_asyncio_timeout_error, type)
    and issubclass(_asyncio_timeout_error, BaseException)
    and _asyncio_timeout_error is not TimeoutError
):
    _TIMEOUT_ERRORS = (TimeoutError, _asyncio_timeout_error)


class TelemetryTrack(BaseModel):
    model_config = ConfigDict(frozen=True)

    class_name: str
    confidence: float
    bbox: dict[str, float]
    track_id: int
    stable_track_id: int | None = None
    track_state: Literal["active", "coasting"] | None = None
    last_seen_age_ms: int | None = None
    source_track_id: int | None = None
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


class BufferedTelemetryPublisher:
    def __init__(
        self,
        wrapped_publisher: PublisherTransport,
        *,
        max_queue_size: int = 64,
        publish_timeout_seconds: float = 1.0,
        shutdown_timeout_seconds: float = 2.0,
        drop_log_interval_frames: int = 100,
    ) -> None:
        if max_queue_size < 1:
            raise ValueError("max_queue_size must be at least 1")
        if publish_timeout_seconds <= 0:
            raise ValueError("publish_timeout_seconds must be greater than 0")
        if shutdown_timeout_seconds <= 0:
            raise ValueError("shutdown_timeout_seconds must be greater than 0")
        if drop_log_interval_frames < 1:
            raise ValueError("drop_log_interval_frames must be at least 1")
        self.wrapped_publisher = wrapped_publisher
        self.max_queue_size = max_queue_size
        self.publish_timeout_seconds = publish_timeout_seconds
        self.shutdown_timeout_seconds = shutdown_timeout_seconds
        self.drop_log_interval_frames = drop_log_interval_frames
        self.dropped_frames = 0
        self._queue: asyncio.Queue[TelemetryFrame | None] = asyncio.Queue(
            maxsize=max_queue_size
        )
        self._worker_task: asyncio.Task[None] | None = None
        self._closed = False

    async def publish(self, frame: TelemetryFrame) -> None:
        if self._closed:
            return
        self._ensure_worker()
        try:
            self._queue.put_nowait(frame)
        except asyncio.QueueFull:
            self._drop_oldest_pending()
            try:
                self._queue.put_nowait(frame)
            except asyncio.QueueFull:
                self.dropped_frames += 1
                logger.warning(
                    "Dropped live telemetry frame for camera %s because the "
                    "background queue remained full.",
                    frame.camera_id,
                )

    async def close(self) -> None:
        self._closed = True
        worker_task = self._worker_task
        try:
            if worker_task is None:
                return
            if worker_task.done():
                await worker_task
                return
            try:
                await asyncio.wait_for(
                    self._queue.put(None),
                    timeout=self.shutdown_timeout_seconds,
                )
                await asyncio.wait_for(
                    worker_task,
                    timeout=self.shutdown_timeout_seconds,
                )
            except _TIMEOUT_ERRORS:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task
                logger.warning(
                    "Timed out while flushing live telemetry queue; dropped %s "
                    "pending frames.",
                    self._queue.qsize(),
                )
        finally:
            await self.wrapped_publisher.close()

    def _ensure_worker(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(
                self._drain(),
                name="argus-live-telemetry-publisher",
            )

    def _drop_oldest_pending(self) -> None:
        try:
            dropped = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        self._queue.task_done()
        if dropped is not None:
            self.dropped_frames += 1
            if self._should_log_dropped_frame():
                logger.warning(
                    "Dropped oldest live telemetry frame for camera %s because the "
                    "background queue is full. dropped_frames=%s pending_frames=%s",
                    dropped.camera_id,
                    self.dropped_frames,
                    self._queue.qsize(),
                )

    async def _drain(self) -> None:
        while True:
            frame = await self._queue.get()
            try:
                if frame is None:
                    return
                await self._publish_with_timeout(frame)
            except Exception:
                logger.exception(
                    "Failed to publish buffered live telemetry for camera %s; "
                    "continuing worker loop.",
                    frame.camera_id if frame is not None else "<shutdown>",
                )
            finally:
                self._queue.task_done()

    def _should_log_dropped_frame(self) -> bool:
        return (
            self.dropped_frames == 1
            or self.dropped_frames % self.drop_log_interval_frames == 0
        )

    async def _publish_with_timeout(self, frame: TelemetryFrame) -> None:
        try:
            await asyncio.wait_for(
                self.wrapped_publisher.publish(frame),
                timeout=self.publish_timeout_seconds,
            )
        except _TIMEOUT_ERRORS:
            logger.warning(
                "Timed out publishing live telemetry frame for camera %s after %.1fs; "
                "dropping stale frame.",
                frame.camera_id,
                self.publish_timeout_seconds,
            )


class HttpPublisher:
    def __init__(
        self,
        *,
        url: str,
        headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
        flush_interval_seconds: float = 0.5,
        max_buffer_size: int | None = None,
        monotonic: MonotonicClock = time.monotonic,
    ) -> None:
        if max_buffer_size is not None and max_buffer_size < 1:
            raise ValueError("max_buffer_size must be at least 1 when set")
        self.url = url
        self.headers = dict(headers or {})
        self.flush_interval_seconds = flush_interval_seconds
        self.max_buffer_size = max_buffer_size
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
        if self.max_buffer_size is not None:
            self._buffer = self._buffer[-self.max_buffer_size :]
        if now - self._batch_started_at >= self.flush_interval_seconds:
            await self.flush()

    async def flush(self) -> None:
        if not self._buffer:
            return
        payload = TelemetryBatch(events=list(self._buffer))
        response = await self._http_client.post(
            self.url,
            json=payload.model_dump(mode="json"),
            headers=self.headers or None,
        )
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
