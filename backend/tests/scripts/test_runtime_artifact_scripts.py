from __future__ import annotations

import hashlib

from argus.scripts.build_runtime_artifact import (
    build_fixed_vocab_artifact_payload,
    build_open_vocab_scene_artifact_payloads,
    post_json,
    sha256_file,
)
from argus.scripts.validate_runtime_artifact import build_validation_patch, patch_json
from argus.vision.vocabulary import hash_vocabulary


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, *, headers: dict[str, str], json: dict[str, object], timeout: int):
        self.calls.append({"method": "POST", "url": url, "headers": headers, "json": json})
        return _FakeResponse({"id": "artifact-1", **json})

    def patch(self, url: str, *, headers: dict[str, str], json: dict[str, object], timeout: int):
        self.calls.append({"method": "PATCH", "url": url, "headers": headers, "json": json})
        return _FakeResponse({"id": "artifact-1", **json})


def test_fixed_vocab_build_payload_computes_hash_and_posts_artifact(tmp_path) -> None:
    source = tmp_path / "yolo26n.onnx"
    source.write_bytes(b"source-model")
    engine = tmp_path / "yolo26n.engine"
    engine.write_bytes(b"engine")
    model_id = "11111111-1111-4111-8111-111111111111"
    client = _FakeClient()

    payload = build_fixed_vocab_artifact_payload(
        source_model_path=source,
        prebuilt_engine_path=engine,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        target_profile="linux-aarch64-nvidia-jetson",
        build_duration_seconds=1.25,
    )
    response = post_json(
        f"http://api.local/api/v1/models/{model_id}/runtime-artifacts",
        "token",
        payload,
        client=client,
    )

    assert payload["scope"] == "model"
    assert payload["kind"] == "tensorrt_engine"
    assert payload["capability"] == "fixed_vocab"
    assert payload["runtime_backend"] == "tensorrt_engine"
    assert payload["source_model_sha256"] == hashlib.sha256(b"source-model").hexdigest()
    assert payload["sha256"] == hashlib.sha256(b"engine").hexdigest()
    assert payload["size_bytes"] == 6
    assert response["id"] == "artifact-1"
    assert client.calls[0]["method"] == "POST"


def test_open_vocab_build_payload_exports_scene_artifacts_with_vocabulary_hash(tmp_path) -> None:
    source = tmp_path / "yoloe-26n-seg.pt"
    source.write_bytes(b"open-vocab-source")
    events: list[tuple[str, object]] = []

    class _FakeYOLOE:
        def __init__(self, path: str) -> None:
            events.append(("load", path))

        def set_classes(self, classes: list[str]) -> None:
            events.append(("set_classes", list(classes)))

        def export(self, *, format: str) -> str:  # noqa: A002
            events.append(("export", format))
            exported = tmp_path / f"scene.{format if format == 'onnx' else 'engine'}"
            exported.write_bytes(format.encode())
            return str(exported)

    payloads = build_open_vocab_scene_artifact_payloads(
        source_model_path=source,
        camera_id="22222222-2222-4222-8222-222222222222",
        runtime_vocabulary=[" person ", "chair", ""],
        export_formats=["onnx", "engine"],
        input_shape={"width": 640, "height": 640},
        target_profile="linux-aarch64-nvidia-jetson",
        vocabulary_version=9,
        yoloe_loader=_FakeYOLOE,
    )

    vocabulary_hash = hash_vocabulary(["person", "chair"])

    assert events == [
        ("load", str(source)),
        ("set_classes", ["person", "chair"]),
        ("export", "onnx"),
        ("export", "engine"),
    ]
    assert [payload["kind"] for payload in payloads] == ["onnx_export", "tensorrt_engine"]
    assert [payload["runtime_backend"] for payload in payloads] == [
        "onnxruntime",
        "tensorrt_engine",
    ]
    assert {payload["scope"] for payload in payloads} == {"scene"}
    assert {payload["capability"] for payload in payloads} == {"open_vocab"}
    assert {payload["camera_id"] for payload in payloads} == {
        "22222222-2222-4222-8222-222222222222"
    }
    assert {payload["vocabulary_hash"] for payload in payloads} == {vocabulary_hash}
    assert {payload["vocabulary_version"] for payload in payloads} == {9}
    assert {tuple(payload["classes"]) for payload in payloads} == {("person", "chair")}
    assert all(payload["build_duration_seconds"] is not None for payload in payloads)


def test_validate_runtime_artifact_patches_valid_when_file_hash_matches(tmp_path) -> None:
    artifact = tmp_path / "yolo26n.engine"
    artifact.write_bytes(b"engine")
    client = _FakeClient()

    payload = build_validation_patch(
        artifact_path=artifact,
        expected_sha256=sha256_file(artifact),
        target_profile="linux-aarch64-nvidia-jetson",
        host_profile="linux-aarch64-nvidia-jetson",
    )
    response = patch_json(
        "http://api.local/api/v1/models/model-1/runtime-artifacts/artifact-1",
        "token",
        payload,
        client=client,
    )

    assert payload["validation_status"] == "valid"
    assert payload["validation_error"] is None
    assert response["validation_status"] == "valid"
    assert client.calls[0]["method"] == "PATCH"


def test_validate_runtime_artifact_patches_invalid_when_file_missing(tmp_path) -> None:
    missing = tmp_path / "missing.engine"

    payload = build_validation_patch(
        artifact_path=missing,
        expected_sha256="b" * 64,
        target_profile="linux-aarch64-nvidia-jetson",
        host_profile="linux-aarch64-nvidia-jetson",
    )

    assert payload["validation_status"] == "invalid"
    assert "does not exist" in str(payload["validation_error"])
