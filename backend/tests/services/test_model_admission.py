from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from argus.api.contracts import HardwarePerformanceSample, WorkerModelAdmissionRequest
from argus.models.enums import DetectorCapability, ModelAdmissionStatus
from argus.services.model_admission import evaluate_worker_model_admission


def test_model_admission_is_unknown_without_fresh_hardware_report() -> None:
    decision = evaluate_worker_model_admission(
        _admission_request(selected_backend="tensorrt_engine"),
        hardware_report=None,
    )

    assert decision.status is ModelAdmissionStatus.UNKNOWN
    assert "No fresh hardware report" in decision.rationale


def test_model_admission_rejects_required_backend_missing_from_hardware() -> None:
    decision = evaluate_worker_model_admission(
        _admission_request(
            selected_backend="tensorrt_engine",
            runtime_artifact_target_profile="linux-aarch64-nvidia-jetson",
        ),
        hardware_report=_hardware_report(
            host_profile="linux-aarch64-nvidia-jetson",
            providers={"CPUExecutionProvider": True, "TensorrtExecutionProvider": False},
            performance=[],
        ),
    )

    assert decision.status is ModelAdmissionStatus.UNSUPPORTED
    assert "tensorrt_engine" in decision.rationale
    assert decision.recommended_backend == "onnxruntime"


def test_model_admission_rejects_open_world_cpu_for_production_stream() -> None:
    decision = evaluate_worker_model_admission(
        _admission_request(
            model_capability=DetectorCapability.OPEN_VOCAB,
            model_name="YOLOE S open vocabulary",
            selected_backend="onnxruntime",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
        ),
        hardware_report=_hardware_report(
            host_profile="linux-x86_64-cpu",
            providers={"CPUExecutionProvider": True},
            accelerators=[],
            performance=[],
        ),
    )

    assert decision.status is ModelAdmissionStatus.UNSUPPORTED
    assert "open-world" in decision.rationale
    assert decision.recommended_model_name == "YOLO26n COCO"
    assert decision.recommended_backend == "onnxruntime"


def test_model_admission_recommends_backend_when_p95_fits_frame_budget() -> None:
    model_id = uuid4()

    decision = evaluate_worker_model_admission(
        _admission_request(
            model_id=model_id,
            model_name="YOLO26n COCO",
            selected_backend="CoreMLExecutionProvider",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
        ),
        hardware_report=_hardware_report(
            host_profile="macos-x86_64-intel",
            providers={"CoreMLExecutionProvider": True},
            accelerators=["coreml"],
            performance=[
                HardwarePerformanceSample(
                    model_id=model_id,
                    model_name="YOLO26n COCO",
                    runtime_backend="CoreMLExecutionProvider",
                    input_width=1280,
                    input_height=720,
                    target_fps=10.0,
                    observed_fps=10.0,
                    stage_p95_ms={"total": 91.0, "detect": 54.0},
                    stage_p99_ms={"total": 119.0, "detect": 72.0},
                )
            ],
        ),
    )

    assert decision.status is ModelAdmissionStatus.RECOMMENDED
    assert "91.0ms" in decision.rationale
    assert decision.constraints["frame_budget_ms"] == 100.0


def test_model_admission_degrades_when_fallback_exceeds_frame_budget() -> None:
    model_id = uuid4()

    decision = evaluate_worker_model_admission(
        _admission_request(
            model_id=model_id,
            selected_backend="onnxruntime",
            stream_profile={"width": 1280, "height": 720, "fps": 10},
        ),
        hardware_report=_hardware_report(
            host_profile="linux-x86_64-cpu",
            providers={"CPUExecutionProvider": True},
            performance=[
                HardwarePerformanceSample(
                    model_id=model_id,
                    model_name="YOLO26n COCO",
                    runtime_backend="onnxruntime",
                    input_width=1280,
                    input_height=720,
                    target_fps=10.0,
                    observed_fps=6.8,
                    stage_p95_ms={"total": 148.0},
                    stage_p99_ms={"total": 190.0},
                )
            ],
        ),
    )

    assert decision.status is ModelAdmissionStatus.DEGRADED
    assert "exceeds" in decision.rationale
    assert decision.recommended_model_name == "YOLO26n COCO"


def _admission_request(
    *,
    model_id=None,  # noqa: ANN001
    model_name: str = "YOLO26n COCO",
    model_capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
    selected_backend: str = "onnxruntime",
    runtime_artifact_target_profile: str | None = None,
    stream_profile: dict[str, object] | None = None,
) -> WorkerModelAdmissionRequest:
    return WorkerModelAdmissionRequest(
        camera_id=uuid4(),
        edge_node_id=uuid4(),
        model_id=model_id or uuid4(),
        model_name=model_name,
        model_capability=model_capability,
        selected_backend=selected_backend,
        runtime_artifact_target_profile=runtime_artifact_target_profile,
        stream_profile=stream_profile or {"width": 1280, "height": 720, "fps": 10},
    )


def _hardware_report(
    *,
    host_profile: str,
    providers: dict[str, bool],
    performance: list[HardwarePerformanceSample],
    accelerators: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        edge_node_id=uuid4(),
        supervisor_id="supervisor-1",
        reported_at=datetime(2026, 5, 13, 11, 0, tzinfo=UTC),
        host_profile=host_profile,
        accelerators=accelerators or [],
        provider_capabilities=providers,
        observed_performance=[sample.model_dump(mode="json") for sample in performance],
    )
