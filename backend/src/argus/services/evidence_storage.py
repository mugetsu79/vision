from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from pydantic import SecretStr

from argus.api.contracts import EvidenceRecordingPolicy, WorkerEvidenceStorageSettings
from argus.core.config import Settings
from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
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


@dataclass(frozen=True, slots=True)
class EvidenceStorageRoute:
    store: EvidenceObjectStore
    provider: EvidenceStorageProvider
    scope: EvidenceStorageScope
    status_override: EvidenceArtifactStatus | None = None


class LocalFilesystemEvidenceStore:
    def __init__(
        self,
        settings: Settings,
        *,
        root: str | Path | None = None,
        scope: EvidenceStorageScope | None = None,
        path_prefix: str | None = None,
    ) -> None:
        self.root = Path(root or settings.incident_local_storage_root)
        self.scope = scope or EvidenceStorageScope(settings.incident_storage_scope)
        self.path_prefix = _safe_path_prefix(path_prefix)

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        object_key = _prefixed_object_key(self.path_prefix, key)
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
        provider: EvidenceStorageProvider | None = None,
        scope: EvidenceStorageScope | None = None,
        bucket: str | None = None,
        path_prefix: str | None = None,
    ) -> None:
        self.settings = settings
        self.object_store = object_store or MinioObjectStore(settings)
        self.provider = provider or _remote_provider(settings)
        self.scope = scope or EvidenceStorageScope(settings.incident_storage_scope)
        self.bucket = bucket or settings.minio_incidents_bucket
        self.path_prefix = _safe_path_prefix(path_prefix)

    async def put_object(
        self,
        *,
        key: str,
        data: bytes,
        content_type: str,
    ) -> StoredEvidenceObject:
        object_key = _prefixed_object_key(self.path_prefix, key)
        review_url = await self.object_store.put_object(
            key=object_key,
            data=data,
            content_type=content_type,
        )
        return StoredEvidenceObject(
            provider=self.provider,
            scope=self.scope,
            bucket=self.bucket,
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


def resolve_evidence_storage_route(
    settings: Settings,
    *,
    recording_policy: EvidenceRecordingPolicy,
    profile: WorkerEvidenceStorageSettings,
) -> EvidenceStorageRoute:
    if (
        recording_policy.storage_profile_id is not None
        and profile.profile_id is not None
        and recording_policy.storage_profile_id != profile.profile_id
    ):
        raise ValueError("recording_policy.storage_profile_id does not match evidence profile.")

    provider = str(profile.provider)
    scope = EvidenceStorageScope(profile.storage_scope)
    expected_profile = _storage_profile_for_provider_scope(provider, scope)
    if recording_policy.storage_profile != expected_profile:
        raise ValueError(
            "recording_policy.storage_profile does not match resolved evidence profile "
            f"residency: {recording_policy.storage_profile!r} != {expected_profile!r}."
        )

    if provider == "local_first":
        return EvidenceStorageRoute(
            store=LocalFilesystemEvidenceStore(
                settings,
                root=_string_or_none(profile.config.get("local_root"))
                or settings.incident_local_storage_root,
                scope=EvidenceStorageScope.EDGE,
                path_prefix=_string_or_none(profile.config.get("path_prefix")),
            ),
            provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
            scope=EvidenceStorageScope.EDGE,
            status_override=EvidenceArtifactStatus.UPLOAD_PENDING,
        )
    if provider == EvidenceStorageProvider.LOCAL_FILESYSTEM.value:
        return EvidenceStorageRoute(
            store=LocalFilesystemEvidenceStore(
                settings,
                root=_string_or_none(profile.config.get("local_root"))
                or settings.incident_local_storage_root,
                scope=EvidenceStorageScope.EDGE,
                path_prefix=_string_or_none(profile.config.get("path_prefix")),
            ),
            provider=EvidenceStorageProvider.LOCAL_FILESYSTEM,
            scope=EvidenceStorageScope.EDGE,
        )

    remote_provider = (
        EvidenceStorageProvider.S3_COMPATIBLE
        if provider == EvidenceStorageProvider.S3_COMPATIBLE.value
        else EvidenceStorageProvider.MINIO
    )
    remote_settings = _settings_for_remote_profile(settings, profile, remote_provider, scope)
    return EvidenceStorageRoute(
        store=S3CompatibleEvidenceStore(
            remote_settings,
            provider=remote_provider,
            scope=scope,
            bucket=_string_or_none(profile.config.get("bucket")),
            path_prefix=_string_or_none(profile.config.get("path_prefix")),
        ),
        provider=remote_provider,
        scope=scope,
    )


@dataclass(frozen=True, slots=True)
class ResolvedEvidenceStorageResolver:
    settings: Settings
    evidence_storage: WorkerEvidenceStorageSettings | None

    async def resolve(
        self,
        *,
        camera_id: object,
        recording_policy: EvidenceRecordingPolicy,
    ) -> EvidenceStorageRoute:
        del camera_id
        if self.evidence_storage is None:
            store = build_evidence_store(self.settings)
            provider = (
                EvidenceStorageProvider.LOCAL_FILESYSTEM
                if isinstance(store, LocalFilesystemEvidenceStore)
                else _remote_provider(self.settings)
            )
            return EvidenceStorageRoute(
                store=store,
                provider=provider,
                scope=EvidenceStorageScope(self.settings.incident_storage_scope),
            )
        return resolve_evidence_storage_route(
            self.settings,
            recording_policy=recording_policy,
            profile=self.evidence_storage,
        )


def _remote_provider(settings: Settings) -> EvidenceStorageProvider:
    provider = EvidenceStorageProvider(settings.incident_storage_provider)
    if provider is EvidenceStorageProvider.S3_COMPATIBLE:
        return EvidenceStorageProvider.S3_COMPATIBLE
    return EvidenceStorageProvider.MINIO


def _storage_profile_for_provider_scope(
    provider: str,
    scope: EvidenceStorageScope,
) -> str:
    if provider == "local_first":
        return "local_first"
    if (
        provider == EvidenceStorageProvider.LOCAL_FILESYSTEM.value
        and scope is EvidenceStorageScope.EDGE
    ):
        return "edge_local"
    if provider == EvidenceStorageProvider.MINIO.value and scope is EvidenceStorageScope.CENTRAL:
        return "central"
    if (
        provider == EvidenceStorageProvider.S3_COMPATIBLE.value
        and scope is EvidenceStorageScope.CLOUD
    ):
        return "cloud"
    raise ValueError(
        f"Unsupported evidence storage provider/scope combination: {provider}/{scope.value}."
    )


def _settings_for_remote_profile(
    settings: Settings,
    profile: WorkerEvidenceStorageSettings,
    provider: EvidenceStorageProvider,
    scope: EvidenceStorageScope,
) -> Settings:
    return settings.model_copy(
        update={
            "incident_storage_provider": provider.value,
            "incident_storage_scope": scope.value,
            "minio_endpoint": profile.config.get("endpoint") or settings.minio_endpoint,
            "minio_access_key": profile.secrets.get("access_key", settings.minio_access_key),
            "minio_secret_key": SecretStr(
                profile.secrets.get(
                    "secret_key",
                    settings.minio_secret_key.get_secret_value(),
                )
            ),
            "minio_secure": bool(profile.config.get("secure", settings.minio_secure)),
            "minio_incidents_bucket": (
                _string_or_none(profile.config.get("bucket")) or settings.minio_incidents_bucket
            ),
        }
    )


def _safe_object_key(key: str) -> str:
    path = PurePosixPath(key)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Evidence object keys must be relative paths without traversal.")
    return path.as_posix()


def _safe_path_prefix(prefix: str | None) -> str | None:
    if prefix is None or prefix == "":
        return None
    return _safe_object_key(prefix)


def _prefixed_object_key(prefix: str | None, key: str) -> str:
    object_key = _safe_object_key(key)
    if prefix is None:
        return object_key
    return f"{prefix}/{object_key}"


def _string_or_none(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
