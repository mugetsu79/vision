from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID, uuid4

import anyio

from argus.api.contracts import (
    DeploymentModelInventoryReport,
    DeploymentModelSyncJobResponse,
    SupervisorModelJobComplete,
    SupervisorModelJobEventCreate,
)
from argus.compat import UTC
from argus.models.enums import ModelLifecycleJobStatus
from argus.supervisor.model_inventory import InventoryScanner


class ModelJobOperationsClient(Protocol):
    async def poll_model_jobs(self, limit: int = 10) -> list[DeploymentModelSyncJobResponse]: ...

    async def record_model_job_event(
        self,
        job_id: UUID,
        event: SupervisorModelJobEventCreate,
    ) -> DeploymentModelSyncJobResponse: ...

    async def complete_model_job(
        self,
        job_id: UUID,
        completion: SupervisorModelJobComplete,
    ) -> DeploymentModelSyncJobResponse: ...

    async def record_model_inventory(
        self,
        report: DeploymentModelInventoryReport,
    ) -> DeploymentModelInventoryReport: ...

    async def download_model_asset(self, asset_id: UUID, destination_path: str | Path) -> Path: ...


class SupervisorModelJobExecutor:
    def __init__(
        self,
        *,
        operations_client: ModelJobOperationsClient,
        limit: int = 10,
        reported_at: Callable[[], datetime] | None = None,
    ) -> None:
        self.operations_client = operations_client
        self.limit = limit
        self.reported_at = reported_at or (lambda: datetime.now(tz=UTC))

    async def execute_once(self) -> int:
        jobs = await self.operations_client.poll_model_jobs(limit=self.limit)
        completed = 0
        for job in jobs:
            await self._execute_job(job)
            completed += 1
        return completed

    async def _execute_job(self, job: DeploymentModelSyncJobResponse) -> None:
        await self._record_event(
            job,
            ModelLifecycleJobStatus.ACCEPTED,
            "Accepted model sync job.",
        )
        try:
            job_type = _string(job.payload.get("job_type"))
            if job_type != "model_sync":
                await self._fail_job(job, f"Unsupported model job type: {job_type or 'missing'}.")
                return
            await self.execute_model_sync(job)
        except Exception as exc:
            await self._fail_job(job, str(exc))

    async def execute_model_sync(self, job: DeploymentModelSyncJobResponse) -> None:
        source_path = _path_field(job.payload, "source_path")
        target_path = _path_field(job.payload, "target_path")
        expected_sha256 = _optional_string(job.payload.get("expected_sha256"))
        expected_size = _optional_int(job.payload.get("size_bytes"))
        if target_path is None:
            raise ValueError("Model sync job is missing target_path.")

        await self._record_event(
            job,
            ModelLifecycleJobStatus.RUNNING,
            "Staging model file.",
            payload={
                "source_path": str(source_path) if source_path is not None else None,
                "target_path": str(target_path),
            },
        )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = target_path.with_name(f".{target_path.name}.{uuid4().hex}.tmp")
        try:
            observed_sha256, observed_size = await self._stage_model_file(
                job=job,
                source_path=source_path,
                temporary_path=temporary_path,
            )
            _verify_model_file(
                expected_sha256=expected_sha256,
                observed_sha256=observed_sha256,
                expected_size=expected_size,
                observed_size=observed_size,
            )
            temporary_path.replace(target_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        await self._record_event(
            job,
            ModelLifecycleJobStatus.SUCCEEDED,
            "Model file synced.",
            payload={
                "local_path": str(target_path),
                "sha256": observed_sha256,
                "size_bytes": observed_size,
            },
        )
        await self.operations_client.complete_model_job(
            job.id,
            SupervisorModelJobComplete(
                status=ModelLifecycleJobStatus.SUCCEEDED,
                local_path=str(target_path),
                path=str(target_path),
                sha256=observed_sha256,
                size_bytes=observed_size,
            ),
        )
        await self._record_inventory(
            job=job,
            local_path=target_path,
        )

    async def _record_inventory(
        self,
        *,
        job: DeploymentModelSyncJobResponse,
        local_path: Path,
    ) -> None:
        scanner = InventoryScanner(
            reported_at=self.reported_at,
            target_profile=_optional_string(job.payload.get("target_profile")),
            runtime_versions=_mapping_or_none(job.payload.get("runtime_versions")),
        )
        items = scanner.scan_models(
            [
                {
                    "asset_id": job.model_id,
                    "local_path": local_path,
                }
            ]
        )
        if items:
            await self.operations_client.record_model_inventory(
                DeploymentModelInventoryReport(items=items)
            )

    async def _stage_model_file(
        self,
        *,
        job: DeploymentModelSyncJobResponse,
        source_path: Path | None,
        temporary_path: Path,
    ) -> tuple[str, int]:
        if source_path is not None and await anyio.to_thread.run_sync(
            _is_regular_file,
            source_path,
        ):
            return _copy_with_hash(source_path, temporary_path)
        await self.operations_client.download_model_asset(job.model_id, temporary_path)
        if not await anyio.to_thread.run_sync(_is_regular_file, temporary_path):
            raise ValueError("Downloaded model asset was not written to the staging path.")
        return _hash_existing_file(temporary_path)

    async def _fail_job(self, job: DeploymentModelSyncJobResponse, message: str) -> None:
        await self._record_event(job, ModelLifecycleJobStatus.FAILED, message)
        await self.operations_client.complete_model_job(
            job.id,
            SupervisorModelJobComplete(
                status=ModelLifecycleJobStatus.FAILED,
                error=message,
            ),
        )

    async def _record_event(
        self,
        job: DeploymentModelSyncJobResponse,
        status: ModelLifecycleJobStatus,
        message: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> None:
        await self.operations_client.record_model_job_event(
            job.id,
            SupervisorModelJobEventCreate(
                job_kind="model_sync",
                status=status,
                message=message,
                payload=payload or {},
            ),
        )


def _copy_with_hash(source_path: Path, temporary_path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size_bytes = 0
    with source_path.open("rb") as source, temporary_path.open("wb") as target:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
            size_bytes += len(chunk)
            target.write(chunk)
    return digest.hexdigest(), size_bytes


def _hash_existing_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size_bytes = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size_bytes += len(chunk)
    return digest.hexdigest(), size_bytes


def _is_regular_file(path: Path) -> bool:
    return path.exists() and path.is_file()


def _verify_model_file(
    *,
    expected_sha256: str | None,
    observed_sha256: str,
    expected_size: int | None,
    observed_size: int,
) -> None:
    if expected_sha256 is not None and observed_sha256 != expected_sha256:
        raise ValueError(
            f"SHA-256 mismatch for synced model: expected {expected_sha256}, "
            f"got {observed_sha256}."
        )
    if expected_size is not None and observed_size != expected_size:
        raise ValueError(
            f"Size mismatch for synced model: expected {expected_size}, got {observed_size}."
        )


def _path_field(payload: Mapping[str, Any], key: str) -> Path | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return Path(value)
    return None


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _optional_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _mapping_or_none(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None
