from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

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
from argus.services import app as app_services
from argus.services.model_catalog import ModelCatalogEntry
from argus.services.model_lifecycle import ModelLifecycleService


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _patch_model_class_resolver(
    monkeypatch: pytest.MonkeyPatch,
    classes: list[str] | None = None,
) -> None:
    monkeypatch.setattr(
        app_services,
        "_resolve_model_classes_for_capability",
        lambda **kwargs: list(classes or []),
    )


@pytest.mark.asyncio
async def test_register_master_path_import_creates_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    model_bytes = b"fake-onnx"
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(model_bytes)
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    _patch_model_class_resolver(monkeypatch)

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
async def test_file_import_directory_path_returns_failed_job(tmp_path: Path) -> None:
    tenant_id = uuid4()
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(tmp_path),
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

    assert response.status == ModelLifecycleJobStatus.FAILED
    assert response.model_id is None
    assert response.error is not None
    assert "regular file" in response.error
    assert session_factory.models == []


@pytest.mark.asyncio
async def test_file_import_hash_oserror_persists_failed_job(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake-onnx")
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)

    def raise_permission_denied(path: Path) -> str:
        raise OSError("permission denied")

    monkeypatch.setattr(model_lifecycle, "_hash_file", raise_permission_denied)

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(model_path),
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

    assert response.status == ModelLifecycleJobStatus.FAILED
    assert response.model_id is None
    assert response.error is not None
    assert "permission denied" in response.error
    assert session_factory.models == []
    assert len(session_factory.import_jobs) == 1
    assert session_factory.import_jobs[0].status == ModelLifecycleJobStatus.FAILED


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
    _patch_model_class_resolver(monkeypatch)
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


@pytest.mark.asyncio
async def test_register_catalog_entry_resolves_installed_mount_path_hint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    mounted_models = tmp_path / "models-mount"
    mounted_models.mkdir()
    model_path = mounted_models / "yolo26n.onnx"
    model_path.write_bytes(b"catalog-onnx")
    monkeypatch.setenv("ARGUS_MODEL_CATALOG_MOUNT_DIR", str(mounted_models))
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    resolver_calls: list[list[str] | None] = []

    def fake_resolve_model_classes_for_capability(
        *,
        capability: DetectorCapability,
        path: str,
        format: ModelFormat,
        classes: list[str] | None,
        capability_config: dict[str, object],
    ) -> list[str]:
        assert capability is DetectorCapability.FIXED_VOCAB
        assert path == str(model_path)
        assert format is ModelFormat.ONNX
        assert capability_config["catalog_id"] == "mounted-yolo26n-coco-onnx"
        resolver_calls.append(classes)
        return ["person", "car"]

    monkeypatch.setattr(
        app_services,
        "_resolve_model_classes_for_capability",
        fake_resolve_model_classes_for_capability,
    )
    catalog_entry = ModelCatalogEntry(
        id="mounted-yolo26n-coco-onnx",
        name="Mounted YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path_hint="models/yolo26n.onnx",
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note="Mounted test entry.",
    )
    monkeypatch.setattr(
        model_lifecycle,
        "get_model_catalog_entry",
        lambda catalog_id: catalog_entry if catalog_id == catalog_entry.id else None,
    )

    response = await service.register_catalog_entry(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id="mounted-yolo26n-coco-onnx",
    )

    assert response.status == ModelLifecycleJobStatus.SUCCEEDED
    assert response.observed_sha256 == _sha256(b"catalog-onnx")
    assert response.source_uri == str(model_path)
    assert resolver_calls == [None]
    assert session_factory.models[0].path == str(model_path)
    assert session_factory.models[0].classes == ["person", "car"]


@pytest.mark.asyncio
async def test_repeated_catalog_registration_reuses_existing_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    model_path = tmp_path / "catalog-yolo26n.onnx"
    model_path.write_bytes(b"catalog-onnx")
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    _patch_model_class_resolver(monkeypatch)
    catalog_entry = ModelCatalogEntry(
        id="dedup-yolo26n-coco-onnx",
        name="Dedup YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path_hint=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note="Dedup test entry.",
    )
    monkeypatch.setattr(
        model_lifecycle,
        "get_model_catalog_entry",
        lambda catalog_id: catalog_entry if catalog_id == catalog_entry.id else None,
    )

    first = await service.register_catalog_entry(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id="dedup-yolo26n-coco-onnx",
    )
    second = await service.register_catalog_entry(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id="dedup-yolo26n-coco-onnx",
    )

    assert second.status == ModelLifecycleJobStatus.SUCCEEDED
    assert second.model_id == first.model_id
    assert len(session_factory.models) == 1
    assert len(session_factory.import_jobs) == 2


@pytest.mark.asyncio
async def test_catalog_registration_integrity_error_reloads_existing_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    catalog_id = "race-yolo26n-coco-onnx"
    model_path = tmp_path / "catalog-yolo26n.onnx"
    model_path.write_bytes(b"catalog-onnx")
    existing_model = Model(
        id=uuid4(),
        name="Existing YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config={"catalog_id": catalog_id},
        classes=[],
        input_shape={"width": 640, "height": 640},
        sha256=_sha256(b"catalog-onnx"),
        size_bytes=len(b"catalog-onnx"),
        license="AGPL-3.0",
    )
    session_factory = _CatalogInsertConflictSessionFactory(existing_model)
    service = ModelLifecycleService(session_factory=session_factory)
    _patch_model_class_resolver(monkeypatch)
    catalog_entry = ModelCatalogEntry(
        id=catalog_id,
        name="Race YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path_hint=str(model_path),
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note="Race test entry.",
    )
    monkeypatch.setattr(
        model_lifecycle,
        "get_model_catalog_entry",
        lambda requested_id: catalog_entry if requested_id == catalog_id else None,
    )

    response = await service.register_catalog_entry(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id=catalog_id,
    )

    assert response.status == ModelLifecycleJobStatus.SUCCEEDED
    assert response.model_id == existing_model.id
    assert len(session_factory.models) == 1
    assert session_factory.models[0].id == existing_model.id
    assert len(session_factory.import_jobs) == 1
    assert session_factory.import_jobs[0].status == ModelLifecycleJobStatus.SUCCEEDED
    assert session_factory.rollback_count == 1


@pytest.mark.asyncio
async def test_catalog_download_with_trusted_source_queues_url_job(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    source_url = "https://example.test/yolo26n.onnx"
    expected_sha256 = "a" * 64
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    catalog_entry = ModelCatalogEntry(
        id="trusted-yolo26n-coco-onnx",
        name="Trusted YOLO26n COCO",
        version="2026.1",
        task=ModelTask.DETECT,
        path_hint="models/yolo26n.onnx",
        format=ModelFormat.ONNX,
        capability=DetectorCapability.FIXED_VOCAB,
        capability_config=ModelCapabilityConfig(
            source_url=source_url,
            source_sha256=expected_sha256,
        ),
        classes=(),
        input_shape={"width": 640, "height": 640},
        license="AGPL-3.0",
        note="Trusted downloadable entry.",
    )
    monkeypatch.setattr(
        model_lifecycle,
        "get_model_catalog_entry",
        lambda catalog_id: catalog_entry if catalog_id == catalog_entry.id else None,
    )

    response = await service.queue_catalog_download(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        catalog_id="trusted-yolo26n-coco-onnx",
    )

    assert response.status == ModelLifecycleJobStatus.QUEUED
    assert response.source == ModelImportSource.URL
    assert response.catalog_id == "trusted-yolo26n-coco-onnx"
    assert response.source_uri == source_url
    assert response.expected_sha256 == expected_sha256
    assert response.model_id is None
    assert session_factory.models == []


@pytest.mark.asyncio
async def test_url_import_with_unsafe_filename_returns_failed_job(tmp_path: Path) -> None:
    tenant_id = uuid4()
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(
        session_factory=session_factory,
        model_store_path=tmp_path / "model-store",
    )

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.URL,
            source_uri="https://example.test/%2e%2e",
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

    assert response.status == ModelLifecycleJobStatus.FAILED
    assert response.model_id is None
    assert response.error is not None
    assert "Unsafe model URL filename" in response.error
    assert ".." not in Path(response.target_path).parts
    assert session_factory.models == []


@pytest.mark.asyncio
async def test_file_import_reuses_model_service_class_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    tenant_id = uuid4()
    model_path = tmp_path / "yolo26n.onnx"
    model_path.write_bytes(b"fake-onnx")
    session_factory = _FakeSessionFactory()
    service = ModelLifecycleService(session_factory=session_factory)
    calls: list[
        tuple[DetectorCapability, str, ModelFormat, list[str] | None, dict[str, object]]
    ] = []

    def fake_resolve_model_classes_for_capability(
        *,
        capability: DetectorCapability,
        path: str,
        format: ModelFormat,
        classes: list[str] | None,
        capability_config: dict[str, object],
    ) -> list[str]:
        calls.append((capability, path, format, classes, capability_config))
        return ["person", "car"]

    monkeypatch.setattr(
        app_services,
        "_resolve_model_classes_for_capability",
        fake_resolve_model_classes_for_capability,
    )

    response = await service.import_model_from_request(
        tenant_id=tenant_id,
        actor_subject="admin@example.test",
        payload=ModelImportRequest(
            source=ModelImportSource.MASTER_PATH,
            source_uri=str(model_path),
            expected_sha256=_sha256(b"fake-onnx"),
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
    assert calls == [
        (
            DetectorCapability.FIXED_VOCAB,
            str(model_path),
            ModelFormat.ONNX,
            [],
            ModelCapabilityConfig().model_dump(mode="python"),
        )
    ]
    assert session_factory.models[0].classes == ["person", "car"]


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

    async def execute(self, statement):  # noqa: ANN001
        return _FakeExecuteResult(
            _models_matching_statement(self.session_factory.models, statement)
        )


class _FakeSessionFactory:
    def __init__(self) -> None:
        self.models: list[Model] = []
        self.import_jobs: list[ModelImportJob] = []
        self.commits = 0

    def __call__(self) -> _FakeSession:
        return _FakeSession(self)


class _FakeExecuteResult:
    def __init__(self, rows: list[Model]) -> None:
        self.rows = rows

    def scalars(self) -> _FakeScalarResult:
        return _FakeScalarResult(self.rows)


class _FakeScalarResult:
    def __init__(self, rows: list[Model]) -> None:
        self.rows = rows

    def first(self) -> Model | None:
        return self.rows[0] if self.rows else None

    def all(self) -> list[Model]:
        return self.rows


class _CatalogInsertConflictSessionFactory:
    def __init__(self, existing_model: Model) -> None:
        self.models = [existing_model]
        self.import_jobs: list[ModelImportJob] = []
        self.rollback_count = 0
        self.conflict_raised = False

    def __call__(self) -> _CatalogInsertConflictSession:
        return _CatalogInsertConflictSession(self)


class _CatalogInsertConflictSession:
    def __init__(self, session_factory: _CatalogInsertConflictSessionFactory) -> None:
        self.session_factory = session_factory
        self.pending: list[Model | ModelImportJob] = []

    async def __aenter__(self) -> _CatalogInsertConflictSession:
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
        self.pending.append(row)

    async def commit(self) -> None:
        if not self.session_factory.conflict_raised and any(
            isinstance(row, Model)
            and (row.capability_config or {}).get("catalog_id")
            == (self.session_factory.models[0].capability_config or {}).get("catalog_id")
            for row in self.pending
        ):
            self.session_factory.conflict_raised = True
            raise IntegrityError(
                "duplicate catalog model",
                params=None,
                orig=Exception("unique catalog model"),
            )
        for row in self.pending:
            if isinstance(row, ModelImportJob):
                self.session_factory.import_jobs.append(row)
        self.pending = []

    async def rollback(self) -> None:
        self.session_factory.rollback_count += 1
        self.pending = []

    async def refresh(self, row: Model | ModelImportJob) -> None:
        return None

    async def execute(self, statement):  # noqa: ANN001
        if not self.session_factory.conflict_raised:
            return _FakeExecuteResult([])
        return _FakeExecuteResult(
            _models_matching_statement(self.session_factory.models, statement)
        )


def _models_matching_statement(models: list[Model], statement) -> list[Model]:  # noqa: ANN001
    params = statement.compile().params
    if params.get("capability_config_1") != "catalog_id":
        return models
    catalog_id = params.get("param_1")
    return [
        model
        for model in models
        if (model.capability_config or {}).get("catalog_id") == catalog_id
    ]
