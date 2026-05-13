from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkerProcessResult:
    runtime_state: str
    last_error: str | None = None


class WorkerProcessAdapter(Protocol):
    async def start(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def stop(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def restart(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def drain(self, camera_id: UUID) -> WorkerProcessResult: ...
