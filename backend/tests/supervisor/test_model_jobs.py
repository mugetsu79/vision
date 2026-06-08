from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import anyio
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
async def test_model_sync_job_copies_file_and_reports_inventory(tmp_path) -> None:
    source_path = tmp_path / "source.onnx"
    model_bytes = b"edge model payload"
    source_path.write_bytes(model_bytes)
    target_path = tmp_path / "models" / "yolo26n.onnx"
    expected_sha256 = hashlib.sha256(model_bytes).hexdigest()
    model_id = uuid4()
    job = _model_job(
        model_id=model_id,
        payload={
            "job_type": "model_sync",
            "source_path": str(source_path),
            "target_path": str(target_path),
            "expected_sha256": expected_sha256,
            "size_bytes": len(model_bytes),
            "target_profile": "linux-aarch64-nvidia-jetson",
        },
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(
        operations_client=client,
        reported_at=lambda: datetime(2026, 6, 8, 9, 0, tzinfo=UTC),
    )

    await executor.execute_once()

    assert target_path.read_bytes() == model_bytes
    assert [event.status for _, event in client.events] == [
        ModelLifecycleJobStatus.ACCEPTED,
        ModelLifecycleJobStatus.RUNNING,
        ModelLifecycleJobStatus.SUCCEEDED,
    ]
    assert len(client.inventory_reports) == 1
    inventory_item = client.inventory_reports[0].items[0]
    assert inventory_item.asset_id == model_id
    assert inventory_item.local_path == str(target_path)
    assert inventory_item.sha256 == expected_sha256
    assert inventory_item.size_bytes == len(model_bytes)
    assert inventory_item.target_profile == "linux-aarch64-nvidia-jetson"
    assert len(client.completed) == 1
    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.SUCCEEDED
    assert completed.local_path == str(target_path)
    assert completed.sha256 == expected_sha256
    assert completed.size_bytes == len(model_bytes)


@pytest.mark.asyncio
async def test_execute_model_sync_public_method_copies_file_and_reports_inventory(
    tmp_path,
) -> None:
    source_path = tmp_path / "source.onnx"
    model_bytes = b"edge model payload"
    source_path.write_bytes(model_bytes)
    target_path = tmp_path / "models" / "yolo26n.onnx"
    expected_sha256 = hashlib.sha256(model_bytes).hexdigest()
    job = _model_job(
        payload={
            "job_type": "model_sync",
            "source_path": str(source_path),
            "target_path": str(target_path),
            "expected_sha256": expected_sha256,
            "size_bytes": len(model_bytes),
        },
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(operations_client=client)

    await executor.execute_model_sync(job)

    assert target_path.read_bytes() == model_bytes
    assert [event.status for _, event in client.events] == [
        ModelLifecycleJobStatus.RUNNING,
        ModelLifecycleJobStatus.SUCCEEDED,
    ]
    assert len(client.completed) == 1
    assert len(client.inventory_reports) == 1


@pytest.mark.asyncio
async def test_model_sync_job_downloads_asset_when_source_path_is_not_local(
    tmp_path,
) -> None:
    target_path = tmp_path / "models" / "yolo26n.onnx"
    model_bytes = b"downloaded model payload"
    expected_sha256 = hashlib.sha256(model_bytes).hexdigest()
    model_id = uuid4()
    job = _model_job(
        model_id=model_id,
        payload={
            "job_type": "model_sync",
            "target_path": str(target_path),
            "expected_sha256": expected_sha256,
            "size_bytes": len(model_bytes),
        },
    )
    client = _FakeOperationsClient([job], download_bytes=model_bytes)
    executor = SupervisorModelJobExecutor(operations_client=client)

    await executor.execute_once()

    assert target_path.read_bytes() == model_bytes
    assert len(client.downloaded_assets) == 1
    assert client.downloaded_assets[0][0] == model_id
    assert Path(client.downloaded_assets[0][1]).parent == target_path.parent
    assert len(client.inventory_reports) == 1


@pytest.mark.asyncio
async def test_model_sync_job_rejects_hash_mismatch(tmp_path) -> None:
    source_path = tmp_path / "source.onnx"
    source_path.write_bytes(b"unexpected model payload")
    target_path = tmp_path / "models" / "yolo26n.onnx"
    job = _model_job(
        payload={
            "job_type": "model_sync",
            "source_path": str(source_path),
            "target_path": str(target_path),
            "expected_sha256": "0" * 64,
            "size_bytes": source_path.stat().st_size,
        },
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(operations_client=client)

    await executor.execute_once()

    assert not target_path.exists()
    failed_events = [
        event for _, event in client.events if event.status is ModelLifecycleJobStatus.FAILED
    ]
    assert len(failed_events) == 1
    assert "SHA-256 mismatch" in (failed_events[0].message or "")
    assert client.inventory_reports == []
    assert len(client.completed) == 1
    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error is not None
    assert "SHA-256 mismatch" in completed.error


@pytest.mark.asyncio
async def test_model_job_executor_ignores_unknown_job_type(tmp_path) -> None:
    job = _model_job(
        payload={
            "job_type": "unknown",
            "target_path": str(tmp_path / "models" / "yolo26n.onnx"),
            "expected_sha256": "a" * 64,
        },
    )
    client = _FakeOperationsClient([job])
    executor = SupervisorModelJobExecutor(operations_client=client)

    await executor.execute_once()

    assert len(client.completed) == 1
    completed = client.completed[0][1]
    assert completed.status is ModelLifecycleJobStatus.FAILED
    assert completed.error is not None
    assert "Unsupported model job type" in completed.error
    failed_events = [
        event for _, event in client.events if event.status is ModelLifecycleJobStatus.FAILED
    ]
    assert len(failed_events) == 1
    assert "Unsupported model job type" in (failed_events[0].message or "")


def _model_job(
    *,
    model_id: UUID | None = None,
    payload: dict[str, object],
) -> DeploymentModelSyncJobResponse:
    now = datetime(2026, 6, 8, 9, 0, tzinfo=UTC)
    return DeploymentModelSyncJobResponse(
        id=uuid4(),
        tenant_id=uuid4(),
        deployment_node_id=uuid4(),
        assignment_id=uuid4(),
        model_id=model_id or uuid4(),
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
    def __init__(
        self,
        jobs: list[DeploymentModelSyncJobResponse],
        *,
        download_bytes: bytes | None = None,
    ) -> None:
        self.jobs = jobs
        self.download_bytes = download_bytes
        self.events: list[tuple[UUID, SupervisorModelJobEventCreate]] = []
        self.completed: list[tuple[UUID, SupervisorModelJobComplete]] = []
        self.inventory_reports: list[DeploymentModelInventoryReport] = []
        self.downloaded_assets: list[tuple[UUID, str]] = []

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
        result: SupervisorModelJobComplete,
    ) -> DeploymentModelSyncJobResponse:
        self.completed.append((job_id, result))
        return self.jobs[0]

    async def record_model_inventory(
        self,
        report: DeploymentModelInventoryReport,
    ) -> DeploymentModelInventoryReport:
        self.inventory_reports.append(report)
        return report

    async def download_model_asset(self, asset_id: UUID, destination_path: str) -> str:
        self.downloaded_assets.append((asset_id, destination_path))
        if self.download_bytes is None:
            raise AssertionError("download_model_asset should not be called for local source paths")
        await anyio.to_thread.run_sync(Path(destination_path).write_bytes, self.download_bytes)
        return destination_path
