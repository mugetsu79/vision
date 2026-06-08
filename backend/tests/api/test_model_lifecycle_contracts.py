from uuid import uuid4

import pytest
from pydantic import ValidationError

from argus.api.contracts import (
    EdgeConfigurationUpdate,
    ModelImportRequest,
    RuntimeArtifactBuildJobCreate,
)


def test_model_import_request_requires_checksum_for_url() -> None:
    payload = ModelImportRequest(
        source="url",
        source_uri="https://models.example/weights/yolo26n.onnx",
        expected_sha256="a" * 64,
        name="YOLO26n COCO",
        version="2026.1",
        task="detect",
        format="onnx",
        capability="fixed_vocab",
        input_shape={"width": 640, "height": 640},
        classes=[],
        license="AGPL-3.0",
    )
    assert payload.expected_sha256 == "a" * 64


def test_model_import_request_rejects_url_without_checksum() -> None:
    with pytest.raises(ValidationError, match="expected_sha256 is required"):
        ModelImportRequest(
            source="url",
            source_uri="https://models.example/weights/yolo26n.onnx",
            name="YOLO26n COCO",
            version="2026.1",
            task="detect",
            format="onnx",
            capability="fixed_vocab",
            input_shape={"width": 640, "height": 640},
            classes=[],
            license="AGPL-3.0",
        )


def test_artifact_build_job_accepts_tensorrt_target_node() -> None:
    payload = RuntimeArtifactBuildJobCreate(
        deployment_node_id=uuid4(),
        build_format="tensorrt_engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision="fp16",
        input_shape={"width": 640, "height": 640},
        export_formats=["tensorrt_engine"],
    )
    assert payload.build_format == "tensorrt_engine"


def test_edge_configuration_update_contains_post_install_settings() -> None:
    payload = EdgeConfigurationUpdate(
        desired_config={
            "model_store_path": "/var/lib/vezor/models",
            "artifact_store_path": "/var/lib/vezor/artifacts",
            "worker_concurrency": 1,
            "runtime_preference": "tensorrt_first",
            "service_report_interval_seconds": 30,
            "stream_delivery_profile": "native",
        }
    )
    assert payload.desired_config["worker_concurrency"] == 1
