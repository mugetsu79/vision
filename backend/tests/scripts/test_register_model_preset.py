from __future__ import annotations

import hashlib
import json
import subprocess
import sys

from argus.scripts.register_model_preset import build_model_create_payload


def test_build_model_create_payload_uses_catalog_defaults(tmp_path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"model")

    payload = build_model_create_payload(
        catalog_id="yolo26n-coco-onnx",
        artifact_path=artifact,
        classes=["person", "car"],
    )

    assert payload["name"] == "YOLO26n COCO"
    assert payload["format"] == "onnx"
    assert payload["capability"] == "fixed_vocab"
    assert payload["capability_config"]["catalog_id"] == "yolo26n-coco-onnx"
    assert payload["sha256"] == hashlib.sha256(b"model").hexdigest()
    assert payload["size_bytes"] == 5
    assert payload["classes"] == ["person", "car"]


def test_build_model_create_payload_leaves_empty_catalog_classes_unspecified(tmp_path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"model")

    payload = build_model_create_payload(
        catalog_id="yolo26n-coco-onnx",
        artifact_path=artifact,
        classes=None,
    )

    assert payload["classes"] is None


def test_module_entrypoint_prints_payload_without_api_base_url(tmp_path) -> None:
    artifact = tmp_path / "yolo26n.onnx"
    artifact.write_bytes(b"model")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "argus.scripts.register_model_preset",
            "--catalog-id",
            "yolo26n-coco-onnx",
            "--artifact-path",
            str(artifact),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["name"] == "YOLO26n COCO"
    assert payload["path"] == str(artifact)
