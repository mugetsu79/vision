from __future__ import annotations

import asyncio
import inspect
import os
import signal
import sys
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
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
ProcessFinder = Callable[[UUID], list[object] | Awaitable[list[object]]]


@dataclass(frozen=True, slots=True)
class WorkerMetricsLaunchConfig:
    enabled: bool = False
    bind_addr: str = "127.0.0.1"
    scrape_host: str = "127.0.0.1"
    port_base: int = 19108
    port_count: int = 200


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
    startup_probe_seconds: float = 1.0
    worker_metrics: WorkerMetricsLaunchConfig = field(default_factory=WorkerMetricsLaunchConfig)


class LocalWorkerProcessAdapter:
    def __init__(
        self,
        config: WorkerLaunchConfig,
        *,
        subprocess_exec: SubprocessExec | None = None,
        process_finder: ProcessFinder | None = None,
    ) -> None:
        self.config = config
        self._subprocess_exec = subprocess_exec or asyncio.create_subprocess_exec
        self._process_finder = process_finder
        self._processes: dict[UUID, object] = {}
        self._metrics_ports: dict[UUID, int] = {}
        self._metrics_urls: dict[UUID, str] = {}
        self._allocated_metrics_ports: set[int] = set()
        self.accepting_new_work = True

    def is_running(self, camera_id: UUID) -> bool:
        process = self._processes.get(camera_id)
        return process is not None and _returncode(process) is None

    def metrics_url_for(self, camera_id: UUID) -> str | None:
        if not self.is_running(camera_id):
            return None
        return self._metrics_urls.get(camera_id)

    async def start(self, camera_id: UUID) -> WorkerProcessResult:
        self.accepting_new_work = True
        self._release_dead_processes()
        existing = self._processes.get(camera_id)
        if existing is not None and _returncode(existing) is None:
            return WorkerProcessResult(runtime_state="running")
        if existing is not None:
            self._processes.pop(camera_id, None)
            self._release_worker_metrics(camera_id)
        argv = self._argv(camera_id)
        metrics_port = self._allocate_worker_metrics_port(camera_id)
        if isinstance(metrics_port, WorkerProcessResult):
            return metrics_port
        try:
            process = await self._subprocess_exec(
                *argv,
                env=await self._env(metrics_port=metrics_port),
            )
        except Exception as exc:
            self._release_worker_metrics(camera_id)
            return WorkerProcessResult(runtime_state="error", last_error=str(exc))
        startup_error = await self._startup_error(process)
        if startup_error is not None:
            self._release_worker_metrics(camera_id)
            return WorkerProcessResult(runtime_state="error", last_error=startup_error)
        self._processes[camera_id] = process
        return WorkerProcessResult(runtime_state="running")

    async def stop(self, camera_id: UUID) -> WorkerProcessResult:
        process = self._processes.pop(camera_id, None)
        self._release_worker_metrics(camera_id)
        processes = []
        if process is not None and _returncode(process) is None:
            processes.append(process)
        processes.extend(await self._matching_untracked_processes(camera_id))
        processes = _unique_processes(processes)
        if not processes:
            return WorkerProcessResult(runtime_state="stopped")
        errors = [error for target in processes if (error := await self._terminate(target))]
        remaining = await self._matching_untracked_processes(camera_id)
        if remaining:
            return WorkerProcessResult(
                runtime_state="error",
                last_error="Matching worker process remained after stop.",
            )
        error = "; ".join(errors) if errors else None
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

    async def _env(self, *, metrics_port: int | None = None) -> dict[str, str]:
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
        if metrics_port is not None:
            env["ARGUS_ENABLE_WORKER_METRICS_SERVER"] = "true"
            env["ARGUS_WORKER_METRICS_BIND_ADDR"] = self.config.worker_metrics.bind_addr
            env["ARGUS_WORKER_METRICS_PORT"] = str(metrics_port)
        return env

    def _allocate_worker_metrics_port(self, camera_id: UUID) -> int | WorkerProcessResult | None:
        metrics = self.config.worker_metrics
        if not metrics.enabled:
            return None
        existing_port = self._metrics_ports.get(camera_id)
        if existing_port is not None:
            return existing_port
        for offset in range(metrics.port_count):
            port = metrics.port_base + offset
            if port in self._allocated_metrics_ports:
                continue
            self._allocated_metrics_ports.add(port)
            self._metrics_ports[camera_id] = port
            self._metrics_urls[camera_id] = f"http://{metrics.scrape_host}:{port}/metrics"
            return port
        last_port = metrics.port_base + metrics.port_count - 1
        return WorkerProcessResult(
            runtime_state="error",
            last_error=(
                "No worker metrics ports available in range "
                f"{metrics.port_base}-{last_port}."
            ),
        )

    def _release_worker_metrics(self, camera_id: UUID) -> None:
        port = self._metrics_ports.pop(camera_id, None)
        if port is not None:
            self._allocated_metrics_ports.discard(port)
        self._metrics_urls.pop(camera_id, None)

    def _release_dead_processes(self) -> None:
        dead_camera_ids = [
            camera_id
            for camera_id, process in self._processes.items()
            if _returncode(process) is not None
        ]
        for camera_id in dead_camera_ids:
            self._processes.pop(camera_id, None)
            self._release_worker_metrics(camera_id)

    async def _bearer_token(self) -> str | None:
        if self.config.bearer_token_provider is None:
            return self.config.bearer_token
        provided = self.config.bearer_token_provider()
        token = await provided if inspect.isawaitable(provided) else provided
        return token or None

    async def _matching_untracked_processes(self, camera_id: UUID) -> list[object]:
        if self._process_finder is not None:
            found = self._process_finder(camera_id)
            processes = await found if inspect.isawaitable(found) else found
        else:
            processes = await self._scan_matching_worker_processes(camera_id)
        return [process for process in processes if _returncode(process) is None]

    async def _scan_matching_worker_processes(self, camera_id: UUID) -> list[object]:
        try:
            process = await asyncio.create_subprocess_exec(
                "ps",
                "-eo",
                "pid=,command=",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
        except OSError:
            return []
        stdout, _stderr = await process.communicate()
        if process.returncode != 0:
            return []
        current_pid = os.getpid()
        matches: list[object] = []
        camera_marker = str(camera_id)
        for raw_line in stdout.decode("utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            pid_text, _, command = line.partition(" ")
            try:
                pid = int(pid_text)
            except ValueError:
                continue
            if pid == current_pid:
                continue
            if self.config.module_name not in command:
                continue
            if "--camera-id" not in command:
                continue
            if camera_marker not in command:
                continue
            matches.append(_ExternalWorkerProcess(pid))
        return matches

    async def _startup_error(self, process: object) -> str | None:
        await asyncio.sleep(max(self.config.startup_probe_seconds, 0.0))
        returncode = _returncode(process)
        if returncode is None:
            return None
        try:
            await process.wait()  # type: ignore[attr-defined]
        except Exception:
            pass
        return f"Worker exited during startup with code {returncode}."

    async def _terminate(self, process: object) -> str | None:
        if _returncode(process) is not None:
            return None
        try:
            process.terminate()  # type: ignore[attr-defined]
            await asyncio.wait_for(
                process.wait(),  # type: ignore[attr-defined]
                timeout=self.config.graceful_timeout_seconds,
            )
            if _returncode(process) is None:
                process.kill()  # type: ignore[attr-defined]
                await process.wait()  # type: ignore[attr-defined]
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


def _unique_processes(processes: list[object]) -> list[object]:
    unique: list[object] = []
    seen_objects: set[int] = set()
    seen_pids: set[int] = set()
    for process in processes:
        pid = getattr(process, "pid", None)
        if isinstance(pid, int):
            if pid in seen_pids:
                continue
            seen_pids.add(pid)
            unique.append(process)
            continue
        object_id = id(process)
        if object_id in seen_objects:
            continue
        seen_objects.add(object_id)
        unique.append(process)
    return unique


class _ExternalWorkerProcess:
    def __init__(self, pid: int) -> None:
        self.pid = pid
        self._returncode: int | None = None

    @property
    def returncode(self) -> int | None:
        if self._returncode is not None:
            return self._returncode
        if not self._alive():
            self._returncode = 0
        return self._returncode

    def terminate(self) -> None:
        self._signal(signal.SIGTERM)

    def kill(self) -> None:
        self._signal(signal.SIGKILL)

    async def wait(self) -> int:
        for _ in range(100):
            if self.returncode is not None:
                return self.returncode
            await asyncio.sleep(0.05)
        return self.returncode or 0

    def _signal(self, sig: signal.Signals) -> None:
        try:
            os.kill(self.pid, sig)
        except ProcessLookupError:
            self._returncode = 0

    def _alive(self) -> bool:
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
