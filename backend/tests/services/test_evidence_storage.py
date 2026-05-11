from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

from argus.api.contracts import EvidenceRecordingPolicy, WorkerEvidenceStorageSettings
from argus.core.config import Settings
from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceStorageProvider,
    EvidenceStorageScope,
)
from argus.services.evidence_storage import (
    EvidenceStorageRoute,
    LocalFilesystemEvidenceStore,
    S3CompatibleEvidenceStore,
    build_evidence_store,
    resolve_evidence_storage_route,
)
from argus.services.object_store import MinioObjectStore


@pytest.mark.asyncio
async def test_local_filesystem_evidence_store_writes_bytes_and_metadata(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        incident_storage_provider="local_filesystem",
        incident_storage_scope="edge",
        incident_local_storage_root=str(tmp_path),
    )
    store = LocalFilesystemEvidenceStore(settings)

    stored = await store.put_object(
        key="cameras/cam-1/incidents/incident-1/clip.mjpeg",
        data=b"synthetic-clip",
        content_type="video/x-motion-jpeg",
    )

    assert (tmp_path / stored.object_key).read_bytes() == b"synthetic-clip"
    assert stored.provider is EvidenceStorageProvider.LOCAL_FILESYSTEM
    assert stored.scope is EvidenceStorageScope.EDGE
    assert stored.bucket is None
    assert stored.object_key == "cameras/cam-1/incidents/incident-1/clip.mjpeg"
    assert stored.content_type == "video/x-motion-jpeg"
    assert stored.sha256 == hashlib.sha256(b"synthetic-clip").hexdigest()
    assert stored.size_bytes == len(b"synthetic-clip")
    assert stored.review_url is None


@pytest.mark.asyncio
async def test_s3_compatible_evidence_store_preserves_minio_upload_metadata() -> None:
    settings = Settings(
        _env_file=None,
        incident_storage_provider="s3_compatible",
        incident_storage_scope="cloud",
        minio_incidents_bucket="incident-clips",
    )
    object_store = MinioObjectStore(settings)
    fake_client = _FakeMinioClient()
    object_store._client = fake_client  # noqa: SLF001
    store = S3CompatibleEvidenceStore(settings, object_store=object_store)

    stored = await store.put_object(
        key="tenant-a/camera-b/clip.mjpeg",
        data=b"remote-clip",
        content_type="video/x-motion-jpeg",
    )

    assert fake_client.bucket_checks == ["incident-clips"]
    assert fake_client.created_buckets == ["incident-clips"]
    assert fake_client.uploads == [
        (
            "incident-clips",
            "tenant-a/camera-b/clip.mjpeg",
            b"remote-clip",
            "video/x-motion-jpeg",
        )
    ]
    assert stored.provider is EvidenceStorageProvider.S3_COMPATIBLE
    assert stored.scope is EvidenceStorageScope.CLOUD
    assert stored.bucket == "incident-clips"
    assert stored.object_key == "tenant-a/camera-b/clip.mjpeg"
    assert stored.content_type == "video/x-motion-jpeg"
    assert stored.sha256 == hashlib.sha256(b"remote-clip").hexdigest()
    assert stored.size_bytes == len(b"remote-clip")
    assert stored.review_url == "https://minio.local/incident-clips/tenant-a/camera-b/clip.mjpeg"


def test_build_evidence_store_uses_configured_provider(tmp_path) -> None:
    local = build_evidence_store(
        Settings(
            _env_file=None,
            incident_storage_provider="local_filesystem",
            incident_local_storage_root=str(tmp_path),
        )
    )
    remote = build_evidence_store(
        Settings(
            _env_file=None,
            incident_storage_provider="minio",
        )
    )

    assert isinstance(local, LocalFilesystemEvidenceStore)
    assert isinstance(remote, S3CompatibleEvidenceStore)


def test_resolve_evidence_storage_route_maps_ui_managed_profiles(tmp_path) -> None:
    settings = Settings(_env_file=None, incident_local_storage_root=str(tmp_path))
    edge_profile_id = "11111111-1111-1111-1111-111111111111"
    central_profile_id = "22222222-2222-2222-2222-222222222222"
    cloud_profile_id = "33333333-3333-3333-3333-333333333333"
    local_first_profile_id = "44444444-4444-4444-4444-444444444444"

    edge_route = resolve_evidence_storage_route(
        settings,
        recording_policy=EvidenceRecordingPolicy(
            storage_profile="edge_local",
            storage_profile_id=edge_profile_id,
        ),
        profile=WorkerEvidenceStorageSettings(
            profile_id=edge_profile_id,
            profile_name="Edge local evidence",
            profile_hash="a" * 64,
            provider="local_filesystem",
            storage_scope=EvidenceStorageScope.EDGE,
            config={"local_root": str(tmp_path / "edge")},
        ),
    )
    central_route = resolve_evidence_storage_route(
        settings,
        recording_policy=EvidenceRecordingPolicy(
            storage_profile="central",
            storage_profile_id=central_profile_id,
        ),
        profile=WorkerEvidenceStorageSettings(
            profile_id=central_profile_id,
            profile_name="Central MinIO",
            profile_hash="b" * 64,
            provider="minio",
            storage_scope=EvidenceStorageScope.CENTRAL,
            config={
                "endpoint": "minio.local:9000",
                "bucket": "incidents",
                "secure": False,
            },
            secrets={"access_key": "argus", "secret_key": "argus-secret"},
        ),
    )
    cloud_route = resolve_evidence_storage_route(
        settings,
        recording_policy=EvidenceRecordingPolicy(
            storage_profile="cloud",
            storage_profile_id=cloud_profile_id,
        ),
        profile=WorkerEvidenceStorageSettings(
            profile_id=cloud_profile_id,
            profile_name="Cloud S3",
            profile_hash="c" * 64,
            provider="s3_compatible",
            storage_scope=EvidenceStorageScope.CLOUD,
            config={
                "endpoint": "s3.example.com",
                "region": "eu-central-1",
                "bucket": "omnisight-evidence",
                "secure": True,
                "path_prefix": "prod/incidents",
            },
            secrets={"access_key": "cloud-key", "secret_key": "cloud-secret"},
        ),
    )
    local_first_route = resolve_evidence_storage_route(
        settings,
        recording_policy=EvidenceRecordingPolicy(
            storage_profile="local_first",
            storage_profile_id=local_first_profile_id,
        ),
        profile=WorkerEvidenceStorageSettings(
            profile_id=local_first_profile_id,
            profile_name="Local first",
            profile_hash="d" * 64,
            provider="local_first",
            storage_scope=EvidenceStorageScope.EDGE,
            config={"local_root": str(tmp_path / "pending")},
        ),
    )

    assert isinstance(edge_route, EvidenceStorageRoute)
    assert isinstance(edge_route.store, LocalFilesystemEvidenceStore)
    assert edge_route.provider is EvidenceStorageProvider.LOCAL_FILESYSTEM
    assert edge_route.scope is EvidenceStorageScope.EDGE
    assert edge_route.status_override is None
    assert isinstance(central_route.store, S3CompatibleEvidenceStore)
    assert central_route.provider is EvidenceStorageProvider.MINIO
    assert central_route.scope is EvidenceStorageScope.CENTRAL
    assert isinstance(cloud_route.store, S3CompatibleEvidenceStore)
    assert cloud_route.provider is EvidenceStorageProvider.S3_COMPATIBLE
    assert cloud_route.scope is EvidenceStorageScope.CLOUD
    assert isinstance(local_first_route.store, LocalFilesystemEvidenceStore)
    assert local_first_route.provider is EvidenceStorageProvider.LOCAL_FILESYSTEM
    assert local_first_route.scope is EvidenceStorageScope.EDGE
    assert local_first_route.status_override is EvidenceArtifactStatus.UPLOAD_PENDING


def test_resolve_evidence_storage_route_rejects_profile_residency_mismatch(tmp_path) -> None:
    settings = Settings(_env_file=None, incident_local_storage_root=str(tmp_path))

    with pytest.raises(ValueError, match="storage_profile.*does not match"):
        resolve_evidence_storage_route(
            settings,
            recording_policy=EvidenceRecordingPolicy(
                storage_profile="cloud",
                storage_profile_id="22222222-2222-2222-2222-222222222222",
            ),
            profile=WorkerEvidenceStorageSettings(
                profile_id="22222222-2222-2222-2222-222222222222",
                profile_name="Central MinIO",
                profile_hash="b" * 64,
                provider="minio",
                storage_scope=EvidenceStorageScope.CENTRAL,
                config={"endpoint": "minio.local:9000", "bucket": "incidents"},
                secrets={"access_key": "argus", "secret_key": "argus-secret"},
            ),
        )


class _FakeMinioClient:
    def __init__(self) -> None:
        self.bucket_checks: list[str] = []
        self.created_buckets: list[str] = []
        self.uploads: list[tuple[str, str, bytes, str]] = []

    def bucket_exists(self, bucket_name: str) -> bool:
        self.bucket_checks.append(bucket_name)
        return False

    def make_bucket(self, bucket_name: str) -> None:
        self.created_buckets.append(bucket_name)

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        *,
        length: int,
        content_type: str,
    ) -> None:
        payload = data.read(length)
        self.uploads.append((bucket_name, object_name, payload, content_type))

    def presigned_get_object(self, bucket_name: str, object_name: str) -> str:
        return f"https://minio.local/{bucket_name}/{object_name}"
