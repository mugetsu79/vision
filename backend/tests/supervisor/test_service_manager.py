from __future__ import annotations

from pathlib import Path

from argus.models.enums import DeploymentServiceManager
from argus.supervisor.service_manager import CommandResult, detect_service_manager


def test_linux_detects_systemd_with_runtime_evidence() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> CommandResult:
        calls.append(command)
        return CommandResult(returncode=0, stdout="systemd 255", stderr="")

    detection = detect_service_manager(
        platform_system="Linux",
        environ={},
        path_exists=lambda path: path == Path("/run/systemd/system"),
        command_runner=runner,
    )

    assert detection.manager is DeploymentServiceManager.SYSTEMD
    assert detection.production_ready is True
    assert detection.development_only is False
    assert calls == [["systemctl", "--version"]]


def test_macos_detects_launchd_without_shelling_out() -> None:
    def runner(command: list[str]) -> CommandResult:
        raise AssertionError(f"unexpected command: {command}")

    detection = detect_service_manager(
        platform_system="Darwin",
        environ={},
        path_exists=lambda path: False,
        command_runner=runner,
    )

    assert detection.manager is DeploymentServiceManager.LAUNCHD
    assert detection.production_ready is True


def test_containerized_deployments_report_compose() -> None:
    detection = detect_service_manager(
        platform_system="Linux",
        environ={"VEZOR_SUPERVISOR_SERVICE_MANAGER": "compose"},
        path_exists=lambda path: False,
        command_runner=lambda command: CommandResult(returncode=1, stdout="", stderr=""),
    )

    assert detection.manager is DeploymentServiceManager.COMPOSE
    assert detection.production_ready is True
    assert detection.detail == "Supervisor service manager is configured as compose."


def test_unknown_platform_falls_back_to_direct_child_for_development_only() -> None:
    detection = detect_service_manager(
        platform_system="FreeBSD",
        environ={},
        path_exists=lambda path: False,
        command_runner=lambda command: CommandResult(returncode=1, stdout="", stderr=""),
    )

    assert detection.manager is DeploymentServiceManager.DIRECT_CHILD
    assert detection.production_ready is False
    assert detection.development_only is True
    assert "development" in detection.detail.lower()


def test_detection_never_passes_untrusted_input_to_command_runner() -> None:
    calls: list[list[str]] = []

    def runner(command: list[str]) -> CommandResult:
        calls.append(command)
        return CommandResult(returncode=0, stdout="systemd 255", stderr="")

    detect_service_manager(
        platform_system="Linux; rm -rf /",
        environ={"PATH": "/tmp/evil", "VEZOR_SUPERVISOR_ID": "$(touch bad)"},
        path_exists=lambda path: path == Path("/run/systemd/system"),
        command_runner=runner,
    )

    assert calls == [["systemctl", "--version"]]
    assert all("; " not in part and "$(" not in part for call in calls for part in call)
