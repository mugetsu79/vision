from __future__ import annotations

import hashlib
from io import BytesIO

import pytest

from argus.core.config import Settings
from argus.models.enums import EvidenceStorageProvider, EvidenceStorageScope
from argus.services.evidence_storage import (
    LocalFilesystemEvidenceStore,
    S3CompatibleEvidenceStore,
    build_evidence_store,
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
