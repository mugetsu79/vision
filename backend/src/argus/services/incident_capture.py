from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.core.events import EventMessage
from argus.models.tables import Camera, Incident, Site, Tenant

type Frame = NDArray[np.uint8]


class IncidentTriggeredEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    camera_id: UUID
    ts: datetime
    type: str
    payload: dict[str, object] = Field(default_factory=dict)


@dataclass(slots=True)
class IncidentTenantPolicy:
    tenant_id: UUID
    allow_plaintext_plates: bool
    plaintext_justification: str | None
    storage_quota_bytes: int
    current_storage_bytes: int = 0


class SupportsIncidentSubscribe(Protocol):
    async def subscribe(self, subject: str, handler: Any) -> Any: ...


class ObjectStore(Protocol):
    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str: ...


class IncidentRepository(Protocol):
    async def tenant_policy_for_camera(self, *, camera_id: UUID) -> IncidentTenantPolicy: ...

    async def create_incident(
        self,
        *,
        camera_id: UUID,
        ts: datetime,
        incident_type: str,
        payload: dict[str, object],
        clip_url: str | None,
        storage_bytes: int,
    ) -> None: ...


class ClipEncoder(Protocol):
    def encode_clip(self, frames: list[Frame], *, fps: int) -> bytes: ...


class OpenCvMjpegClipEncoder:
    def encode_clip(self, frames: list[Frame], *, fps: int) -> bytes:
        if not frames:
            return b""

        boundary = b"--argus-frame\r\nContent-Type: image/jpeg\r\n\r\n"
        chunks: list[bytes] = []
        for frame in frames:
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:  # pragma: no cover - defensive branch
                continue
            chunks.extend((boundary, encoded.tobytes(), b"\r\n"))
        chunks.append(b"--argus-frame--\r\n")
        return b"".join(chunks)


@dataclass(slots=True)
class _PendingIncident:
    event: IncidentTriggeredEvent
    ends_at: datetime
    frames: list[Frame] = field(default_factory=list)


class IncidentClipCaptureService:
    def __init__(
        self,
        *,
        object_store: ObjectStore,
        repository: IncidentRepository,
        clip_encoder: ClipEncoder | None = None,
        pre_seconds: int = 10,
        post_seconds: int = 10,
        fps: int = 10,
    ) -> None:
        self.object_store = object_store
        self.repository = repository
        self.clip_encoder = clip_encoder or OpenCvMjpegClipEncoder()
        self.pre_seconds = pre_seconds
        self.post_seconds = post_seconds
        self.fps = fps
        self._buffers: dict[UUID, deque[tuple[datetime, Frame]]] = defaultdict(deque)
        self._pending: dict[UUID, list[_PendingIncident]] = defaultdict(list)
        self._subscriptions: list[Any] = []

    async def start(self, *, camera_id: UUID, event_bus: SupportsIncidentSubscribe) -> None:
        subscription = await event_bus.subscribe(
            f"incident.triggered.{camera_id}",
            self._handle_bus_message,
        )
        self._subscriptions.append(subscription)

    async def record_frame(self, *, camera_id: UUID, frame: Frame, ts: datetime) -> None:
        buffer = self._buffers[camera_id]
        buffer.append((ts, frame.copy()))
        window_start = ts - timedelta(seconds=self.pre_seconds)
        while buffer and buffer[0][0] < window_start:
            buffer.popleft()

        completed: list[_PendingIncident] = []
        for pending in self._pending[camera_id]:
            if ts >= pending.event.ts:
                pending.frames.append(frame.copy())
            if ts >= pending.ends_at:
                completed.append(pending)

        for pending in completed:
            self._pending[camera_id].remove(pending)
            await self._finalize_pending(pending)

    async def queue_incident(self, event: IncidentTriggeredEvent) -> None:
        pre_window_start = event.ts - timedelta(seconds=self.pre_seconds)
        frames = [
            frame.copy()
            for frame_ts, frame in self._buffers[event.camera_id]
            if frame_ts >= pre_window_start
        ]
        self._pending[event.camera_id].append(
            _PendingIncident(
                event=event,
                ends_at=event.ts + timedelta(seconds=self.post_seconds),
                frames=frames,
            )
        )

    async def flush(self, *, camera_id: UUID) -> None:
        pending = list(self._pending[camera_id])
        self._pending[camera_id].clear()
        for item in pending:
            await self._finalize_pending(item)

    async def close(self) -> None:
        for subscription in self._subscriptions:
            unsubscribe = getattr(subscription, "unsubscribe", None)
            if callable(unsubscribe):
                await unsubscribe()
        self._subscriptions.clear()

    async def _handle_bus_message(
        self,
        message: EventMessage | IncidentTriggeredEvent | dict[str, Any],
    ) -> None:
        if isinstance(message, IncidentTriggeredEvent):
            event = message
        elif isinstance(message, EventMessage):
            event = IncidentTriggeredEvent.model_validate_json(message.data)
        else:
            event = IncidentTriggeredEvent.model_validate(message)
        await self.queue_incident(event)

    async def _finalize_pending(self, pending: _PendingIncident) -> None:
        policy = await self.repository.tenant_policy_for_camera(camera_id=pending.event.camera_id)
        payload = dict(pending.event.payload)
        if not (policy.allow_plaintext_plates and policy.plaintext_justification):
            payload.pop("plate_text", None)

        clip_bytes = self.clip_encoder.encode_clip(pending.frames, fps=self.fps)
        clip_size = len(clip_bytes)
        clip_url: str | None = None
        storage_bytes = 0

        if clip_size > 0 and policy.current_storage_bytes + clip_size <= policy.storage_quota_bytes:
            key = (
                f"incidents/{pending.event.camera_id}/"
                f"{pending.event.ts.strftime('%Y%m%dT%H%M%S.%fZ')}.mjpeg"
            )
            clip_url = await self.object_store.put_object(
                key=key,
                data=clip_bytes,
                content_type="video/x-motion-jpeg",
            )
            storage_bytes = clip_size
            policy.current_storage_bytes += clip_size
        else:
            payload["storage_quota_exceeded"] = True

        await self.repository.create_incident(
            camera_id=pending.event.camera_id,
            ts=pending.event.ts,
            incident_type=pending.event.type,
            payload=payload,
            clip_url=clip_url,
            storage_bytes=storage_bytes,
        )


class SQLIncidentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def tenant_policy_for_camera(self, *, camera_id: UUID) -> IncidentTenantPolicy:
        async with self.session_factory() as session:
            tenant_statement = (
                select(
                    Tenant.id,
                    Tenant.anpr_store_plaintext,
                    Tenant.anpr_plaintext_justification,
                    Tenant.incident_storage_quota_bytes,
                )
                .join(Site, Site.tenant_id == Tenant.id)
                .join(Camera, Camera.site_id == Site.id)
                .where(Camera.id == camera_id)
            )
            tenant_row = (await session.execute(tenant_statement)).one()
            usage_statement = (
                select(func.coalesce(func.sum(Incident.storage_bytes), 0))
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_row.id)
            )
            current_storage_bytes = int((await session.execute(usage_statement)).scalar_one())

        return IncidentTenantPolicy(
            tenant_id=tenant_row.id,
            allow_plaintext_plates=bool(tenant_row.anpr_store_plaintext),
            plaintext_justification=tenant_row.anpr_plaintext_justification,
            storage_quota_bytes=int(tenant_row.incident_storage_quota_bytes),
            current_storage_bytes=current_storage_bytes,
        )

    async def create_incident(
        self,
        *,
        camera_id: UUID,
        ts: datetime,
        incident_type: str,
        payload: dict[str, object],
        clip_url: str | None,
        storage_bytes: int,
    ) -> None:
        async with self.session_factory() as session:
            incident = Incident(
                camera_id=camera_id,
                ts=ts,
                type=incident_type,
                payload=payload,
                snapshot_url=None,
                clip_url=clip_url,
                storage_bytes=storage_bytes,
            )
            session.add(incident)
            await session.commit()
