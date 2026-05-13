from __future__ import annotations

import os
import platform
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from argus.api.contracts import EdgeNodeHardwareReportCreate, HardwarePerformanceSample
from argus.compat import UTC

ProviderGetter = Callable[[], Sequence[str]]


@dataclass(frozen=True, slots=True)
class HostCapabilityProbe:
    system_getter: Callable[[], str] = platform.system
    machine_getter: Callable[[], str] = platform.machine
    processor_getter: Callable[[], str] = platform.processor
    cpu_count_getter: Callable[[], int | None] = os.cpu_count
    memory_total_mb_getter: Callable[[], int | None] | None = None
    provider_getter: ProviderGetter | None = None
    path_exists: Callable[[str], bool] | None = None
    file_reader: Callable[[str], str] | None = None
    command_runner: Callable[[list[str], float], str] | None = None

    def build_hardware_report(
        self,
        *,
        edge_node_id: UUID | None,
        observed_performance: list[HardwarePerformanceSample],
    ) -> EdgeNodeHardwareReportCreate:
        system = _lower_or_unknown(_safe_call(self.system_getter), "unknown")
        machine = _lower_or_unknown(_safe_call(self.machine_getter), "unknown")
        providers = self._provider_capabilities()
        accelerators = self._accelerators(providers)
        return EdgeNodeHardwareReportCreate(
            edge_node_id=edge_node_id,
            reported_at=datetime.now(tz=UTC),
            host_profile=self._host_profile(system, machine, providers),
            os_name=system,
            machine_arch=machine,
            cpu_model=_safe_str_call(self.processor_getter),
            cpu_cores=_positive_int(_safe_call(self.cpu_count_getter)),
            memory_total_mb=_positive_int(self._memory_total_mb(system)),
            accelerators=accelerators,
            provider_capabilities=providers,
            observed_performance=observed_performance,
            thermal_state=None,
        )

    def _provider_capabilities(self) -> dict[str, bool]:
        getter = self.provider_getter or _default_provider_getter
        providers = _safe_call(getter)
        if not providers:
            return {}
        return {str(provider): True for provider in providers}

    def _host_profile(
        self,
        system: str,
        machine: str,
        providers: dict[str, bool],
    ) -> str:
        if system == "darwin" and machine == "x86_64":
            return "macos-x86_64-intel"
        if system == "darwin" and machine in {"arm64", "aarch64"}:
            return "macos-arm64-apple"
        if system == "linux" and machine in {"aarch64", "arm64"} and self._is_jetson():
            return "linux-aarch64-nvidia-jetson"
        if system == "linux" and machine == "x86_64":
            return (
                "linux-x86_64-nvidia"
                if self._has_nvidia_evidence(providers)
                else "linux-x86_64-intel"
            )
        return f"{system}-{machine}"

    def _accelerators(self, providers: dict[str, bool]) -> list[str]:
        accelerators = {"cpu"}
        provider_keys = {key.lower() for key, enabled in providers.items() if enabled}
        if any("coreml" in key for key in provider_keys):
            accelerators.add("coreml")
        if self._has_nvidia_evidence(providers):
            accelerators.add("nvidia")
        if any("cuda" in key for key in provider_keys):
            accelerators.add("cuda")
        if any("tensorrt" in key for key in provider_keys):
            accelerators.add("tensorrt")
        return sorted(accelerators)

    def _has_nvidia_evidence(self, providers: dict[str, bool]) -> bool:
        provider_keys = {key.lower() for key, enabled in providers.items() if enabled}
        if any("cuda" in key or "tensorrt" in key for key in provider_keys):
            return True
        return self._path_exists("/proc/driver/nvidia/version") or self._is_jetson()

    def _is_jetson(self) -> bool:
        if self._path_exists("/etc/nv_tegra_release"):
            return True
        model = self._read_file("/proc/device-tree/model").lower()
        return "jetson" in model or "nvidia" in model

    def _memory_total_mb(self, system: str) -> int | None:
        if self.memory_total_mb_getter is not None:
            return _safe_call(self.memory_total_mb_getter)
        if system == "darwin":
            output = self._run_command(["sysctl", "-n", "hw.memsize"], timeout=2.0)
            try:
                return int(output.strip()) // (1024 * 1024)
            except (TypeError, ValueError):
                return None
        try:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
        except (AttributeError, OSError, ValueError):
            return None
        if not isinstance(pages, int) or not isinstance(page_size, int):
            return None
        return int(pages * page_size / (1024 * 1024))

    def _path_exists(self, path: str) -> bool:
        exists = self.path_exists or (lambda value: Path(value).exists())
        try:
            return bool(exists(path))
        except OSError:
            return False

    def _read_file(self, path: str) -> str:
        reader = self.file_reader
        try:
            if reader is not None:
                return reader(path)
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def _run_command(self, argv: list[str], *, timeout: float) -> str:
        if self.command_runner is not None:
            return self.command_runner(argv, timeout)
        try:
            result = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        return result.stdout if result.returncode == 0 else ""


def _default_provider_getter() -> Sequence[str]:
    try:
        import onnxruntime as ort  # type: ignore[import-not-found]
    except Exception:
        return []
    try:
        return list(ort.get_available_providers())
    except Exception:
        return []


def _safe_call(callback: Callable[[], object]) -> object | None:
    try:
        return callback()
    except Exception:
        return None


def _safe_str_call(callback: Callable[[], object]) -> str | None:
    value = _safe_call(callback)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _lower_or_unknown(value: object | None, fallback: str) -> str:
    text = str(value or "").strip().lower()
    return text or fallback


def _positive_int(value: object | None) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
