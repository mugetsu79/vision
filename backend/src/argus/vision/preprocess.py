from __future__ import annotations

import cv2
import numpy as np
from numpy.typing import NDArray

type Uint8Frame = NDArray[np.uint8]


def apply_clahe(
    frame: Uint8Frame,
    *,
    clip_limit: float = 2.0,
    tile_grid_size: tuple[int, int] = (8, 8),
) -> Uint8Frame:
    yuv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    yuv_frame[:, :, 0] = clahe.apply(yuv_frame[:, :, 0])
    return np.asarray(cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2BGR), dtype=np.uint8)


def apply_tonemap_drago(
    frame: Uint8Frame,
    *,
    gamma: float = 1.0,
    saturation: float = 1.0,
    bias: float = 0.85,
) -> Uint8Frame:
    normalized = frame.astype(np.float32) / 255.0
    tonemap = cv2.createTonemapDrago(gamma=gamma, saturation=saturation, bias=bias)
    tonemapped = tonemap.process(normalized)
    tonemapped = np.nan_to_num(tonemapped, nan=0.0, posinf=1.0, neginf=0.0)
    min_value = float(tonemapped.min())
    max_value = float(tonemapped.max())
    if max_value > min_value:
        tonemapped = (tonemapped - min_value) / (max_value - min_value)
    tonemapped = np.clip(tonemapped * 255.0, 0.0, 255.0)
    return tonemapped.astype(np.uint8)


def apply_dark_channel_dehaze(
    frame: Uint8Frame,
    *,
    strength: float = 0.95,
    window_size: int = 15,
    min_transmission: float = 0.1,
) -> Uint8Frame:
    normalized = frame.astype(np.float32) / 255.0
    dark_channel = _dark_channel(normalized, window_size)
    atmosphere = _estimate_atmosphere(normalized, dark_channel)
    transmission = 1.0 - strength * _dark_channel(normalized / atmosphere, window_size)
    transmission = np.asarray(
        cv2.GaussianBlur(transmission, (0, 0), sigmaX=3.0),
        dtype=np.float32,
    )
    transmission = np.clip(transmission, min_transmission, 1.0)
    restored = (normalized - atmosphere) / transmission[..., np.newaxis] + atmosphere
    restored = np.clip(restored, 0.0, 1.0)
    return (restored * 255.0).astype(np.uint8)


def _dark_channel(image: NDArray[np.float32], window_size: int) -> NDArray[np.float32]:
    minimum_per_pixel = np.min(image, axis=2)
    kernel = np.ones((window_size, window_size), dtype=np.uint8)
    return np.asarray(cv2.erode(minimum_per_pixel, kernel), dtype=np.float32)


def _estimate_atmosphere(
    image: NDArray[np.float32],
    dark_channel: NDArray[np.float32],
) -> NDArray[np.float32]:
    flat_image = image.reshape(-1, 3)
    flat_dark_channel = dark_channel.reshape(-1)
    top_count = max(1, flat_dark_channel.size // 1000)
    atmosphere_indices = np.argpartition(flat_dark_channel, -top_count)[-top_count:]
    atmosphere = flat_image[atmosphere_indices].mean(axis=0)
    return np.asarray(np.maximum(atmosphere, 1e-6), dtype=np.float32)
