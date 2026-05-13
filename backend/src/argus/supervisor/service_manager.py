from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from argus.models.enums import DeploymentServiceManager


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]
PathExists = Callable[[Path], bool]


@dataclass(frozen=True, slots=True)
class ServiceManagerDetection:
    manager: DeploymentServiceManager
    production_ready: bool
    development_only: bool
    detail: str


def detect_service_manager(
    *,
    platform_system: str | None = None,
    environ: Mapping[str, str] | None = None,
    path_exists: PathExists | None = None,
    command_runner: CommandRunner | None = None,
) -> ServiceManagerDetection:
    env = environ if environ is not None else os.environ
    configured = env.get("VEZOR_SUPERVISOR_SERVICE_MANAGER")
    if configured == DeploymentServiceManager.COMPOSE.value:
        return ServiceManagerDetection(
            manager=DeploymentServiceManager.COMPOSE,
            production_ready=True,
            development_only=False,
            detail="Supervisor service manager is configured as compose.",
        )

    system = (platform_system or platform.system()).lower()
    exists = path_exists or Path.exists
    runner = command_runner or _run_command

    if "darwin" in system:
        return ServiceManagerDetection(
            manager=DeploymentServiceManager.LAUNCHD,
            production_ready=True,
            development_only=False,
            detail="macOS launchd can own the Vezor supervisor daemon.",
        )

    if "linux" in system and exists(Path("/run/systemd/system")):
        result = runner(["systemctl", "--version"])
        if result.returncode == 0:
            return ServiceManagerDetection(
                manager=DeploymentServiceManager.SYSTEMD,
                production_ready=True,
                development_only=False,
                detail="Linux systemd can own the Vezor supervisor service.",
            )

    return ServiceManagerDetection(
        manager=DeploymentServiceManager.DIRECT_CHILD,
        production_ready=False,
        development_only=True,
        detail=(
            "No production service manager was detected; direct_child is for "
            "local development, smoke tests, and break-glass operation only."
        ),
    )


def _run_command(command: list[str]) -> CommandResult:
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell.
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
