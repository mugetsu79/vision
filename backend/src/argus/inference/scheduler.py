from __future__ import annotations

import asyncio
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.models.enums import ProcessingMode
from argus.models.tables import Camera


@dataclass(slots=True, frozen=True)
class CameraWorkerRecord:
    camera_id: UUID
    mode: ProcessingMode


class ProcessHandle(Protocol):
    def poll(self) -> int | None: ...


class CameraWorkerRepository(Protocol):
    async def list_cameras(self) -> list[CameraWorkerRecord]: ...


class DatabaseCameraWorkerRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def list_cameras(self) -> list[CameraWorkerRecord]:
        async with self.session_factory() as session:
            result = await session.execute(
                select(Camera.id, Camera.processing_mode).where(
                    Camera.processing_mode.in_((ProcessingMode.CENTRAL, ProcessingMode.HYBRID))
                )
            )
        return [
            CameraWorkerRecord(camera_id=camera_id, mode=mode)
            for camera_id, mode in result.all()
        ]


class Scheduler:
    def __init__(
        self,
        *,
        repository: CameraWorkerRepository,
        process_runner: Callable[[UUID, list[str]], ProcessHandle] | None = None,
        python_executable: str = sys.executable,
    ) -> None:
        self.repository = repository
        self._process_runner = process_runner or self._default_process_runner
        self._python_executable = python_executable
        self._workers: dict[UUID, ProcessHandle] = {}

    async def sync(self) -> None:
        records = await self.repository.list_cameras()
        desired: dict[UUID, CameraWorkerRecord] = {
            record.camera_id: record
            for record in records
            if record.mode in {ProcessingMode.CENTRAL, ProcessingMode.HYBRID}
        }

        for camera_id in desired:
            process = self._workers.get(camera_id)
            if process is None or process.poll() is not None:
                self._workers[camera_id] = self._process_runner(camera_id, self._command(camera_id))

        for camera_id in list(self._workers):
            if camera_id not in desired:
                self._workers.pop(camera_id, None)

    async def serve(self, *, interval_seconds: float = 5.0) -> None:
        while True:
            await self.sync()
            await asyncio.sleep(interval_seconds)

    def _command(self, camera_id: UUID) -> list[str]:
        return [
            self._python_executable,
            "-m",
            "argus.inference.engine",
            "--camera-id",
            str(camera_id),
        ]

    def _default_process_runner(self, camera_id: UUID, command: list[str]) -> ProcessHandle:
        return subprocess.Popen(command)  # noqa: S603
