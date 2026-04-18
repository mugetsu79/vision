from __future__ import annotations

from importlib import import_module
from typing import Any

PROVIDER_PRIORITY: tuple[str, ...] = (
    "TensorrtExecutionProvider",
    "CUDAExecutionProvider",
    "OpenVINOExecutionProvider",
    "CoreMLExecutionProvider",
    "CPUExecutionProvider",
)


def import_onnxruntime() -> Any:
    return import_module("onnxruntime")


def select_execution_provider(runtime: Any) -> str:
    available_providers = [str(provider) for provider in runtime.get_available_providers()]
    for provider_name in PROVIDER_PRIORITY:
        if provider_name in available_providers:
            return provider_name

    if not available_providers:
        raise RuntimeError("No ONNX execution providers are available.")

    return available_providers[0]
