from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

import argus.services.model_lifecycle as model_lifecycle
from argus.api.contracts import ModelCapabilityConfig, ModelImportRequest
from argus.compat import UTC
from argus.models.enums import (
    DetectorCapability,
    ModelFormat,
    ModelImportSource,
    ModelLifecycleJobStatus,
    ModelTask,
)
from argus.models.tables import Model, ModelImportJob
from argus.services.model_catalog import ModelCatalogEntry
from argus.services.model_lifecycle import ModelLifecycleService


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.asyncio
async def test_register_master_path_import_creates_model(tmp_path: Path) -> None:
    tenant_id = uuid4()
    model_bytes = b"fake-onnx"
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(model_bytes)
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(model_path),
            expected_sha256=_sha256(model_bytes),
            name="YOLO26n COCO",
            version="2026.1",
            task=ModelTask.DETECT,
            format=ModelFormat.ONNX,
            capability=DetectorCapability.FIXED_VOCAB,
            input_shape={"width": 640, "height": 640},
            classes=[],
            license="AGPL-3.0",
        ),
    )

    assert response.status == ModelLifecycleJobStatus.SUCCEEDED
    assert response.model_id is not None
    assert response.observed_sha256 == _sha256(model_bytes)
    assert response.size_bytes == len(model_bytes)
    assert len(session_factory.models) == 1
    assert session_factory.models[0].sha256 == _sha256(model_bytes)
    assert len(session_factory.import_jobs) == 1
    assert session_factory.import_jobs[0].model_id == response.model_id


@pytest.mark.asyncio
async def test_url_import_queues_job_without_downloading() -> None:
    tenant_id = uuid4()
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.URL,
            source_uri="https://models.example.test/yolo26n.onnx",
            expected_sha256="a" * 64,
            name="YOLO26n COCO",
            version="2026.1",
            task=ModelTask.DETECT,
            format=ModelFormat.ONNX,
            capability=DetectorCapability.FIXED_VOCAB,
            input_shape={"width": 640, "height": 640},
            classes=[],
            license="AGPL-3.0",
        ),
    )

    assert response.status == ModelLifecycleJobStatus.QUEUED
    assert response.source == ModelImportSource.URL
    assert response.model_id is None
    assert response.observed_sha256 is None
    assert session_factory.models == []
    assert len(session_factory.import_jobs) == 1
    assert session_factory.import_jobs[0].source_uri == "https://models.example.test/yolo26n.onnx"


@pytest.mark.asyncio
async def test_file_import_hash_mismatch_returns_failed_job(tmp_path: Path) -> None:
    tenant_id = uuid4()
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake-onnx")
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(model_path),
            expected_sha256="b" * 64,
            name="YOLO26n COCO",
            version="2026.1",
            task=ModelTask.DETECT,
            format=ModelFormat.ONNX,
            capability=DetectorCapability.FIXED_VOCAB,
            input_shape={"width": 640, "height": 640},
            classes=[],
            license="AGPL-3.0",
        ),
    )

    assert response.status == ModelLifecycleJobStatus.FAILED
    assert response.model_id is None
    assert response.observed_sha256 == _sha256(b"fake-onnx")
    assert response.error is not None
    assert "sha256 mismatch" in response.error
    assert session_factory.models == []


@pytest.mark.asyncio
async def test_register_catalog_entry_resolves_path_hint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    model_path = tmp_path / "catalog-yolo26n.onnx"
    model_path.write_bytes(b"catalog-onnx")
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    catalog_entry = ModelCatalogEntry(
        id="test-yolo26n-coco-onnx",
        name="Test YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path_hint=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note="Test entry.",
    )
    monkeypatch.setattr(
        model_lifecycle,
        "get_model_catalog_entry",
        lambda catalog_id: catalog_entry if catalog_id == catalog_entry.id else None,
    )

    response = await service.register_catalog_entry(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id="test-yolo26n-coco-onnx",
    )

    assert response.status == ModelLifecycleJobStatus.SUCCEEDED
    assert response.catalog_id == "test-yolo26n-coco-onnx"
    assert response.source == ModelImportSource.CATALOG
    assert response.model_id is not None
    assert response.observed_sha256 == _sha256(b"catalog-onnx")
    assert session_factory.models[0].capability_config["catalog_id"] == "test-yolo26n-coco-onnx"


class _FakeSession:
    def __init__(self, session_factory: _FakeSessionFactory) -> None:
        self.session_factory = session_factory

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, row: Model | ModelImportJob) -> None:
        if row.id is None:
            row.id = uuid4()
        if isinstance(row, ModelImportJob):
            now = datetime.now(UTC)
            if row.created_at is None:
                row.created_at = now
            if row.updated_at is None:
                row.updated_at = now
            self.session_factory.import_jobs.append(row)
            return
        self.session_factory.models.append(row)

    async def commit(self) -> None:
        self.session_factory.commits += 1

    async def refresh(self, row: Model | ModelImportJob) -> None:
        return None


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.models: list[Model] = []
        self.import_jobs: list[ModelImportJob] = []
        self.commits = 0

    def __call__(self) -> _FakeSession:
        return _FakeSession(self)
