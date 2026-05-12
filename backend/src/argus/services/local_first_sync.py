from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import EvidenceRecordingPolicy, WorkerEvidenceStorageSettings
from argus.compat import UTC
from argus.core.config import Settings
from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.models.tables import (
    Camera,
    EvidenceArtifact,
    Incident,
    LocalFirstSyncAttempt,
    Site,
)
from argus.services.evidence_ledger import EvidenceLedgerService
from argus.services.evidence_storage import (
    EvidenceObjectStore,
    StoredEvidenceObject,
    resolve_evidence_storage_route,
    resolve_local_evidence_path,
)


@dataclass(frozen=True, slots=True)
class LocalFirstPendingArtifact:
    tenant_id: UUID
    incident_id: UUID
    camera_id: UUID
    artifact_id: UUID
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class LocalFirstSyncResult:
    artifact_id: UUID
    status: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class LocalFirstSyncSummary:
    processed: int = 0
    promoted: int = 0
    failed: int = 0
    results: list[LocalFirstSyncResult] = field(default_factory=list)


class LocalFirstSyncRepository(Protocol):
    async def list_pending(
        self,
        *,
        tenant_id: UUID,
        limit: int,
    ) -> list[LocalFirstPendingArtifact]: ...

    async def mark_upload_started(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        remote_profile_id: UUID | None,
        attempted_at: datetime,
    ) -> None: ...

    async def mark_upload_available(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        stored_object: StoredEvidenceObject,
        completed_at: datetime,
    ) -> None: ...

    async def mark_upload_failed(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        error: str,
        attempted_at: datetime,
    ) -> None: ...


class EvidenceLedgerWriter(Protocol):
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
    ) -> object: ...


RemoteStoreFactory = Callable[[WorkerEvidenceStorageSettings], EvidenceObjectStore]
LocalArtifactReader = Callable[[LocalFirstPendingArtifact], bytes]
Clock = Callable[[], datetime]


class LocalFirstEvidenceSyncService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: LocalFirstSyncRepository | None = None,
        ledger: EvidenceLedgerWriter | None = None,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        remote_store_factory: RemoteStoreFactory | None = None,
        local_reader: LocalArtifactReader | None = None,
        now: Clock | None = None,
    ) -> None:
        if repository is None:
            if session_factory is None:
                raise ValueError("session_factory is required when repository is not supplied.")
            repository = SQLLocalFirstSyncRepository(session_factory)
        if ledger is None:
            if session_factory is None:
                raise ValueError("session_factory is required when ledger is not supplied.")
            ledger = EvidenceLedgerService(session_factory)
        self.settings = settings
        self.repository = repository
        self.ledger = ledger
        self.remote_store_factory = remote_store_factory or self._build_remote_store
        self.local_reader = local_reader or self._read_local_artifact
        self.now = now or (lambda: datetime.now(tz=UTC))

    async def sync_pending_artifacts(
        self,
        *,
        tenant_id: UUID,
        remote_profile: WorkerEvidenceStorageSettings,
        limit: int = 50,
    ) -> LocalFirstSyncSummary:
        pending = await self.repository.list_pending(tenant_id=tenant_id, limit=limit)
        results: list[LocalFirstSyncResult] = []
        promoted = 0
        failed = 0
        store = self.remote_store_factory(remote_profile)
        remote_profile_id = remote_profile.profile_id

        for artifact in pending:
            attempted_at = self.now()
            await self.repository.mark_upload_started(
                artifact=artifact,
                remote_profile_id=remote_profile_id,
                attempted_at=attempted_at,
            )
            await self._append_ledger(
                artifact,
                EvidenceLedgerAction.EVIDENCE_UPLOAD_STARTED,
                occurred_at=attempted_at,
                payload={
                    "artifact_id": artifact.artifact_id,
                    "object_key": artifact.object_key,
                    "remote_profile_id": remote_profile_id,
                    "remote_profile_hash": remote_profile.profile_hash,
                },
            )

            try:
                data = self.local_reader(artifact)
                stored_object = await store.put_object(
                    key=artifact.object_key,
                    data=data,
                    content_type=artifact.content_type,
                )
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
                failed += 1
                await self.repository.mark_upload_failed(
                    artifact=artifact,
                    error=error,
                    attempted_at=attempted_at,
                )
                await self._append_ledger(
                    artifact,
                    EvidenceLedgerAction.EVIDENCE_UPLOAD_FAILED,
                    occurred_at=attempted_at,
                    payload={
                        "artifact_id": artifact.artifact_id,
                        "object_key": artifact.object_key,
                        "remote_profile_id": remote_profile_id,
                        "error": error,
                    },
                )
                results.append(
                    LocalFirstSyncResult(
                        artifact_id=artifact.artifact_id,
                        status="failed",
                        error=error,
                    )
                )
                continue

            completed_at = self.now()
            promoted += 1
            await self.repository.mark_upload_available(
                artifact=artifact,
                stored_object=stored_object,
                completed_at=completed_at,
            )
            await self._append_ledger(
                artifact,
                EvidenceLedgerAction.EVIDENCE_UPLOAD_AVAILABLE,
                occurred_at=completed_at,
                payload={
                    "artifact_id": artifact.artifact_id,
                    "original_object_key": artifact.object_key,
                    "remote_object_key": stored_object.object_key,
                    "remote_profile_id": remote_profile_id,
                    "storage_provider": stored_object.provider,
                    "storage_scope": stored_object.scope,
                    "bucket": stored_object.bucket,
                    "sha256": stored_object.sha256,
                    "size_bytes": stored_object.size_bytes,
                    "review_url": stored_object.review_url,
                },
            )
            results.append(
                LocalFirstSyncResult(
                    artifact_id=artifact.artifact_id,
                    status="promoted",
                )
            )

        return LocalFirstSyncSummary(
            processed=len(pending),
            promoted=promoted,
            failed=failed,
            results=results,
        )

    async def _append_ledger(
        self,
        artifact: LocalFirstPendingArtifact,
        action: EvidenceLedgerAction,
        *,
        occurred_at: datetime,
        payload: dict[str, object],
    ) -> None:
        await self.ledger.append_entry(
            tenant_id=artifact.tenant_id,
            incident_id=artifact.incident_id,
            camera_id=artifact.camera_id,
            action=action,
            actor_type="system",
            actor_subject=None,
            occurred_at=occurred_at,
            payload=payload,
        )

    def _build_remote_store(self, profile: WorkerEvidenceStorageSettings) -> EvidenceObjectStore:
        if str(profile.provider) in {
            "local_first",
            EvidenceStorageProvider.LOCAL_FILESYSTEM.value,
        }:
            raise ValueError("Local-first sync remote profile must resolve to remote storage.")
        scope = EvidenceStorageScope(profile.storage_scope)
        storage_profile = "cloud" if scope is EvidenceStorageScope.CLOUD else "central"
        route = resolve_evidence_storage_route(
            self.settings,
            recording_policy=EvidenceRecordingPolicy(
                storage_profile=storage_profile,
                storage_profile_id=profile.profile_id,
            ),
            profile=profile,
        )
        if route.provider is EvidenceStorageProvider.LOCAL_FILESYSTEM:
            raise ValueError("Local-first sync remote profile must resolve to remote storage.")
        return route.store

    def _read_local_artifact(self, artifact: LocalFirstPendingArtifact) -> bytes:
        return resolve_local_evidence_path(self.settings, artifact.object_key).read_bytes()


class SQLLocalFirstSyncRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_pending(
        self,
        *,
        tenant_id: UUID,
        limit: int,
    ) -> list[LocalFirstPendingArtifact]:
        async with self.session_factory() as session:
            statement = (
                select(EvidenceArtifact, Incident, Site)
                .join(Incident, Incident.id == EvidenceArtifact.incident_id)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_id)
                .where(EvidenceArtifact.status == EvidenceArtifactStatus.UPLOAD_PENDING)
                .where(
                    EvidenceArtifact.storage_provider
                    == EvidenceStorageProvider.LOCAL_FILESYSTEM
                )
                .where(EvidenceArtifact.storage_scope == EvidenceStorageScope.EDGE)
                .order_by(EvidenceArtifact.created_at.asc())
                .limit(limit)
            )
            rows = (await session.execute(statement)).all()
        return [
            LocalFirstPendingArtifact(
                tenant_id=site.tenant_id,
                incident_id=incident.id,
                camera_id=artifact.camera_id,
                artifact_id=artifact.id,
                object_key=artifact.object_key,
                content_type=artifact.content_type,
                sha256=artifact.sha256,
                size_bytes=artifact.size_bytes,
            )
            for artifact, incident, site in rows
        ]

    async def mark_upload_started(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        remote_profile_id: UUID | None,
        attempted_at: datetime,
    ) -> None:
        async with self.session_factory() as session:
            attempt = await self._get_or_create_attempt(
                session,
                artifact=artifact,
                remote_profile_id=remote_profile_id,
            )
            attempt.attempt_count += 1
            attempt.latest_status = "uploading"
            attempt.latest_error = None
            attempt.last_attempted_at = attempted_at
            attempt.completed_at = None
            await session.commit()

    async def mark_upload_available(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        stored_object: StoredEvidenceObject,
        completed_at: datetime,
    ) -> None:
        async with self.session_factory() as session:
            row = await session.get(EvidenceArtifact, artifact.artifact_id)
            if row is None:
                return
            row.status = EvidenceArtifactStatus.REMOTE_AVAILABLE
            row.storage_provider = stored_object.provider
            row.storage_scope = stored_object.scope
            row.bucket = stored_object.bucket
            row.object_key = stored_object.object_key
            row.content_type = stored_object.content_type
            row.sha256 = stored_object.sha256
            row.size_bytes = stored_object.size_bytes
            incident = await session.get(Incident, artifact.incident_id)
            if incident is not None:
                incident.clip_url = stored_object.review_url
                incident.storage_bytes = stored_object.size_bytes
            attempt = await self._get_or_create_attempt(
                session,
                artifact=artifact,
                remote_profile_id=None,
            )
            attempt.latest_status = "remote_available"
            attempt.latest_error = None
            attempt.completed_at = completed_at
            await session.commit()

    async def mark_upload_failed(
        self,
        *,
        artifact: LocalFirstPendingArtifact,
        error: str,
        attempted_at: datetime,
    ) -> None:
        async with self.session_factory() as session:
            attempt = await self._get_or_create_attempt(
                session,
                artifact=artifact,
                remote_profile_id=None,
            )
            attempt.latest_status = "failed"
            attempt.latest_error = error
            attempt.last_attempted_at = attempted_at
            attempt.completed_at = None
            await session.commit()

    async def _get_or_create_attempt(
        self,
        session: AsyncSession,
        *,
        artifact: LocalFirstPendingArtifact,
        remote_profile_id: UUID | None,
    ) -> LocalFirstSyncAttempt:
        statement = select(LocalFirstSyncAttempt).where(
            LocalFirstSyncAttempt.artifact_id == artifact.artifact_id
        )
        attempt = (await session.execute(statement)).scalar_one_or_none()
        if attempt is not None:
            if remote_profile_id is not None:
                attempt.remote_profile_id = remote_profile_id
            return attempt
        attempt = LocalFirstSyncAttempt(
            tenant_id=artifact.tenant_id,
            artifact_id=artifact.artifact_id,
            remote_profile_id=remote_profile_id,
            attempt_count=0,
            latest_status="pending",
        )
        session.add(attempt)
        await session.flush()
        return attempt
