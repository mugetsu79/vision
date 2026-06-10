from __future__ import annotations

import importlib
from collections.abc import Callable
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
    memory_kind: str = "cuda"
    source_profile_hash: str | None = None
    _bgr: np.ndarray | None = None
    _bgr_materializer: Callable[[], np.ndarray] | None = None

    def __post_init__(self) -> None:
        self.width = _validate_positive_dimension("width", self.width)
        self.height = _validate_positive_dimension("height", self.height)

    def as_bgr_numpy(self) -> np.ndarray:
        if self._bgr is not None:
            return self._bgr.copy()
        if self._bgr_materializer is not None:
            return self._bgr_materializer().copy()
        raise NativeJetsonUnavailable("native Jetson frame does not expose BGR pixels")


@dataclass(slots=True)
class NativeJetsonCapture:
    _native_module: object
    _handle: object
    _last_stage_timings: dict[str, float]
    _released: bool = False

    @classmethod
    def create(
        cls,
        *,
        source_uri: str,
        target_width: int | None,
        target_height: int | None,
        fps_cap: int,
        native_module: object | None = None,
        import_name: str = "argus_native_jetson_capture",
    ) -> NativeJetsonCapture:
        target_width = _validate_optional_positive_dimension("target_width", target_width)
        target_height = _validate_optional_positive_dimension("target_height", target_height)
        if native_module is None:
            native_module = _import_native_capture_module(import_name)

        open_rtsp = _required_native_callable(native_module, "open_rtsp")
        _required_native_callable(native_module, "read")
        _required_native_callable(native_module, "close")
        handle = open_rtsp(source_uri, target_width, target_height, fps_cap)
        return cls(
            _native_module=native_module,
            _handle=handle,
            _last_stage_timings={},
        )

    def read(self) -> tuple[bool, NativeJetsonFrame | None]:
        if self._released:
            return False, None
        read_frame = getattr(self._native_module, "read", None)
        if not callable(read_frame):
            raise NativeJetsonUnavailable("native Jetson capture extension does not expose read")

        frame = read_frame(self._handle)
        if frame is None:
            return False, None
        return True, frame

    def release(self) -> None:
        if self._released:
            return
        close = getattr(self._native_module, "close", None)
        if not callable(close):
            self._released = True
            raise NativeJetsonUnavailable("native Jetson capture extension does not expose close")
        try:
            close(self._handle)
        finally:
            self._released = True

    def last_stage_timings(self) -> dict[str, float]:
        return dict(self._last_stage_timings)

    def media_pipeline_mode(self) -> str:
        return "jetson_gstreamer_native"

    def media_capture_backend(self) -> str:
        return "jetson_nvmm_native"


def probe_native_jetson_capture(
    *,
    import_name: str = "argus_native_jetson_capture",
) -> NativeJetsonCapabilities:
    try:
        _import_native_capture_module(import_name)
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


def _validate_optional_positive_dimension(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    return _validate_positive_dimension(name, value)


def _required_native_callable(native_module: object, name: str) -> Callable[..., object]:
    value = getattr(native_module, name, None)
    if not callable(value):
        raise NativeJetsonUnavailable(
            f"native Jetson capture extension does not expose {name}"
        )
    return value


def _import_native_capture_module(import_name: str) -> object:
    return importlib.import_module(import_name)
