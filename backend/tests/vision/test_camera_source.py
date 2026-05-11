from __future__ import annotations

import cv2

from argus.vision.camera import CameraSourceMode, PlatformInfo, _resolve_capture_spec


def test_resolves_usb_uri_to_v4l2_device_path() -> None:
    mode, source, backend = _resolve_capture_spec(
        "usb:///dev/video0",
        PlatformInfo(machine="aarch64", jetson=True),
    )

    assert mode is CameraSourceMode.LINUX_USB
    assert source == "/dev/video0"
    assert backend == cv2.CAP_V4L2
