from __future__ import annotations

import importlib
from dataclasses import dataclass

import numpy as np


class NativeJetsonUnavailable(RuntimeError):
    """Raised when the optional native Jetson capture lane cannot be used."""


@dataclass(slots=True, frozen=True)
class NativeJetsonCapabilities:
    available: bool
    backend: str = "jetson_nvmm_native"
    reason: str | None = None


@dataclass(slots=True)
class NativeJetsonFrame:
    width: int
    height: int
    format: str
    captured_at_monotonic: float
    _bgr: np.ndarray

    def __post_init__(self) -> None:
        self.width = _validate_positive_dimension("width", self.width)
        self.height = _validate_positive_dimension("height", self.height)

    def as_bgr_numpy(self) -> np.ndarray:
        return self._bgr.copy()


def probe_native_jetson_capture(
    *,
    import_name: str = "argus_native_jetson_capture",
) -> NativeJetsonCapabilities:
    try:
        importlib.import_module(import_name)
    except ImportError:
        return NativeJetsonCapabilities(
            available=False,
            reason="native Jetson capture extension is not installed",
        )
    except Exception as exc:
        return NativeJetsonCapabilities(available=False, reason=str(exc))
    return NativeJetsonCapabilities(available=True)


def _validate_positive_dimension(name: str, value: int) -> int:
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be positive.")
    return value
