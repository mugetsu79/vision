from __future__ import annotations

import sys
from types import ModuleType

import numpy as np

import argus.vision.jetson_nvmm_capture as jetson_capture
from argus.vision.jetson_nvmm_capture import (
    NativeJetsonFrame,
    probe_native_jetson_capture,
)


class FakeNativeJetsonModule:
    def __init__(self) -> None:
        self.open_calls: list[tuple[str, int | None, int | None, int]] = []
        self.handle = object()

    def open_rtsp(
        self,
        source_uri: str,
        width: int | None,
        height: int | None,
        fps_cap: int,
    ) -> object:
        self.open_calls.append((source_uri, width, height, fps_cap))
        return self.handle

    def read(self, handle: object) -> NativeJetsonFrame | None:
        assert handle is self.handle
        return None

    def close(self, handle: object) -> None:
        assert handle is self.handle


def test_native_jetson_frame_returns_bgr_numpy_copy() -> None:
    original = np.arange(2 * 3 * 3, dtype=np.uint8).reshape((2, 3, 3))
    frame = NativeJetsonFrame(
        width=3,
        height=2,
        format="BGR",
        captured_at_monotonic=12.5,
        _bgr=original,
    )

    observed = frame.as_bgr_numpy()

    np.testing.assert_array_equal(observed, original)
    assert observed is not original
    observed[0, 0, 0] = 255
    assert original[0, 0, 0] != 255


def test_native_capture_wrapper_reports_backend_and_mode() -> None:
    module = FakeNativeJetsonModule()

    capture = jetson_capture.NativeJetsonCapture.create(
        source_uri="rtsp://camera.local/ch2",
        target_width=1280,
        target_height=720,
        fps_cap=20,
        native_module=module,
    )

    assert module.open_calls == [("rtsp://camera.local/ch2", 1280, 720, 20)]
    assert capture.media_capture_backend() == "jetson_nvmm_native"
    assert capture.media_pipeline_mode() == "jetson_gstreamer_native"


def test_native_capture_wrapper_accepts_native_dimensions() -> None:
    module = FakeNativeJetsonModule()

    jetson_capture.NativeJetsonCapture.create(
        source_uri="rtsp://camera.local/ch2",
        target_width=None,
        target_height=None,
        fps_cap=20,
        native_module=module,
    )

    assert module.open_calls == [("rtsp://camera.local/ch2", None, None, 20)]


def test_native_capture_validates_module_shape_before_opening() -> None:
    class _MissingCloseModule:
        def __init__(self) -> None:
            self.open_calls = 0

        def open_rtsp(
            self,
            source_uri: str,
            width: int | None,
            height: int | None,
            fps_cap: int,
        ) -> object:
            del source_uri, width, height, fps_cap
            self.open_calls += 1
            return object()

        def read(self, handle: object) -> None:
            del handle

    module = _MissingCloseModule()

    with np.testing.assert_raises(jetson_capture.NativeJetsonUnavailable):
        jetson_capture.NativeJetsonCapture.create(
            source_uri="rtsp://camera.local/ch2",
            target_width=1280,
            target_height=720,
            fps_cap=20,
            native_module=module,
        )

    assert module.open_calls == 0


def test_native_frame_can_delay_bgr_materialization() -> None:
    calls = 0

    def materialize() -> np.ndarray:
        nonlocal calls
        calls += 1
        return np.zeros((720, 1280, 3), dtype=np.uint8)

    frame = NativeJetsonFrame(
        width=1280,
        height=720,
        format="NV12",
        captured_at_monotonic=12.5,
        memory_kind="cuda",
        source_profile_hash="h" * 64,
        _bgr_materializer=materialize,
    )

    assert calls == 0

    observed = frame.as_bgr_numpy()

    assert calls == 1
    assert observed.shape == (720, 1280, 3)


def test_probe_native_jetson_capture_reports_unavailable_when_extension_missing() -> None:
    capabilities = probe_native_jetson_capture(
        import_name="argus_native_missing_for_test",
    )

    assert capabilities.available is False
    assert capabilities.backend == "jetson_nvmm_native"
    assert capabilities.reason is not None
    assert "not installed" in capabilities.reason


def test_probe_native_jetson_capture_reports_available_for_importable_extension(
    monkeypatch,
) -> None:
    module_name = "argus_native_fake_for_test"
    monkeypatch.setitem(sys.modules, module_name, ModuleType(module_name))

    capabilities = probe_native_jetson_capture(import_name=module_name)

    assert capabilities.available is True
    assert capabilities.backend == "jetson_nvmm_native"
    assert capabilities.reason is None


def test_native_jetson_frame_rejects_non_positive_dimensions() -> None:
    with np.testing.assert_raises(ValueError):
        NativeJetsonFrame(
            width=0,
            height=2,
            format="BGR",
            captured_at_monotonic=12.5,
            _bgr=np.zeros((2, 3, 3), dtype=np.uint8),
        )
