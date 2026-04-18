from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pytest
from numpy.typing import NDArray

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "vision"


def load_scene(scene_name: str) -> dict[str, Any]:
    return json.loads((FIXTURE_ROOT / f"{scene_name}.json").read_text(encoding="utf-8"))


def render_scene(scene_name: str, *, haze: bool = False) -> NDArray[np.uint8]:
    scene = load_scene(scene_name)
    width = int(scene["width"])
    height = int(scene["height"])
    top_bgr = np.array(scene["background"]["top_bgr"], dtype=np.float32)
    bottom_bgr = np.array(scene["background"]["bottom_bgr"], dtype=np.float32)
    gradient = np.linspace(0.0, 1.0, height, dtype=np.float32).reshape(height, 1, 1)
    frame = np.broadcast_to(
        (top_bgr * (1.0 - gradient) + bottom_bgr * gradient).astype(np.uint8),
        (height, width, 3),
    ).copy()

    for obj in scene["objects"]:
        x1, y1, x2, y2 = [int(value) for value in obj["bbox"]]
        color = tuple(int(value) for value in obj["color_bgr"])
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness=-1)

        if "face_bbox" in obj:
            fx1, fy1, fx2, fy2 = [int(value) for value in obj["face_bbox"]]
            cv2.ellipse(
                frame,
                ((fx1 + fx2) // 2, (fy1 + fy2) // 2),
                ((fx2 - fx1) // 2, (fy2 - fy1) // 2),
                0,
                0,
                360,
                (210, 210, 210),
                thickness=-1,
            )

        if "plate_bbox" in obj:
            px1, py1, px2, py2 = [int(value) for value in obj["plate_bbox"]]
            cv2.rectangle(frame, (px1, py1), (px2, py2), (245, 245, 245), thickness=-1)

    if haze:
        fog = np.full_like(frame, 220)
        frame = cv2.addWeighted(frame, 0.55, fog, 0.45, 0)
        frame = cv2.GaussianBlur(frame, (7, 7), 0)

    return frame


@pytest.fixture(scope="session")
def vehicle_scene() -> dict[str, Any]:
    return load_scene("vehicle_scene")


@pytest.fixture(scope="session")
def pedestrian_scene() -> dict[str, Any]:
    return load_scene("pedestrian_scene")


@pytest.fixture(scope="session")
def ppe_scene() -> dict[str, Any]:
    return load_scene("ppe_scene")


@pytest.fixture()
def vehicle_frame() -> NDArray[np.uint8]:
    return render_scene("vehicle_scene", haze=True)


@pytest.fixture()
def pedestrian_frame() -> NDArray[np.uint8]:
    return render_scene("pedestrian_scene", haze=True)


@pytest.fixture()
def ppe_frame() -> NDArray[np.uint8]:
    return render_scene("ppe_scene", haze=True)
