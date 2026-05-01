from __future__ import annotations

import platform
from dataclasses import dataclass
from enum import StrEnum
from importlib import import_module
from pathlib import Path
from typing import Any


class ExecutionProvider(StrEnum):
    TENSORRT = "TensorrtExecutionProvider"
    CUDA = "CUDAExecutionProvider"
    OPENVINO = "OpenVINOExecutionProvider"
    COREML = "CoreMLExecutionProvider"
    CPU = "CPUExecutionProvider"


class CpuVendor(StrEnum):
    UNKNOWN = "unknown"
    INTEL = "intel"
    AMD = "amd"
    APPLE = "apple"


class ExecutionProfile(StrEnum):
    NVIDIA_LINUX_X86_64 = "linux-x86_64-nvidia"
    LINUX_AARCH64_NVIDIA_JETSON = "linux-aarch64-nvidia-jetson"
    MACOS_APPLE_SILICON = "macos-arm64-apple-silicon"
    LINUX_X86_64_INTEL = "linux-x86_64-intel"
    LINUX_X86_64_AMD = "linux-x86_64-amd"
    MACOS_X86_64_INTEL = "macos-x86_64-intel"
    CPU_FALLBACK = "cpu-fallback"


@dataclass(frozen=True, slots=True)
class HostClassification:
    system: str
    machine: str
    cpu_vendor: CpuVendor
    available_providers: tuple[str, ...]
    profile: ExecutionProfile
    profile_overridden: bool = False


@dataclass(frozen=True, slots=True)
class RuntimeExecutionPolicy:
    host: HostClassification
    provider: str
    available_providers: tuple[str, ...]
    provider_overridden: bool
    inter_op_threads: int | None = None
    intra_op_threads: int | None = None

    @property
    def profile(self) -> ExecutionProfile:
        return self.host.profile

    @property
    def profile_overridden(self) -> bool:
        return self.host.profile_overridden


_PROFILE_PROVIDER_PRIORITY: dict[ExecutionProfile, tuple[ExecutionProvider, ...]] = {
    ExecutionProfile.NVIDIA_LINUX_X86_64: (
        ExecutionProvider.TENSORRT,
        ExecutionProvider.CUDA,
        ExecutionProvider.CPU,
    ),
    ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON: (
        ExecutionProvider.TENSORRT,
        ExecutionProvider.CUDA,
        ExecutionProvider.CPU,
    ),
    ExecutionProfile.MACOS_APPLE_SILICON: (
        ExecutionProvider.COREML,
        ExecutionProvider.CPU,
    ),
    ExecutionProfile.LINUX_X86_64_INTEL: (
        ExecutionProvider.OPENVINO,
        ExecutionProvider.CPU,
    ),
    ExecutionProfile.LINUX_X86_64_AMD: (ExecutionProvider.CPU,),
    ExecutionProfile.MACOS_X86_64_INTEL: (
        ExecutionProvider.COREML,
        ExecutionProvider.CPU,
    ),
    ExecutionProfile.CPU_FALLBACK: (ExecutionProvider.CPU,),
}


def import_onnxruntime() -> Any:
    return import_module("onnxruntime")


def resolve_execution_policy(
    runtime: Any,
    *,
    execution_provider_override: ExecutionProvider | None = None,
    execution_profile_override: ExecutionProfile | None = None,
    inter_op_threads: int | None = None,
    intra_op_threads: int | None = None,
    system: str | None = None,
    machine: str | None = None,
    cpu_vendor: CpuVendor | str | None = None,
    cpuinfo_text: str | None = None,
) -> RuntimeExecutionPolicy:
    available_providers = tuple(str(provider) for provider in runtime.get_available_providers())
    host = classify_host(
        available_providers=available_providers,
        execution_profile_override=execution_profile_override,
        system=system,
        machine=machine,
        cpu_vendor=cpu_vendor,
        cpuinfo_text=cpuinfo_text,
    )

    if execution_provider_override is not None:
        provider_name = execution_provider_override.value
        if provider_name not in available_providers:
            raise RuntimeError(
                "Execution provider override "
                f"{provider_name!r} is not available on this host. "
                f"Available providers: {list(available_providers)!r}"
            )
        provider_overridden = True
    else:
        provider_name = _select_provider_for_profile(
            profile=host.profile,
            available_providers=available_providers,
        )
        provider_overridden = False

    return RuntimeExecutionPolicy(
        host=host,
        provider=provider_name,
        available_providers=available_providers,
        provider_overridden=provider_overridden,
        inter_op_threads=inter_op_threads,
        intra_op_threads=intra_op_threads,
    )


def classify_host(
    *,
    available_providers: tuple[str, ...],
    execution_profile_override: ExecutionProfile | None = None,
    system: str | None = None,
    machine: str | None = None,
    cpu_vendor: CpuVendor | str | None = None,
    cpuinfo_text: str | None = None,
) -> HostClassification:
    resolved_system = (system or platform.system()).strip().lower()
    resolved_machine = (machine or platform.machine()).strip().lower()
    resolved_cpu_vendor = normalize_cpu_vendor(
        cpu_vendor
        or detect_cpu_vendor(
            system=resolved_system,
            machine=resolved_machine,
            cpuinfo_text=cpuinfo_text,
        )
    )

    if execution_profile_override is not None:
        profile = execution_profile_override
        profile_overridden = True
    elif (
        resolved_system == "linux"
        and resolved_machine == "x86_64"
        and any(
            provider in available_providers
            for provider in (
                ExecutionProvider.TENSORRT.value,
                ExecutionProvider.CUDA.value,
            )
        )
    ):
        profile = ExecutionProfile.NVIDIA_LINUX_X86_64
        profile_overridden = False
    elif (
        resolved_system == "linux"
        and resolved_machine in {"aarch64", "arm64"}
        and any(
            provider in available_providers
            for provider in (
                ExecutionProvider.TENSORRT.value,
                ExecutionProvider.CUDA.value,
            )
        )
    ):
        profile = ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
        profile_overridden = False
    elif resolved_system == "darwin" and resolved_machine in {"arm64", "aarch64"}:
        profile = ExecutionProfile.MACOS_APPLE_SILICON
        profile_overridden = False
        if resolved_cpu_vendor is CpuVendor.UNKNOWN:
            resolved_cpu_vendor = CpuVendor.APPLE
    elif (
        resolved_system == "linux"
        and resolved_machine == "x86_64"
        and resolved_cpu_vendor is CpuVendor.INTEL
    ):
        profile = ExecutionProfile.LINUX_X86_64_INTEL
        profile_overridden = False
    elif (
        resolved_system == "linux"
        and resolved_machine == "x86_64"
        and resolved_cpu_vendor is CpuVendor.AMD
    ):
        profile = ExecutionProfile.LINUX_X86_64_AMD
        profile_overridden = False
    elif resolved_system == "darwin" and resolved_machine == "x86_64":
        profile = ExecutionProfile.MACOS_X86_64_INTEL
        profile_overridden = False
        if resolved_cpu_vendor is CpuVendor.UNKNOWN:
            resolved_cpu_vendor = CpuVendor.INTEL
    else:
        profile = ExecutionProfile.CPU_FALLBACK
        profile_overridden = False

    return HostClassification(
        system=resolved_system,
        machine=resolved_machine,
        cpu_vendor=resolved_cpu_vendor,
        available_providers=available_providers,
        profile=profile,
        profile_overridden=profile_overridden,
    )


def create_session_options(runtime: Any, *, policy: RuntimeExecutionPolicy) -> Any | None:
    session_options_factory = getattr(runtime, "SessionOptions", None)
    if session_options_factory is None:
        return None

    session_options = session_options_factory()
    if policy.inter_op_threads is not None:
        session_options.inter_op_num_threads = policy.inter_op_threads
    if policy.intra_op_threads is not None:
        session_options.intra_op_num_threads = policy.intra_op_threads
    return session_options


def select_execution_provider(runtime: Any) -> str:
    return resolve_execution_policy(runtime).provider


def normalize_cpu_vendor(cpu_vendor: CpuVendor | str | None) -> CpuVendor:
    if isinstance(cpu_vendor, CpuVendor):
        return cpu_vendor
    if cpu_vendor is None:
        return CpuVendor.UNKNOWN

    normalized = str(cpu_vendor).strip().lower()
    if normalized in {"intel", "genuineintel"}:
        return CpuVendor.INTEL
    if normalized in {"amd", "authenticamd"}:
        return CpuVendor.AMD
    if normalized in {"apple"}:
        return CpuVendor.APPLE
    return CpuVendor.UNKNOWN


def detect_cpu_vendor(
    *,
    system: str,
    machine: str,
    cpuinfo_text: str | None = None,
) -> CpuVendor:
    if system == "darwin" and machine in {"arm64", "aarch64"}:
        return CpuVendor.APPLE
    if system == "darwin" and machine == "x86_64":
        return CpuVendor.INTEL

    inspection_text = cpuinfo_text
    if inspection_text is None:
        inspection_text = _read_cpuinfo_text()
    normalized = inspection_text.lower()

    if "genuineintel" in normalized or "intel" in normalized:
        return CpuVendor.INTEL
    if "authenticamd" in normalized or "amd" in normalized:
        return CpuVendor.AMD
    return CpuVendor.UNKNOWN


def _read_cpuinfo_text() -> str:
    cpuinfo_path = Path("/proc/cpuinfo")
    if not cpuinfo_path.exists():
        return ""
    try:
        return cpuinfo_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _select_provider_for_profile(
    *,
    profile: ExecutionProfile,
    available_providers: tuple[str, ...],
) -> str:
    for provider in _PROFILE_PROVIDER_PRIORITY[profile]:
        if provider.value in available_providers:
            return provider.value

    if not available_providers:
        raise RuntimeError("No ONNX execution providers are available.")

    return available_providers[0]
