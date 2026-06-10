from __future__ import annotations

import sys
from types import ModuleType

import numpy as np

from argus.vision.jetson_nvmm_capture import (
    NativeJetsonFrame,
    probe_native_jetson_capture,
)


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
