from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from argus.api.contracts import (
    DeploymentModelInventoryReport,
    DeploymentModelSyncJobResponse,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
)
from argus.compat import UTC
from argus.models.enums import ModelLifecycleJobStatus
from argus.supervisor.model_jobs import SupervisorModelJobExecutor


@pytest.mark.asyncio
async def test_tensorrt_artifact_build_invokes_engine_builder_with_bounded_options(
    tmp_path: Path,
) -> None:
    source = tmp_path / "model.onnx"
    source.write_bytes(b"source model")
    output_dir = tmp_path / "artifacts"
    engine_path = output_dir / "model.engine"
    builder = _FakeTensorRTEngineBuilder(engine_path)
    camera_id = uuid4()
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "schema_version": 1,
            "model_id": str(uuid4()),
            "camera_id": str(camera_id),
            "source_model_path": str(source),
            "source_model_sha256": hashlib.sha256(b"source model").hexdigest(),
            "build_format": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": "fp16",
            "input_shape": {"width": 640, "height": 640},
            "classes": ["person", "car"],
            "output_dir": str(output_dir),
        }
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        tensorrt_engine_builder=builder,
        runtime_versions={"tensorrt": "10.8.0", "cuda": "12.8", "provider": "cuda"},
    )

    await executor.execute_once()

    assert builder.calls == [
        {
            "source_path": source,
            "output_path": engine_path,
            "input_shape": {"width": 640, "height": 640},
            "precision": "fp16",
        }
    ]
    assert len(client.completed) == 1
    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    artifact = completed.payload["artifact"]
    assert artifact["kind"] == "tensorrt_engine"
    assert artifact["camera_id"] == str(camera_id)
    assert artifact["runtime_versions"] == {
        "tensorrt": "10.8.0",
        "cuda": "12.8",
        "provider": "cuda",
    }


@pytest.mark.asyncio
async def test_open_vocab_artifact_build_exports_requested_formats_with_fake_yoloe(
    tmp_path: Path,
) -> None:
    source = tmp_path / "yoloe.pt"
    source.write_bytes(b"source model")
    output_dir = tmp_path / "artifacts"
    yoloe = _FakeYOLOE(output_dir)
    camera_id = uuid4()
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "schema_version": 1,
            "model_id": str(uuid4()),
            "camera_id": str(camera_id),
            "source_model_path": str(source),
            "source_model_sha256": hashlib.sha256(b"source model").hexdigest(),
            "build_format": "tensorrt_engine",
            "export_formats": ["onnx_export", "tensorrt_engine"],
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": "fp16",
            "input_shape": {"width": 640, "height": 640},
            "runtime_vocabulary": ["person", "laptop"],
            "vocabulary_version": 4,
            "output_dir": str(output_dir),
        }
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        yoloe_loader=lambda path: yoloe,
    )

    await executor.execute_once()

    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert yoloe.classes == ["person", "laptop"]
    assert yoloe.exported_formats == ["onnx", "engine"]
    assert yoloe.export_projects == [output_dir, output_dir]
    artifacts = completed.payload["artifacts"]
    assert [artifact["kind"] for artifact in artifacts] == ["onnx_export", "tensorrt_engine"]
    assert all(artifact["camera_id"] == str(camera_id) for artifact in artifacts)


@pytest.mark.asyncio
async def test_artifact_build_missing_source_path_reports_failed_completion(
    tmp_path: Path,
) -> None:
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "schema_version": 1,
            "source_model_path": str(tmp_path / "missing.onnx"),
            "build_format": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": "fp16",
            "input_shape": {"width": 640, "height": 640},
            "classes": ["person"],
            "output_dir": str(tmp_path / "artifacts"),
        }
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        tensorrt_engine_builder=_FakeTensorRTEngineBuilder(tmp_path / "unused.engine"),
    )

    await executor.execute_once()

    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error is not None
    assert "does not exist" in completed.error


@pytest.mark.asyncio
async def test_successful_artifact_build_completion_includes_runtime_versions(
    tmp_path: Path,
) -> None:
    source = tmp_path / "model.onnx"
    source.write_bytes(b"source model")
    engine_path = tmp_path / "artifacts" / "model.engine"
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "schema_version": 1,
            "source_model_path": str(source),
            "build_format": "tensorrt_engine",
            "target_profile": "linux-x86_64-cuda",
            "precision": "fp16",
            "input_shape": {"width": 640, "height": 640},
            "classes": ["person"],
            "output_dir": str(engine_path.parent),
        }
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        tensorrt_engine_builder=_FakeTensorRTEngineBuilder(engine_path),
        runtime_versions={"tensorrt": "10.8.0", "cuda": "12.8", "provider": "cuda"},
    )

    await executor.execute_once()

    artifact = client.completed[0][1].payload["artifact"]
    assert artifact["runtime_versions"]["tensorrt"] == "10.8.0"
    assert artifact["runtime_versions"]["cuda"] == "12.8"
    assert artifact["runtime_versions"]["provider"] == "cuda"


@pytest.mark.asyncio
async def test_tensorrt_artifact_build_reports_actual_validated_runtime_path_and_inventory(
    tmp_path: Path,
) -> None:
    source = tmp_path / "yolo26n.onnx"
    source.write_bytes(b"onnx")
    output_dir = tmp_path / "runtime-artifacts" / "model-1"
    expected_engine_path = output_dir / "yolo26n.engine"
    expected_engine_sha256 = hashlib.sha256(b"engine bytes").hexdigest()
    job = _artifact_job(
        payload={
            "job_type": "artifact_build",
            "schema_version": 1,
            "model_id": str(uuid4()),
            "source_model_path": str(source),
            "source_model_sha256": hashlib.sha256(b"onnx").hexdigest(),
            "build_format": "tensorrt_engine",
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": "fp16",
            "input_shape": {"width": 640, "height": 640},
            "classes": ["person"],
            "output_dir": str(output_dir),
        }
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        tensorrt_engine_builder=_FakeTensorRTEngineBuilder(expected_engine_path),
        runtime_versions={"onnxruntime_providers": ["TensorrtExecutionProvider"]},
    )

    await executor.execute_once()

    artifact = client.completed[0][1].payload["artifact"]
    assert artifact["path"] == str(expected_engine_path)
    assert artifact["sha256"] == expected_engine_sha256
    assert artifact["size_bytes"] == len(b"engine bytes")
    assert artifact["target_profile"] == "linux-aarch64-nvidia-jetson"
    assert artifact["source_model_sha256"] == hashlib.sha256(b"onnx").hexdigest()
    assert artifact["validation_status"] == "valid"

    assert len(client.inventory_reports) == 1
    inventory_item = client.inventory_reports[0].items[0]
    assert inventory_item.asset_kind == "runtime_artifact"
    assert inventory_item.asset_id == job.model_id
    assert inventory_item.local_path == str(expected_engine_path)
    assert inventory_item.sha256 == expected_engine_sha256
    assert inventory_item.size_bytes == len(b"engine bytes")
    assert inventory_item.target_profile == "linux-aarch64-nvidia-jetson"


class _FakeTensorRTEngineBuilder:
    def __init__(self, engine_path: Path) -> None:
        self.engine_path = engine_path
        self.calls: list[dict[str, object]] = []

    def build(
        self,
        source_path: Path,
        output_path: Path,
        input_shape: dict[str, int],
        precision: str,
    ) -> Path:
        self.calls.append(
            {
                "source_path": source_path,
                "output_path": output_path,
                "input_shape": dict(input_shape),
                "precision": precision,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"engine bytes")
        return output_path


class _FakeYOLOE:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.classes: list[str] = []
        self.exported_formats: list[str] = []
        self.export_projects: list[Path] = []

    def set_classes(self, terms: list[str]) -> None:
        self.classes = terms

    def export(self, *, format: str, project: str | None = None) -> Path:
        self.exported_formats.append(format)
        output_dir = Path(project) if project is not None else self.output_dir
        self.export_projects.append(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        suffix = "onnx" if format == "onnx" else "engine"
        path = output_dir / f"open-vocab.{suffix}"
        path.write_bytes(f"artifact {format}".encode())
        return path


def _artifact_job(*, payload: dict[str, object]) -> DeploymentModelSyncJobResponse:
    now = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
    return DeploymentModelSyncJobResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        deployment_node_id=uuid4(),
        assignment_id=uuid4(),
        model_id=uuid4(),
        status=ModelLifecycleJobStatus.ACCEPTED,
        payload=payload,
        claimed_by_supervisor_id="edge-supervisor-1",
        claimed_at=now,
        completed_at=None,
        error=None,
        created_at=now,
        updated_at=now,
    )


class _FakeOperationsClient:
    def __init__(self, jobs: list[DeploymentModelSyncJobResponse]) -> None:
        self.jobs = jobs
        self.events: list[tuple[UUID, SupervisorModelJobEventCreate]] = []
        self.completed: list[tuple[UUID, SupervisorModelJobComplete]] = []
        self.inventory_reports: list[DeploymentModelInventoryReport] = []

    async def poll_model_jobs(self, limit: int) -> list[DeploymentModelSyncJobResponse]:
        return self.jobs[:limit]

    async def record_model_job_event(
        self,
        job_id: UUID,
        event: SupervisorModelJobEventCreate,
    ) -> DeploymentModelSyncJobResponse:
        self.events.append((job_id, event))
        return self.jobs[0]

    async def complete_model_job(
        self,
        job_id: UUID,
        completion: SupervisorModelJobComplete,
    ) -> DeploymentModelSyncJobResponse:
        self.completed.append((job_id, completion))
        return self.jobs[0]

    async def record_model_inventory(
        self,
        report: DeploymentModelInventoryReport,
    ) -> DeploymentModelInventoryReport:
        self.inventory_reports.append(report)
        return report

    async def download_model_asset(self, asset_id: UUID, destination_path: str | Path) -> Path:
        raise AssertionError("download_model_asset is not used for artifact builds")
