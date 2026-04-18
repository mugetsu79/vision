from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from traffic_monitor.inference.scheduler import CameraWorkerRecord, Scheduler
from traffic_monitor.models.enums import ProcessingMode


@dataclass(slots=True)
class _FakeProcess:
    alive: bool = True

    def poll(self) -> int | None:
        return None if self.alive else 1


class _FakeRepository:
    def __init__(self, records: list[CameraWorkerRecord]) -> None:
        self.records = records

    async def list_cameras(self) -> list[CameraWorkerRecord]:
        return self.records


class _FakeRunner:
    def __init__(self) -> None:
        self.commands: list[tuple[UUID, list[str]]] = []

    def __call__(self, camera_id: UUID, command: list[str]) -> _FakeProcess:
        self.commands.append((camera_id, command))
        return _FakeProcess()


@pytest.mark.asyncio
async def test_scheduler_spawns_workers_for_central_and_hybrid_cameras() -> None:
    central_camera = CameraWorkerRecord(camera_id=uuid4(), mode=ProcessingMode.CENTRAL)
    hybrid_camera = CameraWorkerRecord(camera_id=uuid4(), mode=ProcessingMode.HYBRID)
    edge_camera = CameraWorkerRecord(camera_id=uuid4(), mode=ProcessingMode.EDGE)
    runner = _FakeRunner()
    scheduler = Scheduler(
        repository=_FakeRepository([central_camera, hybrid_camera, edge_camera]),
        process_runner=runner,
    )

    await scheduler.sync()

    assert [camera_id for camera_id, _ in runner.commands] == [
        central_camera.camera_id,
        hybrid_camera.camera_id,
    ]


@pytest.mark.asyncio
async def test_scheduler_restarts_workers_that_exit() -> None:
    camera = CameraWorkerRecord(camera_id=uuid4(), mode=ProcessingMode.CENTRAL)
    runner = _FakeRunner()
    scheduler = Scheduler(repository=_FakeRepository([camera]), process_runner=runner)

    await scheduler.sync()
    scheduler._workers[camera.camera_id].alive = False

    await scheduler.sync()

    assert [camera_id for camera_id, _ in runner.commands] == [camera.camera_id, camera.camera_id]
