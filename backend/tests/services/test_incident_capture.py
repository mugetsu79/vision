from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import numpy as np
import pytest

from argus.api.contracts import EvidenceRecordingPolicy
from argus.models.enums import (
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.services.evidence_storage import EvidenceStorageRoute, StoredEvidenceObject
from argus.services.incident_capture import (
    IncidentClipCaptureService,
    IncidentTenantPolicy,
    IncidentTriggeredEvent,
)


@dataclass
class _FakeObjectStore:
    uploads: list[tuple[str, bytes, str]] = field(default_factory=list)
    provider: EvidenceStorageProvider = EvidenceStorageProvider.MINIO
    scope: EvidenceStorageScope = EvidenceStorageScope.CENTRAL
    bucket: str | None = "incidents"
    review_url_prefix: str | None = "https://minio.local"
    error: Exception | None = None
    sha256: str = "a" * 64

    async def put_object(self, *, key: str, data: bytes, content_type: str) -> StoredEvidenceObject:
        if self.error is not None:
            raise self.error
        self.uploads.append((key, data, content_type))
        return StoredEvidenceObject(
            provider=self.provider,
            scope=self.scope,
            bucket=self.bucket,
            object_key=key,
            content_type=content_type,
            sha256=self.sha256,
            size_bytes=len(data),
            review_url=f"{self.review_url_prefix}/{key}" if self.review_url_prefix else None,
        )


@dataclass
class _FakeStorageResolver:
    routes: dict[UUID | None, EvidenceStorageRoute]
    calls: list[tuple[UUID, EvidenceRecordingPolicy]] = field(default_factory=list)

    async def resolve(
        self,
        *,
        camera_id: UUID,
        recording_policy: EvidenceRecordingPolicy,
    ) -> EvidenceStorageRoute:
        self.calls.append((camera_id, recording_policy))
        return self.routes[recording_policy.storage_profile_id]


@dataclass
class _FakeIncidentRepository:
    policy: IncidentTenantPolicy
    incidents: list[dict[str, object]] = field(default_factory=list)

    async def tenant_policy_for_camera(self, *, camera_id: UUID) -> IncidentTenantPolicy:
        return self.policy

    async def create_incident(
        self,
        *,
        camera_id: UUID,
        ts: datetime,
        incident_type: str,
        payload: dict[str, object],
        clip_url: str | None,
        storage_bytes: int,
        scene_contract_snapshot_id=None,  # noqa: ANN001
        scene_contract_hash: str | None = None,
        privacy_manifest_snapshot_id=None,  # noqa: ANN001
        privacy_manifest_hash: str | None = None,
        recording_policy: dict[str, object] | None = None,
        artifact_payload: dict[str, object] | None = None,
    ) -> None:
        self.incidents.append(
            {
                "camera_id": camera_id,
                "ts": ts,
                "type": incident_type,
                "payload": payload,
                "clip_url": clip_url,
                "storage_bytes": storage_bytes,
                "scene_contract_snapshot_id": scene_contract_snapshot_id,
                "scene_contract_hash": scene_contract_hash,
                "privacy_manifest_snapshot_id": privacy_manifest_snapshot_id,
                "privacy_manifest_hash": privacy_manifest_hash,
                "recording_policy": recording_policy,
                "artifact_payload": artifact_payload,
            }
        )


@dataclass
class _FakeClipEncoder:
    encoded_bytes: bytes = b"synthetic-clip"

    def encode_clip(self, frames: list[np.ndarray], *, fps: int) -> bytes:
        assert frames
        assert fps == 2
        return self.encoded_bytes


@pytest.mark.asyncio
async def test_incident_capture_uploads_clip_and_persists_incident() -> None:
    camera_id = uuid4()
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=False,
                plaintext_justification=None,
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    started_at = datetime(2026, 4, 19, 12, 0, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=started_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at + timedelta(milliseconds=500),
            type="anpr.line_crossed",
            scene_contract_hash="b" * 64,
            privacy_manifest_hash="c" * 64,
            payload={
                "plate_text": "ZH123456",
                "plate_hash": "hash-value",
            },
        )
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=1),
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=2),
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    uploads = service.object_store.uploads  # type: ignore[attr-defined]

    assert len(uploads) == 1
    assert uploads[0][0].startswith("incidents/")
    assert len(incidents) == 1
    assert incidents[0]["clip_url"] == f"https://minio.local/{uploads[0][0]}"
    assert incidents[0]["storage_bytes"] == len(b"synthetic-clip")
    assert incidents[0]["payload"]["plate_hash"] == "hash-value"
    assert "plate_text" not in incidents[0]["payload"]
    assert incidents[0]["scene_contract_hash"] == "b" * 64
    assert incidents[0]["privacy_manifest_hash"] == "c" * 64
    artifact = incidents[0]["artifact_payload"]
    assert isinstance(artifact, dict)
    assert artifact["kind"] is EvidenceArtifactKind.EVENT_CLIP
    assert artifact["status"] is EvidenceArtifactStatus.REMOTE_AVAILABLE
    assert artifact["storage_provider"] is EvidenceStorageProvider.MINIO
    assert artifact["storage_scope"] is EvidenceStorageScope.CENTRAL
    assert artifact["bucket"] == "incidents"
    assert artifact["object_key"] == uploads[0][0]
    assert artifact["content_type"] == "video/x-motion-jpeg"
    assert artifact["sha256"] == "a" * 64
    assert artifact["size_bytes"] == len(b"synthetic-clip")
    assert artifact["triggered_at"] == started_at + timedelta(milliseconds=500)
    assert artifact["fps"] == 2
    assert artifact["scene_contract_hash"] == "b" * 64
    assert artifact["privacy_manifest_hash"] == "c" * 64


@pytest.mark.asyncio
async def test_incident_capture_skips_clip_when_tenant_storage_quota_is_exceeded() -> None:
    camera_id = uuid4()
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="Municipal evidentiary retention policy",
                storage_quota_bytes=4,
                current_storage_bytes=4,
            )
        ),
        clip_encoder=_FakeClipEncoder(encoded_bytes=b"longer-than-quota"),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    started_at = datetime(2026, 4, 19, 12, 5, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=started_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at,
            type="anpr.line_crossed",
            payload={
                "plate_text": "ZH987654",
                "plate_hash": "hash-two",
            },
        )
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=2),
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    uploads = service.object_store.uploads  # type: ignore[attr-defined]

    assert uploads == []
    assert len(incidents) == 1
    assert incidents[0]["clip_url"] is None
    assert incidents[0]["storage_bytes"] == 0
    assert incidents[0]["payload"]["storage_quota_exceeded"] is True
    assert incidents[0]["payload"]["plate_text"] == "ZH987654"
    assert incidents[0]["artifact_payload"] is None


@pytest.mark.asyncio
async def test_incident_capture_respects_disabled_recording_policy() -> None:
    camera_id = uuid4()
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=False,
                plaintext_justification=None,
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(),
        recording_policy=EvidenceRecordingPolicy(enabled=False),
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    triggered_at = datetime(2026, 4, 19, 12, 10, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=triggered_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=triggered_at,
            type="rule.record_clip",
            payload={"track_id": 42},
        )
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    uploads = service.object_store.uploads  # type: ignore[attr-defined]
    assert uploads == []
    assert len(incidents) == 1
    assert incidents[0]["clip_url"] is None
    assert incidents[0]["storage_bytes"] == 0
    assert incidents[0]["artifact_payload"] is None
    assert incidents[0]["payload"]["recording_disabled"] is True
    assert incidents[0]["recording_policy"] == EvidenceRecordingPolicy(
        enabled=False
    ).model_dump(mode="json")


@pytest.mark.asyncio
async def test_incident_capture_routes_storage_per_event_policy() -> None:
    camera_id = uuid4()
    cloud_profile_id = uuid4()
    edge_profile_id = uuid4()
    cloud_store = _FakeObjectStore(
        provider=EvidenceStorageProvider.S3_COMPATIBLE,
        scope=EvidenceStorageScope.CLOUD,
        bucket="cloud-incidents",
        review_url_prefix="https://s3.example.com",
    )
    edge_store = _FakeObjectStore(
        provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
        scope=EvidenceStorageScope.EDGE,
        bucket=None,
        review_url_prefix=None,
    )
    resolver = _FakeStorageResolver(
        routes={
            cloud_profile_id: EvidenceStorageRoute(
                store=cloud_store,
                provider=EvidenceStorageProvider.S3_COMPATIBLE,
                scope=EvidenceStorageScope.CLOUD,
            ),
            edge_profile_id: EvidenceStorageRoute(
                store=edge_store,
                provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
                scope=EvidenceStorageScope.EDGE,
            ),
        }
    )
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        storage_resolver=resolver,
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="policy",
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    started_at = datetime(2026, 5, 11, 12, 0, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=started_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at,
            type="rule.cloud",
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="cloud",
                storage_profile_id=cloud_profile_id,
            ),
        )
    )
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at + timedelta(milliseconds=100),
            type="rule.edge",
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="edge_local",
                storage_profile_id=edge_profile_id,
            ),
        )
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]

    assert len(cloud_store.uploads) == 1
    assert len(edge_store.uploads) == 1
    assert [policy.storage_profile_id for _, policy in resolver.calls] == [
        cloud_profile_id,
        edge_profile_id,
    ]
    assert incidents[0]["clip_url"] == f"https://s3.example.com/{cloud_store.uploads[0][0]}"
    assert (
        incidents[0]["artifact_payload"]["storage_provider"]
        is EvidenceStorageProvider.S3_COMPATIBLE
    )
    assert incidents[0]["artifact_payload"]["storage_scope"] is EvidenceStorageScope.CLOUD
    assert incidents[1]["clip_url"] is None
    assert (
        incidents[1]["artifact_payload"]["storage_provider"]
        is EvidenceStorageProvider.LOCAL_FILESYSTEM
    )
    assert incidents[1]["artifact_payload"]["storage_scope"] is EvidenceStorageScope.EDGE


@pytest.mark.asyncio
async def test_incident_capture_marks_local_first_upload_pending() -> None:
    camera_id = uuid4()
    profile_id = uuid4()
    local_store = _FakeObjectStore(
        provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
        scope=EvidenceStorageScope.EDGE,
        bucket=None,
        review_url_prefix=None,
    )
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        storage_resolver=_FakeStorageResolver(
            routes={
                profile_id: EvidenceStorageRoute(
                    store=local_store,
                    provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
                    scope=EvidenceStorageScope.EDGE,
                    status_override=EvidenceArtifactStatus.UPLOAD_PENDING,
                )
            }
        ),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="policy",
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    triggered_at = datetime(2026, 5, 11, 13, 0, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=triggered_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=triggered_at,
            type="rule.local_first",
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="local_first",
                storage_profile_id=profile_id,
            ),
        )
    )
    await service.flush(camera_id=camera_id)

    artifact = service.repository.incidents[0]["artifact_payload"]  # type: ignore[attr-defined]
    assert artifact["status"] is EvidenceArtifactStatus.UPLOAD_PENDING
    assert artifact["storage_provider"] is EvidenceStorageProvider.LOCAL_FILESYSTEM
    assert artifact["storage_scope"] is EvidenceStorageScope.EDGE


@pytest.mark.asyncio
async def test_incident_capture_persists_incident_when_selected_storage_fails() -> None:
    camera_id = uuid4()
    profile_id = uuid4()
    failing_store = _FakeObjectStore(
        provider=EvidenceStorageProvider.S3_COMPATIBLE,
        scope=EvidenceStorageScope.CLOUD,
        bucket="cloud-incidents",
        error=RuntimeError("bucket unavailable"),
    )
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        storage_resolver=_FakeStorageResolver(
            routes={
                profile_id: EvidenceStorageRoute(
                    store=failing_store,
                    provider=EvidenceStorageProvider.S3_COMPATIBLE,
                    scope=EvidenceStorageScope.CLOUD,
                )
            }
        ),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="policy",
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(encoded_bytes=b"failed-clip"),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    triggered_at = datetime(2026, 5, 11, 14, 0, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=triggered_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=triggered_at,
            type="rule.storage_failure",
            scene_contract_hash="b" * 64,
            privacy_manifest_hash="c" * 64,
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="cloud",
                storage_profile_id=profile_id,
            ),
        )
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    artifact = incidents[0]["artifact_payload"]

    assert failing_store.uploads == []
    assert incidents[0]["clip_url"] is None
    assert incidents[0]["storage_bytes"] == 0
    assert "RuntimeError: bucket unavailable" in incidents[0]["payload"]["evidence_storage_error"]
    assert artifact["kind"] is EvidenceArtifactKind.EVENT_CLIP
    assert artifact["status"] is EvidenceArtifactStatus.CAPTURE_FAILED
    assert artifact["storage_provider"] is EvidenceStorageProvider.S3_COMPATIBLE
    assert artifact["storage_scope"] is EvidenceStorageScope.CLOUD
    assert artifact["bucket"] is None
    assert artifact["object_key"].startswith("incidents/")
    assert artifact["content_type"] == "video/x-motion-jpeg"
    assert artifact["sha256"] == hashlib.sha256(b"failed-clip").hexdigest()
    assert artifact["size_bytes"] == len(b"failed-clip")
    assert artifact["triggered_at"] == triggered_at
    assert artifact["scene_contract_hash"] == "b" * 64
    assert artifact["privacy_manifest_hash"] == "c" * 64


@pytest.mark.asyncio
async def test_incident_capture_persists_incident_when_storage_resolution_fails() -> None:
    camera_id = uuid4()
    profile_id = uuid4()

    class _FailingResolver:
        async def resolve(
            self,
            *,
            camera_id: UUID,
            recording_policy: EvidenceRecordingPolicy,
        ) -> EvidenceStorageRoute:
            del camera_id, recording_policy
            raise ValueError("recording policy does not match profile residency")

    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        storage_resolver=_FailingResolver(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="policy",
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(encoded_bytes=b"unrouted-clip"),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    triggered_at = datetime(2026, 5, 11, 14, 30, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=triggered_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=triggered_at,
            type="rule.route_failure",
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="cloud",
                storage_profile_id=profile_id,
            ),
        )
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    artifact = incidents[0]["artifact_payload"]

    assert incidents[0]["clip_url"] is None
    assert incidents[0]["storage_bytes"] == 0
    assert "ValueError: recording policy does not match profile residency" in (
        incidents[0]["payload"]["evidence_storage_error"]
    )
    assert artifact["status"] is EvidenceArtifactStatus.CAPTURE_FAILED
    assert artifact["storage_provider"] is EvidenceStorageProvider.S3_COMPATIBLE
    assert artifact["storage_scope"] is EvidenceStorageScope.CLOUD
    assert artifact["sha256"] == hashlib.sha256(b"unrouted-clip").hexdigest()
