from __future__ import annotations

import asyncio
import inspect
import os
import sys
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WorkerProcessResult:
    runtime_state: str
    last_error: str | None = None


class WorkerProcessAdapter(Protocol):
    def is_running(self, camera_id: UUID) -> bool: ...

    async def start(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def stop(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def restart(self, camera_id: UUID) -> WorkerProcessResult: ...

    async def drain(self, camera_id: UUID) -> WorkerProcessResult: ...


SubprocessExec = Callable[..., Awaitable[object]]
BearerTokenProvider = Callable[[], str | Awaitable[str]]


@dataclass(frozen=True, slots=True)
class WorkerLaunchConfig:
    python_executable: str = sys.executable
    module_name: str = "argus.inference.engine"
    api_base_url: str | None = None
    bearer_token: str | None = None
    bearer_token_provider: BearerTokenProvider | None = None
    edge_node_id: UUID | None = None
    extra_env: Mapping[str, str] | None = None
    base_env: Mapping[str, str] | None = None
    graceful_timeout_seconds: float = 10.0


class LocalWorkerProcessAdapter:
    def __init__(
        self,
        config: WorkerLaunchConfig,
        *,
        subprocess_exec: SubprocessExec | None = None,
    ) -> None:
        self.config = config
        self._subprocess_exec = subprocess_exec or asyncio.create_subprocess_exec
        self._processes: dict[UUID, object] = {}
        self.accepting_new_work = True

    def is_running(self, camera_id: UUID) -> bool:
        process = self._processes.get(camera_id)
        return process is not None and _returncode(process) is None

    async def start(self, camera_id: UUID) -> WorkerProcessResult:
        if not self.accepting_new_work:
            return WorkerProcessResult(
                runtime_state="error",
                last_error="Supervisor is draining and is not accepting new work.",
            )
        existing = self._processes.get(camera_id)
        if existing is not None and _returncode(existing) is None:
            return WorkerProcessResult(runtime_state="running")
        argv = self._argv(camera_id)
        try:
            process = await self._subprocess_exec(*argv, env=await self._env())
        except Exception as exc:
            return WorkerProcessResult(runtime_state="error", last_error=str(exc))
        self._processes[camera_id] = process
        return WorkerProcessResult(runtime_state="running")

    async def stop(self, camera_id: UUID) -> WorkerProcessResult:
        process = self._processes.pop(camera_id, None)
        if process is None:
            return WorkerProcessResult(runtime_state="stopped")
        error = await self._terminate(process)
        return WorkerProcessResult(
            runtime_state="error" if error else "stopped",
            last_error=error,
        )

    async def restart(self, camera_id: UUID) -> WorkerProcessResult:
        stopped = await self.stop(camera_id)
        if stopped.last_error:
            return stopped
        return await self.start(camera_id)

    async def drain(self, camera_id: UUID) -> WorkerProcessResult:
        self.accepting_new_work = False
        return await self.stop(camera_id)

    def _argv(self, camera_id: UUID) -> list[str]:
        return [
            self.config.python_executable,
            "-m",
            self.config.module_name,
            "--camera-id",
            str(camera_id),
        ]

    async def _env(self) -> dict[str, str]:
        env = dict(self.config.base_env) if self.config.base_env is not None else dict(os.environ)
        if self.config.api_base_url:
            env["ARGUS_API_BASE_URL"] = self.config.api_base_url
        bearer_token = await self._bearer_token()
        if bearer_token:
            env["ARGUS_API_BEARER_TOKEN"] = bearer_token
        if self.config.edge_node_id is not None:
            env["ARGUS_EDGE_NODE_ID"] = str(self.config.edge_node_id)
        if self.config.extra_env:
            env.update({str(key): str(value) for key, value in self.config.extra_env.items()})
        return env

    async def _bearer_token(self) -> str | None:
        if self.config.bearer_token_provider is None:
            return self.config.bearer_token
        provided = self.config.bearer_token_provider()
        token = await provided if inspect.isawaitable(provided) else provided
        return token or None

    async def _terminate(self, process: object) -> str | None:
        if _returncode(process) is not None:
            return None
        try:
            process.terminate()  # type: ignore[attr-defined]
            await asyncio.wait_for(
                process.wait(),  # type: ignore[attr-defined]
                timeout=self.config.graceful_timeout_seconds,
            )
            return None
        except TimeoutError:
            try:
                process.kill()  # type: ignore[attr-defined]
                await process.wait()  # type: ignore[attr-defined]
                return None
            except Exception as exc:
                return str(exc)
        except Exception as exc:
            return str(exc)


def _returncode(process: object) -> int | None:
    value = getattr(process, "returncode", None)
    return value if isinstance(value, int) else None
