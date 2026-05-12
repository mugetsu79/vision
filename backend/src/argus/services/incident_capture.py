from __future__ import annotations

import hashlib
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

from argus.api.contracts import EvidenceRecordingPolicy, WorkerPrivacyPolicySettings
from argus.core.events import EventMessage
from argus.models.enums import (
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.models.tables import (
    Camera,
    EvidenceArtifact,
    EvidenceLedgerEntry,
    Incident,
    Site,
    Tenant,
)
from argus.services.evidence_ledger import compute_entry_hash
from argus.services.evidence_storage import EvidenceStorageRoute, StoredEvidenceObject

Frame = NDArray[np.uint8]


class IncidentTriggeredEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    camera_id: UUID
    ts: datetime
    type: str
    scene_contract_snapshot_id: UUID | None = None
    scene_contract_hash: str | None = Field(default=None, min_length=64, max_length=64)
    privacy_manifest_snapshot_id: UUID | None = None
    privacy_manifest_hash: str | None = Field(default=None, min_length=64, max_length=64)
    runtime_passport_snapshot_id: UUID | None = None
    runtime_passport_hash: str | None = Field(default=None, min_length=64, max_length=64)
    recording_policy: EvidenceRecordingPolicy | None = None
    payload: dict[str, object] = Field(default_factory=dict)


@dataclass(slots=True)
class IncidentTenantPolicy:
    tenant_id: UUID
    allow_plaintext_plates: bool
    plaintext_justification: str | None
    storage_quota_bytes: int
    current_storage_bytes: int = 0


@dataclass(frozen=True, slots=True)
class IncidentLedgerPayload:
    action: EvidenceLedgerAction
    occurred_at: datetime
    payload: dict[str, object]


class SupportsIncidentSubscribe(Protocol):
    async def subscribe(self, subject: str, handler: Any) -> Any: ...


class ObjectStore(Protocol):
    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject: ...


class EvidenceStorageResolver(Protocol):
    async def resolve(
        self,
        *,
        camera_id: UUID,
        recording_policy: EvidenceRecordingPolicy,
    ) -> EvidenceStorageRoute: ...


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
        scene_contract_snapshot_id: UUID | None = None,
        scene_contract_hash: str | None = None,
        privacy_manifest_snapshot_id: UUID | None = None,
        privacy_manifest_hash: str | None = None,
        runtime_passport_snapshot_id: UUID | None = None,
        runtime_passport_hash: str | None = None,
        recording_policy: dict[str, object] | None = None,
        snapshot_url: str | None = None,
        artifact_payload: dict[str, object] | None = None,
        artifact_payloads: list[dict[str, object]] | None = None,
        ledger_payloads: list[IncidentLedgerPayload] | None = None,
    ) -> None: ...


class ClipEncoder(Protocol):
    def encode_clip(self, frames: list[Frame], *, fps: int) -> bytes: ...


class SnapshotEncoder(Protocol):
    def encode_snapshot(self, frame: Frame, *, quality: int) -> bytes: ...


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


class OpenCvJpegSnapshotEncoder:
    def encode_snapshot(self, frame: Frame, *, quality: int) -> bytes:
        ok, encoded = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), quality],
        )
        if not ok:
            raise ValueError("OpenCV failed to encode snapshot JPEG.")
        return encoded.tobytes()


@dataclass(slots=True)
class _PendingIncident:
    event: IncidentTriggeredEvent
    ends_at: datetime
    frames: list[tuple[datetime, Frame]] = field(default_factory=list)


class IncidentClipCaptureService:
    def __init__(
        self,
        *,
        object_store: ObjectStore,
        storage_resolver: EvidenceStorageResolver | None = None,
        repository: IncidentRepository,
        clip_encoder: ClipEncoder | None = None,
        snapshot_encoder: SnapshotEncoder | None = None,
        pre_seconds: int = 10,
        post_seconds: int = 10,
        fps: int = 10,
        recording_policy: EvidenceRecordingPolicy | None = None,
        privacy_policy: WorkerPrivacyPolicySettings | None = None,
    ) -> None:
        self.object_store = object_store
        self.storage_resolver = storage_resolver
        self.repository = repository
        self.clip_encoder = clip_encoder or OpenCvMjpegClipEncoder()
        self.snapshot_encoder = snapshot_encoder or OpenCvJpegSnapshotEncoder()
        self.recording_policy = recording_policy
        self.privacy_policy = privacy_policy
        self.pre_seconds = (
            recording_policy.pre_seconds if recording_policy is not None else pre_seconds
        )
        self.post_seconds = (
            recording_policy.post_seconds if recording_policy is not None else post_seconds
        )
        self.fps = recording_policy.fps if recording_policy is not None else fps
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
                pending.frames.append((ts, frame.copy()))
            if ts >= pending.ends_at:
                completed.append(pending)

        for pending in completed:
            self._pending[camera_id].remove(pending)
            await self._finalize_pending(pending)

    async def queue_incident(self, event: IncidentTriggeredEvent) -> None:
        pre_window_start = event.ts - timedelta(seconds=self.pre_seconds)
        frames = [
            (frame_ts, frame.copy())
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
        policy = _apply_privacy_policy(
            await self.repository.tenant_policy_for_camera(camera_id=pending.event.camera_id),
            self.privacy_policy,
        )
        payload = dict(pending.event.payload)
        if self.privacy_policy is not None:
            payload.update(_privacy_policy_payload(self.privacy_policy))
        if not (policy.allow_plaintext_plates and policy.plaintext_justification):
            payload.pop("plate_text", None)
        recording_policy = pending.event.recording_policy or self.recording_policy
        recording_policy_payload = (
            recording_policy.model_dump(mode="json") if recording_policy is not None else None
        )
        ledger_payloads = _incident_rule_ledger_payloads(pending.event)
        if recording_policy is not None and not recording_policy.enabled:
            payload["recording_disabled"] = True
            await self.repository.create_incident(
                camera_id=pending.event.camera_id,
                ts=pending.event.ts,
                incident_type=pending.event.type,
                payload=payload,
                clip_url=None,
                storage_bytes=0,
                scene_contract_snapshot_id=pending.event.scene_contract_snapshot_id,
                scene_contract_hash=pending.event.scene_contract_hash,
                privacy_manifest_snapshot_id=pending.event.privacy_manifest_snapshot_id,
                privacy_manifest_hash=pending.event.privacy_manifest_hash,
                runtime_passport_snapshot_id=pending.event.runtime_passport_snapshot_id,
                runtime_passport_hash=pending.event.runtime_passport_hash,
                recording_policy=recording_policy_payload,
                snapshot_url=None,
                artifact_payload=None,
                artifact_payloads=[],
                ledger_payloads=ledger_payloads,
            )
            return

        clip_frames = [frame for _frame_ts, frame in pending.frames]
        clip_bytes = self.clip_encoder.encode_clip(clip_frames, fps=self.fps)
        clip_size = len(clip_bytes)
        clip_url: str | None = None
        snapshot_url: str | None = None
        storage_bytes = 0
        artifact_payloads: list[dict[str, object]] = []

        if clip_size > 0 and policy.current_storage_bytes + clip_size <= policy.storage_quota_bytes:
            key = (
                f"incidents/{pending.event.camera_id}/"
                f"{pending.event.ts.strftime('%Y%m%dT%H%M%S.%fZ')}.mjpeg"
            )
            storage_route: EvidenceStorageRoute | None = None
            try:
                storage_route = await self._resolve_storage_route(
                    camera_id=pending.event.camera_id,
                    recording_policy=recording_policy,
                )
                stored_object = await storage_route.store.put_object(
                    key=key,
                    data=clip_bytes,
                    content_type="video/x-motion-jpeg",
                )
            except Exception as exc:  # noqa: BLE001
                if storage_route is None:
                    storage_route = _fallback_storage_route_for_policy(
                        object_store=self.object_store,
                        recording_policy=recording_policy,
                    )
                payload["evidence_storage_error"] = f"{type(exc).__name__}: {exc}"
                artifact_payload = _failed_event_clip_artifact_payload(
                    key=key,
                    clip_bytes=clip_bytes,
                    route=storage_route,
                    event=pending.event,
                    clip_started_at=pending.event.ts - timedelta(seconds=self.pre_seconds),
                    clip_ended_at=pending.event.ts + timedelta(seconds=self.post_seconds),
                    fps=self.fps,
                )
                artifact_payloads.append(artifact_payload)
            else:
                clip_url = stored_object.review_url
                storage_bytes = stored_object.size_bytes
                policy.current_storage_bytes += clip_size
                artifact_payload = _event_clip_artifact_payload(
                    stored_object=stored_object,
                    event=pending.event,
                    clip_started_at=pending.event.ts - timedelta(seconds=self.pre_seconds),
                    clip_ended_at=pending.event.ts + timedelta(seconds=self.post_seconds),
                    fps=self.fps,
                    status_override=storage_route.status_override,
                )
                artifact_payloads.append(artifact_payload)
        else:
            payload["storage_quota_exceeded"] = True

        if recording_policy is not None and recording_policy.snapshot_enabled:
            snapshot_frame = _select_snapshot_frame(
                pending.frames,
                triggered_at=pending.event.ts,
                offset_seconds=recording_policy.snapshot_offset_seconds,
            )
            if snapshot_frame is None:
                error = "ValueError: no frame available for snapshot capture"
                payload["snapshot_capture_error"] = error
                ledger_payloads.append(
                    _snapshot_ledger_payload(
                        action=EvidenceLedgerAction.SNAPSHOT_CAPTURE_FAILED,
                        event=pending.event,
                        payload={"error": error},
                    )
                )
            else:
                try:
                    snapshot_bytes = self.snapshot_encoder.encode_snapshot(
                        snapshot_frame,
                        quality=recording_policy.snapshot_quality,
                    )
                except Exception as exc:  # noqa: BLE001
                    error = f"{type(exc).__name__}: {exc}"
                    payload["snapshot_capture_error"] = error
                    ledger_payloads.append(
                        _snapshot_ledger_payload(
                            action=EvidenceLedgerAction.SNAPSHOT_CAPTURE_FAILED,
                            event=pending.event,
                            payload={"error": error},
                        )
                    )
                else:
                    snapshot_size = len(snapshot_bytes)
                    if snapshot_size <= 0:
                        error = "ValueError: snapshot encoder produced no bytes"
                        payload["snapshot_capture_error"] = error
                        ledger_payloads.append(
                            _snapshot_ledger_payload(
                                action=EvidenceLedgerAction.SNAPSHOT_CAPTURE_FAILED,
                                event=pending.event,
                                payload={"error": error},
                            )
                        )
                    elif (
                        policy.current_storage_bytes + snapshot_size
                        <= policy.storage_quota_bytes
                    ):
                        key = (
                            f"incidents/{pending.event.camera_id}/"
                            f"{pending.event.ts.strftime('%Y%m%dT%H%M%S.%fZ')}.jpg"
                        )
                        storage_route = None
                        try:
                            storage_route = await self._resolve_storage_route(
                                camera_id=pending.event.camera_id,
                                recording_policy=recording_policy,
                            )
                            stored_snapshot = await storage_route.store.put_object(
                                key=key,
                                data=snapshot_bytes,
                                content_type="image/jpeg",
                            )
                        except Exception as exc:  # noqa: BLE001
                            if storage_route is None:
                                storage_route = _fallback_storage_route_for_policy(
                                    object_store=self.object_store,
                                    recording_policy=recording_policy,
                                )
                            error = f"{type(exc).__name__}: {exc}"
                            payload["snapshot_capture_error"] = error
                            ledger_payloads.append(
                                _snapshot_ledger_payload(
                                    action=EvidenceLedgerAction.SNAPSHOT_CAPTURE_FAILED,
                                    event=pending.event,
                                    payload={
                                        "error": error,
                                        "object_key": key,
                                        "storage_provider": storage_route.provider.value,
                                        "storage_scope": storage_route.scope.value,
                                    },
                                )
                            )
                        else:
                            snapshot_url = stored_snapshot.review_url
                            storage_bytes += stored_snapshot.size_bytes
                            policy.current_storage_bytes += snapshot_size
                            snapshot_artifact = _snapshot_artifact_payload(
                                stored_object=stored_snapshot,
                                event=pending.event,
                                status_override=storage_route.status_override,
                            )
                            artifact_payloads.append(snapshot_artifact)
                            ledger_payloads.append(
                                _snapshot_ledger_payload(
                                    action=EvidenceLedgerAction.SNAPSHOT_AVAILABLE,
                                    event=pending.event,
                                    payload={
                                        "object_key": stored_snapshot.object_key,
                                        "sha256": stored_snapshot.sha256,
                                        "size_bytes": stored_snapshot.size_bytes,
                                        "status": snapshot_artifact["status"].value,
                                        "storage_provider": stored_snapshot.provider.value,
                                        "storage_scope": stored_snapshot.scope.value,
                                    },
                                )
                            )
                    else:
                        payload["snapshot_quota_exceeded"] = True
                        ledger_payloads.append(
                            _snapshot_ledger_payload(
                                action=EvidenceLedgerAction.SNAPSHOT_QUOTA_EXCEEDED,
                                event=pending.event,
                                payload={
                                    "size_bytes": snapshot_size,
                                    "storage_quota_bytes": policy.storage_quota_bytes,
                                    "current_storage_bytes": policy.current_storage_bytes,
                                },
                            )
                        )

        await self.repository.create_incident(
            camera_id=pending.event.camera_id,
            ts=pending.event.ts,
            incident_type=pending.event.type,
            payload=payload,
            clip_url=clip_url,
            storage_bytes=storage_bytes,
            scene_contract_snapshot_id=pending.event.scene_contract_snapshot_id,
            scene_contract_hash=pending.event.scene_contract_hash,
            privacy_manifest_snapshot_id=pending.event.privacy_manifest_snapshot_id,
            privacy_manifest_hash=pending.event.privacy_manifest_hash,
            runtime_passport_snapshot_id=pending.event.runtime_passport_snapshot_id,
            runtime_passport_hash=pending.event.runtime_passport_hash,
            recording_policy=recording_policy_payload,
            snapshot_url=snapshot_url,
            artifact_payload=artifact_payloads[0] if artifact_payloads else None,
            artifact_payloads=artifact_payloads,
            ledger_payloads=ledger_payloads,
        )

    async def _resolve_storage_route(
        self,
        *,
        camera_id: UUID,
        recording_policy: EvidenceRecordingPolicy | None,
    ) -> EvidenceStorageRoute:
        if self.storage_resolver is not None and recording_policy is not None:
            return await self.storage_resolver.resolve(
                camera_id=camera_id,
                recording_policy=recording_policy,
            )
        return EvidenceStorageRoute(
            store=self.object_store,
            provider=EvidenceStorageProvider.MINIO,
            scope=EvidenceStorageScope.CENTRAL,
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
        scene_contract_snapshot_id: UUID | None = None,
        scene_contract_hash: str | None = None,
        privacy_manifest_snapshot_id: UUID | None = None,
        privacy_manifest_hash: str | None = None,
        runtime_passport_snapshot_id: UUID | None = None,
        runtime_passport_hash: str | None = None,
        recording_policy: dict[str, object] | None = None,
        snapshot_url: str | None = None,
        artifact_payload: dict[str, object] | None = None,
        artifact_payloads: list[dict[str, object]] | None = None,
        ledger_payloads: list[IncidentLedgerPayload] | None = None,
    ) -> None:
        async with self.session_factory() as session:
            incident = Incident(
                camera_id=camera_id,
                ts=ts,
                type=incident_type,
                payload=payload,
                snapshot_url=snapshot_url,
                clip_url=clip_url,
                storage_bytes=storage_bytes,
                scene_contract_snapshot_id=scene_contract_snapshot_id,
                scene_contract_hash=scene_contract_hash,
                privacy_manifest_snapshot_id=privacy_manifest_snapshot_id,
                privacy_manifest_hash=privacy_manifest_hash,
                runtime_passport_snapshot_id=runtime_passport_snapshot_id,
                runtime_passport_hash=runtime_passport_hash,
                recording_policy=recording_policy,
            )
            session.add(incident)
            await session.flush()
            payloads = artifact_payloads or (
                [artifact_payload] if artifact_payload is not None else []
            )
            for payload_item in payloads:
                session.add(
                    EvidenceArtifact(
                        incident_id=incident.id,
                        camera_id=camera_id,
                        **payload_item,
                    )
                )
            ledger_items = ledger_payloads or []
            tenant_id = None
            if ledger_items:
                tenant_id = (
                    await session.execute(
                        select(Site.tenant_id)
                        .join(Camera, Camera.site_id == Site.id)
                        .where(Camera.id == camera_id)
                    )
                ).scalar_one()
            previous_hash: str | None = None
            for index, ledger_payload in enumerate(ledger_items, start=1):
                assert tenant_id is not None
                entry_hash = compute_entry_hash(
                    incident_id=incident.id,
                    sequence=index,
                    action=ledger_payload.action,
                    occurred_at=ledger_payload.occurred_at,
                    actor_type="system",
                    actor_subject=None,
                    payload=ledger_payload.payload,
                    previous_entry_hash=previous_hash,
                )
                session.add(
                    EvidenceLedgerEntry(
                        tenant_id=tenant_id,
                        incident_id=incident.id,
                        camera_id=camera_id,
                        sequence=index,
                        action=ledger_payload.action,
                        actor_type="system",
                        actor_subject=None,
                        occurred_at=ledger_payload.occurred_at,
                        payload=ledger_payload.payload,
                        previous_entry_hash=previous_hash,
                        entry_hash=entry_hash,
                    )
                )
                previous_hash = entry_hash
            await session.commit()


def _event_clip_artifact_payload(
    *,
    stored_object: StoredEvidenceObject,
    event: IncidentTriggeredEvent,
    clip_started_at: datetime,
    clip_ended_at: datetime,
    fps: int,
    status_override: EvidenceArtifactStatus | None = None,
) -> dict[str, object]:
    return {
        "kind": EvidenceArtifactKind.EVENT_CLIP,
        "status": status_override
        or _artifact_status_for_storage(
            provider=stored_object.provider,
            scope=stored_object.scope,
        ),
        "storage_provider": stored_object.provider,
        "storage_scope": stored_object.scope,
        "bucket": stored_object.bucket,
        "object_key": stored_object.object_key,
        "content_type": stored_object.content_type,
        "sha256": stored_object.sha256,
        "size_bytes": stored_object.size_bytes,
        "clip_started_at": clip_started_at,
        "triggered_at": event.ts,
        "clip_ended_at": clip_ended_at,
        "duration_seconds": max(0.0, (clip_ended_at - clip_started_at).total_seconds()),
        "fps": fps,
        "scene_contract_hash": event.scene_contract_hash,
        "privacy_manifest_hash": event.privacy_manifest_hash,
    }


def _failed_event_clip_artifact_payload(
    *,
    key: str,
    clip_bytes: bytes,
    route: EvidenceStorageRoute,
    event: IncidentTriggeredEvent,
    clip_started_at: datetime,
    clip_ended_at: datetime,
    fps: int,
) -> dict[str, object]:
    return {
        "kind": EvidenceArtifactKind.EVENT_CLIP,
        "status": EvidenceArtifactStatus.CAPTURE_FAILED,
        "storage_provider": route.provider,
        "storage_scope": route.scope,
        "bucket": None,
        "object_key": key,
        "content_type": "video/x-motion-jpeg",
        "sha256": hashlib.sha256(clip_bytes).hexdigest(),
        "size_bytes": len(clip_bytes),
        "clip_started_at": clip_started_at,
        "triggered_at": event.ts,
        "clip_ended_at": clip_ended_at,
        "duration_seconds": max(0.0, (clip_ended_at - clip_started_at).total_seconds()),
        "fps": fps,
        "scene_contract_hash": event.scene_contract_hash,
        "privacy_manifest_hash": event.privacy_manifest_hash,
    }


def _snapshot_artifact_payload(
    *,
    stored_object: StoredEvidenceObject,
    event: IncidentTriggeredEvent,
    status_override: EvidenceArtifactStatus | None = None,
) -> dict[str, object]:
    return {
        "kind": EvidenceArtifactKind.SNAPSHOT,
        "status": status_override
        or _artifact_status_for_storage(
            provider=stored_object.provider,
            scope=stored_object.scope,
        ),
        "storage_provider": stored_object.provider,
        "storage_scope": stored_object.scope,
        "bucket": stored_object.bucket,
        "object_key": stored_object.object_key,
        "content_type": stored_object.content_type,
        "sha256": stored_object.sha256,
        "size_bytes": stored_object.size_bytes,
        "clip_started_at": None,
        "triggered_at": event.ts,
        "clip_ended_at": None,
        "duration_seconds": None,
        "fps": None,
        "scene_contract_hash": event.scene_contract_hash,
        "privacy_manifest_hash": event.privacy_manifest_hash,
    }


def _snapshot_ledger_payload(
    *,
    action: EvidenceLedgerAction,
    event: IncidentTriggeredEvent,
    payload: dict[str, object],
) -> IncidentLedgerPayload:
    return IncidentLedgerPayload(
        action=action,
        occurred_at=event.ts,
        payload={
            "artifact_kind": EvidenceArtifactKind.SNAPSHOT.value,
            "scene_contract_hash": event.scene_contract_hash,
            "privacy_manifest_hash": event.privacy_manifest_hash,
            **payload,
        },
    )


def _incident_rule_ledger_payloads(event: IncidentTriggeredEvent) -> list[IncidentLedgerPayload]:
    trigger_rule = event.payload.get("trigger_rule")
    if not isinstance(trigger_rule, dict):
        return []
    detection = event.payload.get("detection")
    payload = {
        "rule_id": trigger_rule.get("id"),
        "name": trigger_rule.get("name"),
        "incident_type": trigger_rule.get("incident_type"),
        "severity": trigger_rule.get("severity"),
        "action": trigger_rule.get("action"),
        "cooldown_seconds": trigger_rule.get("cooldown_seconds"),
        "predicate": trigger_rule.get("predicate"),
        "rule_hash": trigger_rule.get("rule_hash"),
        "scene_contract_hash": event.scene_contract_hash,
        "privacy_manifest_hash": event.privacy_manifest_hash,
    }
    if isinstance(detection, dict):
        payload["detection"] = {
            key: detection[key]
            for key in ("class_name", "zone_id", "confidence", "track_id")
            if key in detection
        }
    return [
        IncidentLedgerPayload(
            action=EvidenceLedgerAction.INCIDENT_RULE_ATTACHED,
            occurred_at=event.ts,
            payload=payload,
        )
    ]


def _select_snapshot_frame(
    frames: list[tuple[datetime, Frame]],
    *,
    triggered_at: datetime,
    offset_seconds: float,
) -> Frame | None:
    if not frames:
        return None
    target_at = triggered_at + timedelta(seconds=offset_seconds)
    return min(
        frames,
        key=lambda sample: abs((sample[0] - target_at).total_seconds()),
    )[1]


def _artifact_status_for_storage(
    *,
    provider: EvidenceStorageProvider,
    scope: EvidenceStorageScope,
) -> EvidenceArtifactStatus:
    if provider is EvidenceStorageProvider.LOCAL_FILESYSTEM and scope is EvidenceStorageScope.EDGE:
        return EvidenceArtifactStatus.LOCAL_ONLY
    return EvidenceArtifactStatus.REMOTE_AVAILABLE


def _fallback_storage_route_for_policy(
    *,
    object_store: ObjectStore,
    recording_policy: EvidenceRecordingPolicy | None,
) -> EvidenceStorageRoute:
    if recording_policy is None:
        return EvidenceStorageRoute(
            store=object_store,
            provider=EvidenceStorageProvider.MINIO,
            scope=EvidenceStorageScope.CENTRAL,
        )
    if recording_policy.storage_profile == "cloud":
        return EvidenceStorageRoute(
            store=object_store,
            provider=EvidenceStorageProvider.S3_COMPATIBLE,
            scope=EvidenceStorageScope.CLOUD,
        )
    if recording_policy.storage_profile in {"edge_local", "local_first"}:
        return EvidenceStorageRoute(
            store=object_store,
            provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
            scope=EvidenceStorageScope.EDGE,
            status_override=(
                EvidenceArtifactStatus.UPLOAD_PENDING
                if recording_policy.storage_profile == "local_first"
                else None
            ),
        )
    return EvidenceStorageRoute(
        store=object_store,
        provider=EvidenceStorageProvider.MINIO,
        scope=EvidenceStorageScope.CENTRAL,
    )


def _apply_privacy_policy(
    policy: IncidentTenantPolicy,
    privacy_policy: WorkerPrivacyPolicySettings | None,
) -> IncidentTenantPolicy:
    if privacy_policy is None:
        return policy
    plaintext_allowed = privacy_policy.plaintext_plate_storage == "allowed"
    return IncidentTenantPolicy(
        tenant_id=policy.tenant_id,
        allow_plaintext_plates=plaintext_allowed,
        plaintext_justification=(
            policy.plaintext_justification
            or "Privacy policy profile allows plaintext plate storage."
            if plaintext_allowed
            else None
        ),
        storage_quota_bytes=privacy_policy.storage_quota_bytes,
        current_storage_bytes=policy.current_storage_bytes,
    )


def _privacy_policy_payload(
    privacy_policy: WorkerPrivacyPolicySettings,
) -> dict[str, object]:
    return {
        "privacy_policy_profile_id": str(privacy_policy.profile_id)
        if privacy_policy.profile_id is not None
        else None,
        "privacy_policy_profile_hash": privacy_policy.profile_hash,
        "privacy_retention_days": privacy_policy.retention_days,
        "privacy_residency": privacy_policy.residency,
    }
