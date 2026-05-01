from __future__ import annotations

from dataclasses import dataclass

import pytest

from argus.vision.runtime import (
    CpuVendor,
    ExecutionProfile,
    ExecutionProvider,
    resolve_execution_policy,
)


@dataclass(slots=True)
class _FakeRuntime:
    providers: list[str]

    def get_available_providers(self) -> list[str]:
        return list(self.providers)


def test_runtime_policy_prefers_tensorrt_for_linux_x86_nvidia_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
                ExecutionProvider.TENSORRT.value,
            ]
        ),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.INTEL,
    )

    assert policy.profile is ExecutionProfile.NVIDIA_LINUX_X86_64
    assert policy.provider == ExecutionProvider.TENSORRT.value
    assert policy.host.cpu_vendor is CpuVendor.INTEL


def test_runtime_policy_prefers_tensorrt_for_linux_aarch64_jetson_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
                ExecutionProvider.TENSORRT.value,
            ]
        ),
        system="Linux",
        machine="aarch64",
        cpu_vendor=CpuVendor.UNKNOWN,
    )

    assert policy.profile is ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
    assert policy.provider == ExecutionProvider.TENSORRT.value


def test_runtime_policy_prefers_cuda_for_linux_arm64_jetson_without_tensorrt() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.CPU.value,
                ExecutionProvider.CUDA.value,
            ]
        ),
        system="Linux",
        machine="arm64",
        cpu_vendor=CpuVendor.UNKNOWN,
    )

    assert policy.profile is ExecutionProfile.LINUX_AARCH64_NVIDIA_JETSON
    assert policy.provider == ExecutionProvider.CUDA.value


def test_runtime_policy_prefers_coreml_for_macos_arm64_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.COREML.value,
                ExecutionProvider.CPU.value,
            ]
        ),
        system="Darwin",
        machine="arm64",
    )

    assert policy.profile is ExecutionProfile.MACOS_APPLE_SILICON
    assert policy.provider == ExecutionProvider.COREML.value
    assert policy.host.cpu_vendor is CpuVendor.APPLE


def test_runtime_policy_prefers_coreml_for_macos_x86_hosts_when_available() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.COREML.value,
                ExecutionProvider.CPU.value,
            ]
        ),
        system="Darwin",
        machine="x86_64",
        cpu_vendor=CpuVendor.INTEL,
    )

    assert policy.profile is ExecutionProfile.MACOS_X86_64_INTEL
    assert policy.provider == ExecutionProvider.COREML.value
    assert policy.host.cpu_vendor is CpuVendor.INTEL


def test_runtime_policy_prefers_openvino_for_linux_x86_intel_hosts() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.OPENVINO.value,
                ExecutionProvider.CPU.value,
            ]
        ),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.INTEL,
    )

    assert policy.profile is ExecutionProfile.LINUX_X86_64_INTEL
    assert policy.provider == ExecutionProvider.OPENVINO.value


def test_runtime_policy_falls_back_to_cpu_for_linux_x86_amd_hosts_even_with_openvino() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.OPENVINO.value,
                ExecutionProvider.CPU.value,
            ]
        ),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.AMD,
    )

    assert policy.profile is ExecutionProfile.LINUX_X86_64_AMD
    assert policy.provider == ExecutionProvider.CPU.value


def test_runtime_policy_falls_back_to_cpu_when_accelerated_provider_is_missing() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(providers=[ExecutionProvider.CPU.value]),
        system="Linux",
        machine="x86_64",
        cpu_vendor=CpuVendor.INTEL,
    )

    assert policy.provider == ExecutionProvider.CPU.value


def test_runtime_policy_explicit_override_wins_when_provider_is_available() -> None:
    policy = resolve_execution_policy(
        _FakeRuntime(
            providers=[
                ExecutionProvider.COREML.value,
                ExecutionProvider.CPU.value,
            ]
        ),
        system="Darwin",
        machine="arm64",
        execution_provider_override=ExecutionProvider.CPU,
    )

    assert policy.profile is ExecutionProfile.MACOS_APPLE_SILICON
    assert policy.provider == ExecutionProvider.CPU.value
    assert policy.provider_overridden is True


def test_runtime_policy_rejects_unavailable_valid_override() -> None:
    with pytest.raises(RuntimeError, match="Execution provider override"):
        resolve_execution_policy(
            _FakeRuntime(providers=[ExecutionProvider.CPU.value]),
            system="Darwin",
            machine="arm64",
            execution_provider_override=ExecutionProvider.COREML,
        )
