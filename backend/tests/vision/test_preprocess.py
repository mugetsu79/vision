from __future__ import annotations

import numpy as np

from argus.vision.preprocess import (
    apply_clahe,
    apply_dark_channel_dehaze,
    apply_tonemap_drago,
)


def test_preprocess_functions_are_pure_and_shape_stable(vehicle_frame) -> None:
    original = vehicle_frame.copy()

    clahe_frame = apply_clahe(vehicle_frame, clip_limit=3.0, tile_grid_size=(4, 4))
    tonemapped = apply_tonemap_drago(vehicle_frame)
    dehazed = apply_dark_channel_dehaze(vehicle_frame, strength=0.85, window_size=7)

    assert np.array_equal(vehicle_frame, original)
    assert clahe_frame.shape == vehicle_frame.shape
    assert tonemapped.shape == vehicle_frame.shape
    assert dehazed.shape == vehicle_frame.shape
    assert clahe_frame.dtype == np.uint8
    assert tonemapped.dtype == np.uint8
    assert dehazed.dtype == np.uint8
    assert not np.array_equal(clahe_frame, vehicle_frame)
    assert tonemapped.std() >= vehicle_frame.std()
    assert dehazed.std() >= vehicle_frame.std()
