from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import RuntimeArtifactSoakRunCreate
from argus.models.enums import (
    DetectorCapability,
    ModelAdmissionStatus,
    OperatorConfigProfileKind,
    OperatorConfigScope,
    OperatorConfigValidationStatus,
    RuntimeArtifactKind,
    RuntimeArtifactPrecision,
    RuntimeArtifactScope,
    RuntimeArtifactSoakStatus,
    RuntimeArtifactValidationStatus,
)
from argus.models.tables import (
    EdgeNodeHardwareReport,
    ModelRuntimeArtifact,
    OperatorConfigProfile,
    RuntimeArtifactSoakRun,
    WorkerAssignment,
    WorkerModelAdmissionReport,
)
from argus.services.runtime_soak import RuntimeSoakService

TENANT_ID = UUID("00000000-0000-0000-0000-000000000101")
EDGE_NODE_ID = UUID("00000000-0000-0000-0000-000000000102")
CAMERA_ID = UUID("00000000-0000-0000-0000-000000000103")
MODEL_ID = UUID("00000000-0000-0000-0000-000000000104")


class _Result:
    def __init__(self, values: Iterable[object]) -> None:
        self.values = list(values)

    def scalars(self) -> _Result:
        return self

    def scalar_one_or_none(self) -> object | None:
        return self.values[0] if self.values else None

    def all(self) -> list[object]:
        return self.values


class _FakeSession:
    def __init__(self, state: dict[str, list[object]]) -> None:
        self.state = state

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def add(self, run: RuntimeArtifactSoakRun) -> None:
        if run.id is None:
            run.id = uuid4()
        self.state.setdefault("runs", []).append(run)

    async def commit(self) -> None:
        self.state.setdefault("commits", []).append(True)

    async def refresh(self, run: RuntimeArtifactSoakRun) -> None:
        run.created_at = run.created_at or datetime(2026, 5, 14, 9, 0, tzinfo=UTC)

    async def get(self, model_cls, object_id):  # noqa: ANN001
        for item in self.state.get(model_cls.__name__, []):
            if getattr(item, "id", None) == object_id:
                return item
        return None

    async def execute(self, statement):  # noqa: ANN001
        entity = statement.column_descriptions[0]["entity"]
        if entity is WorkerModelAdmissionReport:
            values = [
                report
                for report in self.state.get(WorkerModelAdmissionReport.__name__, [])
                if report.tenant_id == TENANT_ID
            ]
            return _Result(values)
        if entity is RuntimeArtifactSoakRun:
            return _Result(self.state.get("runs", []))
        return _Result([])


class _FakeSessionFactory:
    def __init__(self, *items: object) -> None:
        self.state: dict[str, list[object]] = {}
        for item in items:
            self.state.setdefault(type(item).__name__, []).append(item)
        self.state["runs"] = []

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


@pytest.mark.asyncio
async def test_runtime_soak_records_fixed_vocab_tensorrt_run_with_control_plane_context() -> None:
    artifact = _runtime_artifact(
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        model_id=MODEL_ID,
        camera_id=None,
    )
    assignment = _assignment()
    profile = _runtime_selection_profile()
    hardware_report = _hardware_report()
    admission = _admission_report(
        artifact_id=artifact.id,
        assignment_id=assignment.id,
        profile_id=profile.id,
        hardware_report_id=hardware_report.id,
        status=ModelAdmissionStatus.RECOMMENDED,
        rationale="TensorRT p95 total fits the Jetson frame budget.",
    )
    service = RuntimeSoakService(
        _FakeSessionFactory(artifact, assignment, profile, hardware_report, admission)
    )

    response = await service.record_soak_run(
        tenant_id=TENANT_ID,
        payload=RuntimeArtifactSoakRunCreate(
            edge_node_id=EDGE_NODE_ID,
            runtime_artifact_id=artifact.id,
            operations_assignment_id=assignment.id,
            runtime_selection_profile_id=profile.id,
            hardware_report_id=hardware_report.id,
            model_admission_report_id=admission.id,
            status=RuntimeArtifactSoakStatus.PASSED,
            started_at=datetime(2026, 5, 14, 8, 0, tzinfo=UTC),
            ended_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            metrics={"duration_minutes": 60, "fps_p50": 10.2, "worker_restarts": 0},
            notes="YOLO26n fixed-vocab TensorRT soak passed on Jetson.",
        ),
    )

    assert response.runtime_artifact_id == artifact.id
    assert response.runtime_kind is RuntimeArtifactKind.TENSORRT_ENGINE
    assert response.runtime_backend == "tensorrt_engine"
    assert response.target_profile == "linux-aarch64-nvidia-jetson"
    assert response.edge_node_id == EDGE_NODE_ID
    assert response.status is RuntimeArtifactSoakStatus.PASSED
    assert response.metrics["fps_p50"] == 10.2
    assert response.operations_assignment_id == assignment.id
    assert response.runtime_selection_profile_id == profile.id
    assert response.runtime_selection_profile_hash == "c" * 64
    assert response.hardware_report_id == hardware_report.id
    assert response.hardware_admission_status is ModelAdmissionStatus.RECOMMENDED
    assert response.model_recommendation_rationale == (
        "TensorRT p95 total fits the Jetson frame budget."
    )


@pytest.mark.asyncio
async def test_runtime_soak_records_open_vocab_scene_fallback_reason() -> None:
    artifact = _runtime_artifact(
        kind=RuntimeArtifactKind.COMPILED_OPEN_VOCAB,
        capability=DetectorCapability.OPEN_VOCAB,
        runtime_backend="tensorrt_engine",
        model_id=MODEL_ID,
        camera_id=CAMERA_ID,
    )
    profile = _runtime_selection_profile()
    admission = _admission_report(
        artifact_id=artifact.id,
        assignment_id=None,
        profile_id=profile.id,
        hardware_report_id=None,
        status=ModelAdmissionStatus.DEGRADED,
        model_capability=DetectorCapability.OPEN_VOCAB,
        rationale="Optimized scene artifact was unavailable; ONNX fallback stayed stable.",
    )
    service = RuntimeSoakService(_FakeSessionFactory(artifact, profile, admission))

    response = await service.record_soak_run(
        tenant_id=TENANT_ID,
        payload=RuntimeArtifactSoakRunCreate(
            edge_node_id=EDGE_NODE_ID,
            runtime_artifact_id=artifact.id,
            runtime_selection_profile_id=profile.id,
            model_admission_report_id=admission.id,
            status=RuntimeArtifactSoakStatus.PASSED,
            started_at=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
            ended_at=datetime(2026, 5, 14, 11, 0, tzinfo=UTC),
            metrics={"open_vocab_queries": 4, "fallback_backend": "onnxruntime"},
            fallback_reason="Compiled TensorRT scene artifact was missing on the Jetson.",
        ),
    )

    assert response.runtime_kind is RuntimeArtifactKind.COMPILED_OPEN_VOCAB
    assert response.model_capability is DetectorCapability.OPEN_VOCAB
    assert response.camera_id == CAMERA_ID
    assert response.fallback_reason == (
        "Compiled TensorRT scene artifact was missing on the Jetson."
    )
    assert response.hardware_admission_status is ModelAdmissionStatus.DEGRADED
    assert response.model_recommendation_rationale == (
        "Optimized scene artifact was unavailable; ONNX fallback stayed stable."
    )


@pytest.mark.asyncio
async def test_runtime_soak_lists_runs_for_runtime_artifact() -> None:
    artifact = _runtime_artifact(
        kind=RuntimeArtifactKind.TENSORRT_ENGINE,
        capability=DetectorCapability.FIXED_VOCAB,
        runtime_backend="tensorrt_engine",
        model_id=MODEL_ID,
        camera_id=None,
    )
    service = RuntimeSoakService(_FakeSessionFactory(artifact))

    created = await service.record_soak_run(
        tenant_id=TENANT_ID,
        payload=RuntimeArtifactSoakRunCreate(
            edge_node_id=EDGE_NODE_ID,
            runtime_artifact_id=artifact.id,
            status=RuntimeArtifactSoakStatus.FAILED,
            started_at=datetime(2026, 5, 14, 12, 0, tzinfo=UTC),
            metrics={"worker_restarts": 2},
            notes="Worker restarted twice during soak.",
        ),
    )

    runs = await service.list_soak_runs(
        tenant_id=TENANT_ID,
        runtime_artifact_id=artifact.id,
    )

    assert [run.id for run in runs] == [created.id]
    assert runs[0].status is RuntimeArtifactSoakStatus.FAILED
    assert runs[0].notes == "Worker restarted twice during soak."


def _runtime_artifact(
    *,
    kind: RuntimeArtifactKind,
    capability: DetectorCapability,
    runtime_backend: str,
    model_id: UUID,
    camera_id: UUID | None,
) -> ModelRuntimeArtifact:
    return ModelRuntimeArtifact(
        id=uuid4(),
        model_id=model_id,
        camera_id=camera_id,
        scope=RuntimeArtifactScope.SCENE if camera_id else RuntimeArtifactScope.MODEL,
        kind=kind,
        capability=capability,
        runtime_backend=runtime_backend,
        path="/models/yolo26n.engine",
        target_profile="linux-aarch64-nvidia-jetson",
        precision=RuntimeArtifactPrecision.FP16,
        input_shape={"width": 640, "height": 640},
        classes=["person", "car"],
        vocabulary_hash="v" * 64 if capability is DetectorCapability.OPEN_VOCAB else None,
        vocabulary_version=3 if capability is DetectorCapability.OPEN_VOCAB else None,
        source_model_sha256="a" * 64,
        sha256="b" * 64,
        size_bytes=4321,
        builder={},
        runtime_versions={"tensorrt": "10.3"},
        validation_status=RuntimeArtifactValidationStatus.VALID,
        validation_error=None,
    )


def _assignment() -> WorkerAssignment:
    return WorkerAssignment(
        id=uuid4(),
        tenant_id=TENANT_ID,
        camera_id=CAMERA_ID,
        edge_node_id=EDGE_NODE_ID,
        desired_state="supervised",
        active=True,
        supersedes_assignment_id=None,
        assigned_by_subject="admin-1",
    )


def _runtime_selection_profile() -> OperatorConfigProfile:
    return OperatorConfigProfile(
        id=uuid4(),
        tenant_id=TENANT_ID,
        site_id=None,
        edge_node_id=EDGE_NODE_ID,
        camera_id=None,
        kind=OperatorConfigProfileKind.RUNTIME_SELECTION,
        scope=OperatorConfigScope.EDGE_NODE,
        name="Jetson TensorRT First",
        slug="jetson-tensorrt-first",
        enabled=True,
        is_default=False,
        config={"artifact_preference": "tensorrt_first"},
        validation_status=OperatorConfigValidationStatus.VALID,
        validation_message=None,
        validated_at=datetime(2026, 5, 14, 7, 0, tzinfo=UTC),
        config_hash="c" * 64,
    )


def _hardware_report() -> EdgeNodeHardwareReport:
    return EdgeNodeHardwareReport(
        id=uuid4(),
        tenant_id=TENANT_ID,
        edge_node_id=EDGE_NODE_ID,
        supervisor_id="edge-orin-1",
        reported_at=datetime(2026, 5, 14, 7, 30, tzinfo=UTC),
        host_profile="linux-aarch64-nvidia-jetson",
        os_name="ubuntu",
        machine_arch="aarch64",
        cpu_model="Jetson Orin Nano",
        cpu_cores=6,
        memory_total_mb=8192,
        accelerators=["cuda", "tensorrt"],
        provider_capabilities={"TensorrtExecutionProvider": True},
        observed_performance=[],
        thermal_state="nominal",
        report_hash="d" * 64,
    )


def _admission_report(
    *,
    artifact_id: UUID,
    assignment_id: UUID | None,
    profile_id: UUID,
    hardware_report_id: UUID | None,
    status: ModelAdmissionStatus,
    rationale: str,
    model_capability: DetectorCapability = DetectorCapability.FIXED_VOCAB,
) -> WorkerModelAdmissionReport:
    return WorkerModelAdmissionReport(
        id=uuid4(),
        tenant_id=TENANT_ID,
        camera_id=CAMERA_ID,
        edge_node_id=EDGE_NODE_ID,
        assignment_id=assignment_id,
        hardware_report_id=hardware_report_id,
        model_id=MODEL_ID,
        model_name="YOLO26n COCO Edge",
        model_capability=model_capability,
        runtime_artifact_id=artifact_id,
        runtime_selection_profile_id=profile_id,
        stream_profile={"width": 1280, "height": 720, "fps": 10},
        status=status,
        selected_backend="tensorrt_engine",
        recommended_model_id=MODEL_ID,
        recommended_model_name="YOLO26n COCO Edge",
        recommended_runtime_profile_id=profile_id,
        recommended_backend="tensorrt_engine",
        rationale=rationale,
        constraints={"frame_budget_ms": 100.0},
        evaluated_at=datetime(2026, 5, 14, 7, 45, tzinfo=UTC),
    )
