from __future__ import annotations

from uuid import uuid4

from argus.api.contracts import HardwarePerformanceSample
from argus.supervisor.hardware_probe import HostCapabilityProbe


def test_darwin_x86_64_intel_reports_coreml_capability() -> None:
    probe = HostCapabilityProbe(
        system_getter=lambda: "Darwin",
        machine_getter=lambda: "x86_64",
        processor_getter=lambda: "Intel Core i9",
        cpu_count_getter=lambda: 8,
        memory_total_mb_getter=lambda: 32768,
        provider_getter=lambda: ["CoreMLExecutionProvider", "CPUExecutionProvider"],
    )

    report = probe.build_hardware_report(
        edge_node_id=None,
        observed_performance=[
            HardwarePerformanceSample(
                model_name="YOLO26n COCO",
                runtime_backend="CoreMLExecutionProvider",
                input_width=1280,
                input_height=720,
                target_fps=10,
                stage_p95_ms={"total": 92.0},
                stage_p99_ms={"total": 108.0},
            )
        ],
    )

    assert report.host_profile == "macos-x86_64-intel"
    assert report.os_name == "darwin"
    assert report.machine_arch == "x86_64"
    assert report.cpu_model == "Intel Core i9"
    assert report.cpu_cores == 8
    assert report.memory_total_mb == 32768
    assert report.provider_capabilities["CoreMLExecutionProvider"] is True
    assert "coreml" in report.accelerators
    assert report.observed_performance[0].stage_p95_ms["total"] == 92.0


def test_linux_aarch64_jetson_reports_nvidia_cuda_tensorrt_capability() -> None:
    probe = HostCapabilityProbe(
        system_getter=lambda: "Linux",
        machine_getter=lambda: "aarch64",
        processor_getter=lambda: "NVIDIA Orin",
        cpu_count_getter=lambda: 6,
        memory_total_mb_getter=lambda: 8192,
        provider_getter=lambda: [
            "TensorrtExecutionProvider",
            "CUDAExecutionProvider",
            "CPUExecutionProvider",
        ],
        path_exists=lambda path: path == "/etc/nv_tegra_release",
        file_reader=lambda path: "R36 (release), REVISION: 4.0" if path else "",
    )
    edge_node_id = uuid4()

    report = probe.build_hardware_report(edge_node_id=edge_node_id, observed_performance=[])

    assert report.edge_node_id == edge_node_id
    assert report.host_profile == "linux-aarch64-nvidia-jetson"
    assert report.provider_capabilities["TensorrtExecutionProvider"] is True
    assert {"nvidia", "cuda", "tensorrt"}.issubset(set(report.accelerators))


def test_linux_x86_64_nvidia_profile_uses_cuda_provider_evidence() -> None:
    probe = HostCapabilityProbe(
        system_getter=lambda: "Linux",
        machine_getter=lambda: "x86_64",
        processor_getter=lambda: "Intel Xeon",
        cpu_count_getter=lambda: 16,
        memory_total_mb_getter=lambda: 65536,
        provider_getter=lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    report = probe.build_hardware_report(edge_node_id=None, observed_performance=[])

    assert report.host_profile == "linux-x86_64-nvidia"
    assert "cuda" in report.accelerators
    assert report.provider_capabilities["CUDAExecutionProvider"] is True


def test_probe_failures_return_conservative_valid_report() -> None:
    def _boom() -> list[str]:
        raise RuntimeError("provider import failed")

    probe = HostCapabilityProbe(
        system_getter=lambda: "Plan9",
        machine_getter=lambda: "mips",
        processor_getter=lambda: (_ for _ in ()).throw(RuntimeError("processor failed")),
        cpu_count_getter=lambda: None,
        memory_total_mb_getter=lambda: (_ for _ in ()).throw(RuntimeError("memory failed")),
        provider_getter=_boom,
        path_exists=lambda path: (_ for _ in ()).throw(OSError(path)),
        file_reader=lambda path: (_ for _ in ()).throw(OSError(path)),
    )

    report = probe.build_hardware_report(edge_node_id=None, observed_performance=[])

    assert report.host_profile == "plan9-mips"
    assert report.os_name == "plan9"
    assert report.machine_arch == "mips"
    assert report.cpu_model is None
    assert report.cpu_cores is None
    assert report.memory_total_mb is None
    assert report.provider_capabilities == {}
    assert report.accelerators == ["cpu"]
