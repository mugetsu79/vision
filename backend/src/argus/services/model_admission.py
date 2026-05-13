from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from argus.api.contracts import WorkerModelAdmissionRequest
from argus.models.enums import DetectorCapability, ModelAdmissionStatus


@dataclass(frozen=True, slots=True)
class ModelAdmissionDecision:
    status: ModelAdmissionStatus
    rationale: str
    constraints: dict[str, Any] = field(default_factory=dict)
    recommended_model_id: UUID | None = None
    recommended_model_name: str | None = None
    recommended_runtime_profile_id: UUID | None = None
    recommended_backend: str | None = None


def evaluate_worker_model_admission(
    request: WorkerModelAdmissionRequest,
    *,
    hardware_report: object | None,
) -> ModelAdmissionDecision:
    if hardware_report is None:
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.UNKNOWN,
            rationale="No fresh hardware report is available for this worker target.",
        )

    backend = request.selected_backend or request.preferred_backend or "onnxruntime"
    frame_budget_ms = _frame_budget_ms(request.stream_profile)
    constraints: dict[str, Any] = {"frame_budget_ms": frame_budget_ms}

    host_profile = str(_value(hardware_report, "host_profile") or "")
    if (
        request.runtime_artifact_target_profile
        and host_profile
        and request.runtime_artifact_target_profile != host_profile
    ):
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.UNSUPPORTED,
            rationale=(
                "Runtime artifact target profile "
                f"{request.runtime_artifact_target_profile!r} does not match "
                f"hardware profile {host_profile!r}."
            ),
            constraints=constraints,
            recommended_backend=_recommended_backend(hardware_report),
        )

    if not _backend_available(backend, hardware_report):
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.UNSUPPORTED,
            rationale=f"Required backend {backend!r} is not available on this hardware.",
            constraints=constraints,
            recommended_backend=_recommended_backend(hardware_report),
        )

    if _open_world_cpu_production_stream(request, hardware_report):
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.UNSUPPORTED,
            rationale=(
                "Production open-world models are unsupported on CPU-only hardware "
                "at 720p10 or higher."
            ),
            constraints=constraints,
            recommended_model_name="YOLO26n COCO",
            recommended_backend=_recommended_backend(hardware_report),
        )

    sample = _matching_performance_sample(request, backend, hardware_report)
    if sample is None:
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.SUPPORTED,
            rationale=(
                f"Backend {backend!r} is available, but no matching "
                "performance sample exists yet."
            ),
            constraints=constraints,
            recommended_backend=backend,
        )

    p95_total_ms = _stage_total_ms(sample, "stage_p95_ms")
    constraints["observed_p95_total_ms"] = p95_total_ms
    if p95_total_ms is not None and p95_total_ms <= frame_budget_ms:
        return ModelAdmissionDecision(
            status=ModelAdmissionStatus.RECOMMENDED,
            rationale=(
                f"{backend} p95 total {p95_total_ms:.1f}ms fits the "
                f"{frame_budget_ms:.1f}ms frame budget."
            ),
            constraints=constraints,
            recommended_backend=backend,
        )

    return ModelAdmissionDecision(
        status=ModelAdmissionStatus.DEGRADED,
        rationale=(
            f"{backend} p95 total {p95_total_ms:.1f}ms exceeds the "
            f"{frame_budget_ms:.1f}ms frame budget."
            if p95_total_ms is not None
            else f"{backend} performance sample is incomplete."
        ),
        constraints=constraints,
        recommended_model_name="YOLO26n COCO",
        recommended_backend=_recommended_backend(hardware_report),
    )


def _frame_budget_ms(stream_profile: dict[str, Any]) -> float:
    fps = float(stream_profile.get("fps") or stream_profile.get("target_fps") or 10.0)
    if fps <= 0:
        fps = 10.0
    return 1000.0 / fps


def _backend_available(backend: str, hardware_report: object) -> bool:
    backend_lower = backend.lower()
    providers = _providers(hardware_report)
    accelerators = {
        str(value).lower() for value in _value(hardware_report, "accelerators") or []
    }
    if "tensorrt" in backend_lower:
        return any("tensorrt" in key and value for key, value in providers.items()) or bool(
            {"tensorrt", "cuda", "nvidia"} & accelerators
        )
    if "coreml" in backend_lower:
        return (
            any("coreml" in key and value for key, value in providers.items())
            or "coreml" in accelerators
        )
    if "onnx" in backend_lower:
        return any(value for value in providers.values()) or not providers
    return True


def _open_world_cpu_production_stream(
    request: WorkerModelAdmissionRequest,
    hardware_report: object,
) -> bool:
    if request.model_capability is not DetectorCapability.OPEN_VOCAB:
        return False
    accelerators = _value(hardware_report, "accelerators") or []
    has_accelerator = any(str(value).lower() not in {"cpu", "none"} for value in accelerators)
    height = int(
        request.stream_profile.get("height")
        or request.stream_profile.get("input_height")
        or 0
    )
    fps = float(request.stream_profile.get("fps") or request.stream_profile.get("target_fps") or 0)
    return not has_accelerator and height >= 720 and fps >= 10


def _matching_performance_sample(
    request: WorkerModelAdmissionRequest,
    backend: str,
    hardware_report: object,
) -> dict[str, Any] | None:
    for raw_sample in _value(hardware_report, "observed_performance") or []:
        sample = dict(raw_sample)
        if sample.get("runtime_backend") != backend:
            continue
        if request.model_id is not None and str(sample.get("model_id")) == str(request.model_id):
            return sample
        if request.model_name and sample.get("model_name") == request.model_name:
            return sample
    return None


def _stage_total_ms(sample: dict[str, Any], key: str) -> float | None:
    stages = sample.get(key)
    if not isinstance(stages, dict):
        return None
    value = stages.get("total")
    return float(value) if value is not None else None


def _recommended_backend(hardware_report: object) -> str:
    providers = _providers(hardware_report)
    accelerators = {
        str(value).lower() for value in _value(hardware_report, "accelerators") or []
    }
    if (
        any("tensorrt" in key and value for key, value in providers.items())
        or "tensorrt" in accelerators
    ):
        return "tensorrt_engine"
    if (
        any("coreml" in key and value for key, value in providers.items())
        or "coreml" in accelerators
    ):
        return "CoreMLExecutionProvider"
    return "onnxruntime"


def _providers(hardware_report: object) -> dict[str, bool]:
    providers = _value(hardware_report, "provider_capabilities") or {}
    return {str(key).lower(): bool(value) for key, value in dict(providers).items()}


def _value(source: object, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)
    return getattr(source, key, None)
