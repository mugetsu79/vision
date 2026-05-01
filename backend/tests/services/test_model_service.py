from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException, status

from argus.api.contracts import ModelCreate, ModelUpdate
from argus.models.enums import DetectorCapability, ModelFormat, ModelTask
from argus.models.tables import Model
from argus.services import app as app_services
from argus.services.app import ModelService

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class _FakeSession:
    def __init__(self, state: dict[str, Model | None]) -> None:
        self.state = state

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    def add(self, model: Model) -> None:
        if model.id is None:
            model.id = uuid4()
        self.state["model"] = model

    async def commit(self) -> None:
        return None

    async def refresh(self, model: Model) -> None:
        return None

    async def get(self, model_cls, model_id):  # noqa: ANN001
        model = self.state["model"]
        if model is not None and model.id == model_id:
            return model
        return None


class _FakeSessionFactory:
    def __init__(self, model: Model | None = None) -> None:
        self.state: dict[str, Model | None] = {"model": model}

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


class _FakeAuditLogger:
    async def record(self, **kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_create_model_uses_embedded_metadata_when_classes_are_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = _FakeSessionFactory()
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())
    calls: list[tuple[str, ModelFormat, list[str] | None]] = []

    def fake_resolve_model_classes(path: str, format: ModelFormat, declared_classes, runtime=None):  # noqa: ANN001
        calls.append((path, format, declared_classes))
        return (["person", "bicycle", "car"], "embedded")

    monkeypatch.setattr(app_services, "resolve_model_classes", fake_resolve_model_classes)

    response = await service.create_model(
        ModelCreate(
            name="Argus YOLO",
            version="1.0.0",
            task=ModelTask.DETECT,
            path="/models/yolo12n.onnx",
            format=ModelFormat.ONNX,
            classes=None,
            input_shape={"width": 640, "height": 640},
            sha256="a" * 64,
            size_bytes=123456,
            license="Apache-2.0",
        )
    )

    assert calls == [("/models/yolo12n.onnx", ModelFormat.ONNX, None)]
    assert response.classes == ["person", "bicycle", "car"]
    assert session_factory.state["model"] is not None
    assert session_factory.state["model"].classes == ["person", "bicycle", "car"]


@pytest.mark.asyncio
async def test_create_open_vocab_model_allows_empty_static_classes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_factory = _FakeSessionFactory()
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())

    def fake_resolve_model_classes(path: str, format: ModelFormat, declared_classes, runtime=None):  # noqa: ANN001
        raise AssertionError("open-vocab models should not use fixed-vocab metadata resolution")

    monkeypatch.setattr(app_services, "resolve_model_classes", fake_resolve_model_classes)

    response = await service.create_model(
        ModelCreate(
            name="YOLO World",
            version="1.0.0",
            task=ModelTask.DETECT,
            path="/models/yolo-world.onnx",
            format=ModelFormat.ONNX,
            capability=DetectorCapability.OPEN_VOCAB,
            capability_config={
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "execution_profiles": ["x86_64_gpu", "arm64_jetson"],
            },
            classes=[],
            input_shape={"width": 640, "height": 640},
            sha256="b" * 64,
            size_bytes=123456,
            license="Apache-2.0",
        )
    )

    assert response.capability == DetectorCapability.OPEN_VOCAB
    assert response.capability_config.supports_runtime_vocabulary_updates is True
    assert response.classes == []
    assert session_factory.state["model"] is not None
    assert session_factory.state["model"].capability == DetectorCapability.OPEN_VOCAB
    assert session_factory.state["model"].classes == []


@pytest.mark.asyncio
async def test_create_open_vocab_ultralytics_model_requires_pt_format() -> None:
    service = ModelService(session_factory=_FakeSessionFactory(), audit_logger=_FakeAuditLogger())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_model(
            ModelCreate(
                name="YOLOE-26N Open Vocab",
                version="2026.1",
                task=ModelTask.DETECT,
                path="/models/yoloe-26n-seg.onnx",
                format=ModelFormat.ONNX,
                capability=DetectorCapability.OPEN_VOCAB,
                capability_config={
                    "supports_runtime_vocabulary_updates": True,
                    "max_runtime_terms": 32,
                    "prompt_format": "labels",
                    "runtime_backend": "ultralytics_yoloe",
                    "model_family": "yoloe",
                    "readiness": "experimental",
                    "requires_gpu": True,
                },
                classes=[],
                input_shape={"width": 640, "height": 640},
                sha256="b" * 64,
                size_bytes=123456,
                license="AGPL-3.0",
            )
        )

    assert exc_info.value.status_code == 422
    assert "requires format=pt" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_create_open_vocab_ultralytics_model_accepts_pt_format() -> None:
    session_factory = _FakeSessionFactory()
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())

    response = await service.create_model(
        ModelCreate(
            name="YOLOE-26N Open Vocab",
            version="2026.1",
            task=ModelTask.DETECT,
            path="/models/yoloe-26n-seg.pt",
            format=ModelFormat.PT,
            capability=DetectorCapability.OPEN_VOCAB,
            capability_config={
                "supports_runtime_vocabulary_updates": True,
                "max_runtime_terms": 32,
                "prompt_format": "labels",
                "runtime_backend": "ultralytics_yoloe",
                "model_family": "yoloe",
                "readiness": "experimental",
                "requires_gpu": True,
                "execution_profiles": ["linux-aarch64-nvidia-jetson", "linux-x86_64-nvidia"],
            },
            classes=[],
            input_shape={"width": 640, "height": 640},
            sha256="c" * 64,
            size_bytes=123456,
            license="AGPL-3.0",
        )
    )

    assert response.format == ModelFormat.PT
    assert response.capability == DetectorCapability.OPEN_VOCAB
    assert response.capability_config.runtime_backend == "ultralytics_yoloe"
    assert session_factory.state["model"] is not None
    assert session_factory.state["model"].classes == []


@pytest.mark.asyncio
async def test_create_engine_model_rejects_ready_tensorrt_backend_until_supported() -> None:
    service = ModelService(session_factory=_FakeSessionFactory(), audit_logger=_FakeAuditLogger())

    with pytest.raises(HTTPException) as exc_info:
        await service.create_model(
            ModelCreate(
                name="YOLO26n TensorRT",
                version="2026.1",
                task=ModelTask.DETECT,
                path="/models/yolo26n.engine",
                format=ModelFormat.ENGINE,
                capability=DetectorCapability.FIXED_VOCAB,
                capability_config={
                    "runtime_backend": "tensorrt_engine",
                    "readiness": "ready",
                    "model_family": "yolo26",
                },
                classes=["person", "car"],
                input_shape={"width": 640, "height": 640},
                sha256="d" * 64,
                size_bytes=123456,
                license="AGPL-3.0",
            )
        )

    assert exc_info.value.status_code == 422
    assert "TensorRT engine detector is not implemented" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_update_model_rejects_class_mismatch_for_self_describing_onnx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(
        id=uuid4(),
        name="Argus YOLO",
        version="1.0.0",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "bicycle", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123456,
        license="Apache-2.0",
    )
    session_factory = _FakeSessionFactory(model=model)
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())

    def fake_resolve_model_classes(path: str, format: ModelFormat, declared_classes, runtime=None):  # noqa: ANN001
        assert path == "/models/yolo12n.onnx"
        assert format is ModelFormat.ONNX
        assert declared_classes == ["person", "car"]
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="Declared classes do not match the embedded ONNX class metadata.",
        )

    monkeypatch.setattr(app_services, "resolve_model_classes", fake_resolve_model_classes)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_model(model.id, ModelUpdate(classes=["person", "car"]))

    assert exc_info.value.status_code == HTTP_422_UNPROCESSABLE
    assert session_factory.state["model"].classes == ["person", "bicycle", "car"]


@pytest.mark.asyncio
async def test_update_model_re_resolves_embedded_classes_when_path_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(
        id=uuid4(),
        name="Argus YOLO",
        version="1.0.0",
        task=ModelTask.DETECT,
        path="/models/yolo12n.onnx",
        format=ModelFormat.ONNX,
        classes=["person", "bicycle", "car"],
        input_shape={"width": 640, "height": 640},
        sha256="a" * 64,
        size_bytes=123456,
        license="Apache-2.0",
    )
    session_factory = _FakeSessionFactory(model=model)
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())
    calls: list[tuple[str, ModelFormat, list[str] | None]] = []

    def fake_resolve_model_classes(path: str, format: ModelFormat, declared_classes, runtime=None):  # noqa: ANN001
        calls.append((path, format, declared_classes))
        return (["person", "car", "truck"], "embedded")

    monkeypatch.setattr(app_services, "resolve_model_classes", fake_resolve_model_classes)

    response = await service.update_model(
        model.id,
        ModelUpdate(path="/models/yolo12n-v2.onnx"),
    )

    assert calls == [("/models/yolo12n-v2.onnx", ModelFormat.ONNX, None)]
    assert response.path == "/models/yolo12n-v2.onnx"
    assert response.classes == ["person", "car", "truck"]


@pytest.mark.asyncio
async def test_update_model_preserves_existing_classes_for_non_onnx_path_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = Model(
        id=uuid4(),
        name="PPE engine",
        version="1.0.0",
        task=ModelTask.ATTRIBUTE,
        path="/models/ppe.engine",
        format=ModelFormat.ENGINE,
        classes=["hard_hat", "hi_vis"],
        input_shape={"width": 224, "height": 224},
        sha256="a" * 64,
        size_bytes=123456,
        license="Apache-2.0",
    )
    session_factory = _FakeSessionFactory(model=model)
    service = ModelService(session_factory=session_factory, audit_logger=_FakeAuditLogger())
    calls: list[tuple[str, ModelFormat, list[str] | None]] = []

    def fake_resolve_model_classes(path: str, format: ModelFormat, declared_classes, runtime=None):  # noqa: ANN001
        calls.append((path, format, declared_classes))
        return (["hard_hat", "hi_vis"], "declared")

    monkeypatch.setattr(app_services, "resolve_model_classes", fake_resolve_model_classes)

    response = await service.update_model(
        model.id,
        ModelUpdate(path="/models/ppe-v2.engine"),
    )

    assert calls == [("/models/ppe-v2.engine", ModelFormat.ENGINE, ["hard_hat", "hi_vis"])]
    assert response.path == "/models/ppe-v2.engine"
    assert response.classes == ["hard_hat", "hi_vis"]
