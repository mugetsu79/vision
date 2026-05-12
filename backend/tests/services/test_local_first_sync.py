from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import WorkerEvidenceStorageSettings
from argus.core.config import Settings
from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.services.evidence_storage import StoredEvidenceObject
from argus.services.local_first_sync import (
    LocalFirstEvidenceSyncService,
    LocalFirstPendingArtifact,
)


@pytest.mark.asyncio
async def test_local_first_sync_promotes_pending_artifact_and_records_ledger(
    tmp_path,
) -> None:
    pending = _pending_artifact()
    repository = _FakeSyncRepository([pending])
    ledger = _FakeLedger()
    uploader = _FakeRemoteUploader(
        StoredEvidenceObject(
            provider=EvidenceStorageProvider.MINIO,
            scope=EvidenceStorageScope.CENTRAL,
            bucket="incidents",
            object_key="remote/incidents/camera-1/clip.mjpeg",
            content_type="video/x-motion-jpeg",
            sha256=pending.sha256,
            size_bytes=pending.size_bytes,
            review_url="https://minio.local/incidents/remote/incidents/camera-1/clip.mjpeg",
        )
    )
    service = LocalFirstEvidenceSyncService(
        settings=Settings(_env_file=None, incident_local_storage_root=str(tmp_path)),
        repository=repository,
        ledger=ledger,
        remote_store_factory=lambda profile: uploader,
        local_reader=lambda artifact: b"clip-bytes",
        now=lambda: datetime(2026, 5, 12, 8, 30, tzinfo=UTC),
    )

    summary = await service.sync_pending_artifacts(
        tenant_id=pending.tenant_id,
        remote_profile=_remote_profile(),
    )

    assert summary.processed == 1
    assert summary.promoted == 1
    assert summary.failed == 0
    assert uploader.uploads == [
        ("incidents/camera-1/clip.mjpeg", b"clip-bytes", "video/x-motion-jpeg")
    ]
    assert repository.started == [(pending.artifact_id, _remote_profile().profile_id)]
    assert repository.promoted[pending.artifact_id] == {
        "status": EvidenceArtifactStatus.REMOTE_AVAILABLE,
        "storage_provider": EvidenceStorageProvider.MINIO,
        "storage_scope": EvidenceStorageScope.CENTRAL,
        "bucket": "incidents",
        "object_key": "remote/incidents/camera-1/clip.mjpeg",
        "review_url": "https://minio.local/incidents/remote/incidents/camera-1/clip.mjpeg",
    }
    assert [entry["action"] for entry in ledger.entries] == [
        EvidenceLedgerAction.EVIDENCE_UPLOAD_STARTED,
        EvidenceLedgerAction.EVIDENCE_UPLOAD_AVAILABLE,
    ]
    available_payload = ledger.entries[-1]["payload"]
    assert available_payload["original_object_key"] == "incidents/camera-1/clip.mjpeg"
    assert available_payload["remote_object_key"] == "remote/incidents/camera-1/clip.mjpeg"
    assert available_payload["sha256"] == pending.sha256


@pytest.mark.asyncio
async def test_local_first_sync_keeps_local_artifact_pending_when_upload_fails(
    tmp_path,
) -> None:
    pending = _pending_artifact()
    repository = _FakeSyncRepository([pending])
    ledger = _FakeLedger()
    uploader = _FailingRemoteUploader(RuntimeError("bucket unavailable"))
    service = LocalFirstEvidenceSyncService(
        settings=Settings(_env_file=None, incident_local_storage_root=str(tmp_path)),
        repository=repository,
        ledger=ledger,
        remote_store_factory=lambda profile: uploader,
        local_reader=lambda artifact: b"clip-bytes",
        now=lambda: datetime(2026, 5, 12, 8, 30, tzinfo=UTC),
    )

    summary = await service.sync_pending_artifacts(
        tenant_id=pending.tenant_id,
        remote_profile=_remote_profile(),
    )

    assert summary.processed == 1
    assert summary.promoted == 0
    assert summary.failed == 1
    assert pending.artifact_id not in repository.promoted
    assert repository.failures[pending.artifact_id] == "RuntimeError: bucket unavailable"
    assert [entry["action"] for entry in ledger.entries] == [
        EvidenceLedgerAction.EVIDENCE_UPLOAD_STARTED,
        EvidenceLedgerAction.EVIDENCE_UPLOAD_FAILED,
    ]
    failed_payload = ledger.entries[-1]["payload"]
    assert failed_payload["object_key"] == "incidents/camera-1/clip.mjpeg"
    assert failed_payload["error"] == "RuntimeError: bucket unavailable"


@pytest.mark.asyncio
async def test_local_first_sync_is_idempotent_after_promotion(tmp_path) -> None:
    pending = _pending_artifact()
    repository = _FakeSyncRepository([pending])
    uploader = _FakeRemoteUploader(
        StoredEvidenceObject(
            provider=EvidenceStorageProvider.S3_COMPATIBLE,
            scope=EvidenceStorageScope.CLOUD,
            bucket="cloud-incidents",
            object_key="cloud/incidents/camera-1/clip.mjpeg",
            content_type="video/x-motion-jpeg",
            sha256=pending.sha256,
            size_bytes=pending.size_bytes,
            review_url="https://s3.local/cloud/incidents/camera-1/clip.mjpeg",
        )
    )
    service = LocalFirstEvidenceSyncService(
        settings=Settings(_env_file=None, incident_local_storage_root=str(tmp_path)),
        repository=repository,
        ledger=_FakeLedger(),
        remote_store_factory=lambda profile: uploader,
        local_reader=lambda artifact: b"clip-bytes",
    )

    first = await service.sync_pending_artifacts(
        tenant_id=pending.tenant_id,
        remote_profile=_remote_profile(provider=EvidenceStorageProvider.S3_COMPATIBLE),
    )
    second = await service.sync_pending_artifacts(
        tenant_id=pending.tenant_id,
        remote_profile=_remote_profile(provider=EvidenceStorageProvider.S3_COMPATIBLE),
    )

    assert first.promoted == 1
    assert second.processed == 0
    assert uploader.call_count == 1


def _pending_artifact() -> LocalFirstPendingArtifact:
    payload = b"clip-bytes"
    return LocalFirstPendingArtifact(
        tenant_id=uuid4(),
        incident_id=uuid4(),
        camera_id=uuid4(),
        artifact_id=uuid4(),
        object_key="incidents/camera-1/clip.mjpeg",
        content_type="video/x-motion-jpeg",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
    )


def _remote_profile(
    *,
    provider: EvidenceStorageProvider = EvidenceStorageProvider.MINIO,
) -> WorkerEvidenceStorageSettings:
    scope = (
        EvidenceStorageScope.CLOUD
        if provider is EvidenceStorageProvider.S3_COMPATIBLE
        else EvidenceStorageScope.CENTRAL
    )
    return WorkerEvidenceStorageSettings(
        profile_id="22222222-2222-2222-2222-222222222222",
        profile_name="Remote evidence",
        profile_hash="b" * 64,
        provider=provider,
        storage_scope=scope,
        config={"bucket": "incidents", "endpoint": "minio.local:9000"},
        secrets={"access_key": "argus", "secret_key": "argus-secret"},
    )


class _FakeSyncRepository:
    def __init__(self, pending: list[LocalFirstPendingArtifact]) -> None:
        self.pending = pending
        self.started: list[tuple[UUID, UUID | None]] = []
        self.promoted: dict[UUID, dict[str, object]] = {}
        self.failures: dict[UUID, str] = {}

    async def list_pending(
        self,
        *,
        tenant_id: UUID,
        limit: int,
    ) -> list[LocalFirstPendingArtifact]:
        del limit
        return [
            artifact
            for artifact in self.pending
            if artifact.tenant_id == tenant_id and artifact.artifact_id not in self.promoted
        ]

    async def mark_upload_started(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        remote_profile_id: UUID | None,
        attempted_at: datetime,
    ) -> None:
        del attempted_at
        self.started.append((artifact.artifact_id, remote_profile_id))

    async def mark_upload_available(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        stored_object: StoredEvidenceObject,
        completed_at: datetime,
    ) -> None:
        del completed_at
        self.promoted[artifact.artifact_id] = {
            "status": EvidenceArtifactStatus.REMOTE_AVAILABLE,
            "storage_provider": stored_object.provider,
            "storage_scope": stored_object.scope,
            "bucket": stored_object.bucket,
            "object_key": stored_object.object_key,
            "review_url": stored_object.review_url,
        }

    async def mark_upload_failed(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        error: str,
        attempted_at: datetime,
    ) -> None:
        del attempted_at
        self.failures[artifact.artifact_id] = error


class _FakeLedger:
    def __init__(self) -> None:
        self.entries: list[dict[str, object]] = []

    async def append_entry(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
        camera_id: UUID,
        action: EvidenceLedgerAction,
        actor_type: str,
        actor_subject: str | None = None,
        occurred_at: datetime | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.entries.append(
            {
                "tenant_id": tenant_id,
                "incident_id": incident_id,
                "camera_id": camera_id,
                "action": action,
                "actor_type": actor_type,
                "actor_subject": actor_subject,
                "occurred_at": occurred_at,
                "payload": payload or {},
            }
        )


@dataclass
class _FakeRemoteUploader:
    stored_object: StoredEvidenceObject
    call_count: int = 0

    def __post_init__(self) -> None:
        self.uploads: list[tuple[str, bytes, str]] = []

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        self.call_count += 1
        self.uploads.append((key, data, content_type))
        return self.stored_object


@dataclass
class _FailingRemoteUploader:
    exc: Exception

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        del key, data, content_type
        raise self.exc
