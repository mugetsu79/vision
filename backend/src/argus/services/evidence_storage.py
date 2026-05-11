from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from argus.core.config import Settings
from argus.models.enums import EvidenceStorageProvider, EvidenceStorageScope
from argus.services.object_store import MinioObjectStore


@dataclass(frozen=True, slots=True)
class StoredEvidenceObject:
    provider: EvidenceStorageProvider
    scope: EvidenceStorageScope
    bucket: str | None
    object_key: str
    content_type: str
    sha256: str
    size_bytes: int
    review_url: str | None = None


class EvidenceObjectStore(Protocol):
    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject: ...


class LocalFilesystemEvidenceStore:
    def __init__(self, settings: Settings) -> None:
        self.root = Path(settings.incident_local_storage_root)
        self.scope = EvidenceStorageScope(settings.incident_storage_scope)

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        object_key = _safe_object_key(key)
        destination = self.root.joinpath(*PurePosixPath(object_key).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return StoredEvidenceObject(
            provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
            scope=self.scope,
            bucket=None,
            object_key=object_key,
            content_type=content_type,
            sha256=_sha256(data),
            size_bytes=len(data),
            review_url=None,
        )


class S3CompatibleEvidenceStore:
    def __init__(
        self,
        settings: Settings,
        *,
        object_store: MinioObjectStore | None = None,
    ) -> None:
        self.settings = settings
        self.object_store = object_store or MinioObjectStore(settings)
        self.provider = _remote_provider(settings)
        self.scope = EvidenceStorageScope(settings.incident_storage_scope)

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        object_key = _safe_object_key(key)
        review_url = await self.object_store.put_object(
            key=object_key,
            data=data,
            content_type=content_type,
        )
        return StoredEvidenceObject(
            provider=self.provider,
            scope=self.scope,
            bucket=self.settings.minio_incidents_bucket,
            object_key=object_key,
            content_type=content_type,
            sha256=_sha256(data),
            size_bytes=len(data),
            review_url=review_url,
        )


def build_evidence_store(settings: Settings) -> EvidenceObjectStore:
    provider = EvidenceStorageProvider(settings.incident_storage_provider)
    if provider is EvidenceStorageProvider.LOCAL_FILESYSTEM:
        return LocalFilesystemEvidenceStore(settings)
    return S3CompatibleEvidenceStore(settings)


def _remote_provider(settings: Settings) -> EvidenceStorageProvider:
    provider = EvidenceStorageProvider(settings.incident_storage_provider)
    if provider is EvidenceStorageProvider.S3_COMPATIBLE:
        return EvidenceStorageProvider.S3_COMPATIBLE
    return EvidenceStorageProvider.MINIO


def _safe_object_key(key: str) -> str:
    path = PurePosixPath(key)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Evidence object keys must be relative paths without traversal.")
    return path.as_posix()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
