from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from argus.vision.runtime_artifact_builder import (
    build_fixed_vocab_artifact_payload,
    build_open_vocab_scene_artifact_payloads,
)
from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms


def test_fixed_vocab_tensorrt_payload_includes_hashes_and_runtime_metadata(
    tmp_path: Path,
) -> None:
    source = tmp_path / "model.onnx"
    engine = tmp_path / "model.engine"
    source.write_bytes(b"source model")
    engine.write_bytes(b"engine bytes")

    payload = build_fixed_vocab_artifact_payload(
        source_model_path=source,
        prebuilt_engine_path=engine,
        classes=["person", "car"],
        input_shape={"width": 640, "height": 640},
        target_profile="linux-aarch64-nvidia-jetson",
    )

    assert payload["kind"] == "tensorrt_engine"
    assert payload["runtime_backend"] == "tensorrt_engine"
    assert payload["source_model_sha256"] == hashlib.sha256(b"source model").hexdigest()
    assert payload["sha256"] == hashlib.sha256(b"engine bytes").hexdigest()
    assert payload["size_bytes"] == len(b"engine bytes")


def test_open_vocab_payload_requires_runtime_vocabulary(tmp_path: Path) -> None:
    source = tmp_path / "yoloe.pt"
    source.write_bytes(b"source model")

    with pytest.raises(ValueError, match="runtime_vocabulary"):
        build_open_vocab_scene_artifact_payloads(
            source_model_path=source,
            camera_id="camera-1",
            runtime_vocabulary=[],
            export_formats=["onnx"],
            input_shape={"width": 640, "height": 640},
            target_profile="linux-aarch64-nvidia-jetson",
        )


def test_open_vocab_payload_uses_normalized_vocabulary_hash_with_fake_yoloe(
    tmp_path: Path,
) -> None:
    source = tmp_path / "yoloe.pt"
    source.write_bytes(b"source model")
    exported = tmp_path / "yoloe.onnx"

    class _FakeYOLOE:
        def __init__(self) -> None:
            self.classes: list[str] = []

        def set_classes(self, terms: list[str]) -> None:
            self.classes = terms

        def export(self, *, format: str) -> Path:
            assert format == "onnx"
            exported.write_bytes(b"exported onnx")
            return exported

    fake = _FakeYOLOE()

    payloads = build_open_vocab_scene_artifact_payloads(
        source_model_path=source,
        camera_id="camera-1",
        runtime_vocabulary=["person", "laptop"],
        export_formats=["onnx"],
        input_shape={"width": 640, "height": 640},
        target_profile="linux-aarch64-nvidia-jetson",
        vocabulary_version=3,
        yoloe_loader=lambda path: fake,
    )

    expected_terms = normalize_vocabulary_terms(["person", "laptop"])
    expected_hash = hash_vocabulary(expected_terms)
    assert fake.classes == expected_terms
    assert payloads[0]["vocabulary_hash"] == expected_hash
    assert payloads[0]["classes"] == expected_terms
    assert payloads[0]["vocabulary_version"] == 3
