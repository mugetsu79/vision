from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from argus.api.contracts import WorkerModelAdmissionRequest
from argus.models.enums import ModelAdmissionStatus
from argus.services import app as app_service
from argus.services.model_admission import evaluate_worker_model_admission
from argus.services.runtime_passports import build_runtime_passport


def test_no_fallback_blocks_when_selected_backend_unavailable() -> None:
    decision = app_service._runtime_selection_decision(
        preferred_backend="tensorrt_engine",
        artifact_preference="tensorrt_first",
        fallback_allowed=False,
        available_artifacts=[],
        available_backends=["onnxruntime"],
    )

    assert decision.selected_backend is None
    assert decision.selected_artifact_id is None
    assert decision.fallback_reason is None
    assert decision.blocked_reason == (
        "Runtime selection has no compatible artifact and fallback is disabled."
    )


def test_runtime_selection_filters_artifacts_by_target_profile() -> None:
    artifact_id = uuid4()

    decision = app_service._runtime_selection_decision(
        preferred_backend=None,
        artifact_preference="tensorrt_first",
        fallback_allowed=True,
        available_artifacts=[
            SimpleNamespace(
                id=artifact_id,
                runtime_backend="tensorrt_engine",
                target_profile="linux-aarch64-nvidia-jetson",
            )
        ],
        available_backends=["tensorrt_engine", "onnxruntime"],
        model_backend="onnxruntime",
        target_profile="linux-aarch64",
    )

    assert decision.selected_backend == "onnxruntime"
    assert decision.selected_artifact_id is None
    assert decision.fallback_reason == "artifact_target_mismatch"
    assert decision.blocked_reason is None


def test_runtime_passport_records_selected_artifact_and_fallback_reason() -> None:
    artifact_id = str(uuid4())
    fallback_reason = "TensorRT artifact unavailable"

    passport = build_runtime_passport(
        tenant_id="tenant-a",
        camera_id="camera-a",
        scene_contract_hash="a" * 64,
        model_metadata={
            "id": "model-yolo",
            "name": "YOLO",
            "sha256": "b" * 64,
            "runtime_backend": "tensorrt_engine",
        },
        runtime_selection={
            "profile_id": "22222222-2222-2222-2222-222222222222",
            "profile_name": "TensorRT first",
            "profile_hash": "c" * 64,
            "artifact_preference": "tensorrt_first",
            "fallback_allowed": True,
            "preferred_backend": "tensorrt_engine",
            "backend": "onnxruntime",
            "selected_artifact_id": artifact_id,
            "fallback_reason": fallback_reason,
        },
        runtime_artifact={
            "id": artifact_id,
            "kind": "onnx_export",
            "sha256": "d" * 64,
            "runtime_backend": "onnxruntime",
            "source_model_sha256": "b" * 64,
        },
        selection_report={
            "selected_backend": "onnxruntime",
            "fallback": True,
            "fallback_reason": fallback_reason,
        },
    )

    assert passport["selected_runtime"]["backend"] == "onnxruntime"
    assert passport["selected_runtime"]["runtime_artifact_id"] == artifact_id
    assert passport["selected_runtime"]["fallback_reason"] == fallback_reason
    assert passport["runtime_selection_profile"]["fallback_reason"] == fallback_reason


def test_model_admission_uses_preferred_backend_when_selected_backend_is_empty() -> None:
    request = WorkerModelAdmissionRequest(
        camera_id=uuid4(),
        edge_node_id=uuid4(),
        model_name="YOLO",
        selected_backend=None,
        preferred_backend="tensorrt_engine",
        stream_profile={"width": 1280, "height": 720, "fps": 10},
    )

    decision = evaluate_worker_model_admission(
        request,
        hardware_report=SimpleNamespace(
            id=uuid4(),
            host_profile="linux-aarch64-nvidia-jetson",
            accelerators=["tensorrt"],
            provider_capabilities={"TensorrtExecutionProvider": True},
            observed_performance=[],
            reported_at=datetime(2026, 5, 13, 11, 0, tzinfo=UTC),
        ),
    )

    assert decision.status is ModelAdmissionStatus.SUPPORTED
    assert decision.recommended_backend == "tensorrt_engine"
