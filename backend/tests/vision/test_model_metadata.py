from __future__ import annotations

import pytest
from fastapi import HTTPException

from argus.models.enums import ModelFormat
from argus.vision.model_metadata import extract_onnx_classes, resolve_model_classes


class _FakeModelMeta:
    def __init__(self, custom_metadata_map: dict[str, str]) -> None:
        self.custom_metadata_map = custom_metadata_map


class _FakeSession:
    def __init__(self, metadata: dict[str, str]) -> None:
        self._meta = _FakeModelMeta(metadata)

    def get_modelmeta(self) -> _FakeModelMeta:
        return self._meta


class _FakeRuntime:
    def __init__(self, metadata: dict[str, str]) -> None:
        self._metadata = metadata

    def InferenceSession(self, path: str, providers: list[str]) -> _FakeSession:  # noqa: N802
        assert path == "/models/yolo12n.onnx"
        assert providers == ["CPUExecutionProvider"]
        return _FakeSession(self._metadata)


def test_extract_onnx_classes_reads_embedded_dict_metadata() -> None:
    runtime = _FakeRuntime({"names": "{0: 'person', 1: 'bicycle', 2: 'car'}"})
    assert extract_onnx_classes("/models/yolo12n.onnx", runtime=runtime) == [
        "person",
        "bicycle",
        "car",
    ]


def test_extract_onnx_classes_sorts_numeric_string_keys_numerically() -> None:
    runtime = _FakeRuntime({"names": '{"10": "truck", "2": "car", "0": "person"}'})
    assert extract_onnx_classes("/models/yolo12n.onnx", runtime=runtime) == [
        "person",
        "car",
        "truck",
    ]


def test_extract_onnx_classes_returns_none_without_names() -> None:
    runtime = _FakeRuntime({})
    assert extract_onnx_classes("/models/yolo12n.onnx", runtime=runtime) is None


def test_resolve_model_classes_uses_embedded_metadata_when_classes_are_omitted() -> None:
    runtime = _FakeRuntime({"names": "{0: 'person', 1: 'bicycle', 2: 'car'}"})
    assert resolve_model_classes(
        "/models/yolo12n.onnx",
        ModelFormat.ONNX,
        None,
        runtime,
    ) == (["person", "bicycle", "car"], "embedded")


def test_resolve_model_classes_rejects_mismatch_for_self_describing_onnx() -> None:
    runtime = _FakeRuntime({"names": "{0: 'person', 1: 'bicycle', 2: 'car'}"})
    with pytest.raises(HTTPException) as exc_info:
        resolve_model_classes(
            "/models/yolo12n.onnx",
            ModelFormat.ONNX,
            ["person", "car"],
            runtime,
        )

    assert exc_info.value.status_code == 422


def test_resolve_model_classes_preserves_explicit_empty_declared_list_for_onnx() -> None:
    runtime = _FakeRuntime({})
    assert resolve_model_classes(
        "/models/yolo12n.onnx",
        ModelFormat.ONNX,
        [],
        runtime,
    ) == ([], "declared")


def test_resolve_model_classes_requires_declared_classes_for_non_onnx_models() -> None:
    with pytest.raises(HTTPException) as exc_info:
        resolve_model_classes(
            "/models/model.engine",
            ModelFormat.ENGINE,
            None,
        )

    assert exc_info.value.status_code == 422
