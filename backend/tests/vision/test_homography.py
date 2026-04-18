from __future__ import annotations

from argus.vision.homography import Homography


def test_homography_maps_pixels_and_estimates_speed() -> None:
    homography = Homography(
        src_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        dst_points=[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)],
        ref_distance_m=10.0,
        smoothing_window=3,
    )

    x_world, y_world = homography.pixel_to_world(5.0, 5.0)
    speed_kph = homography.speed_kph(
        track_history=[(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)],
        fps=1.0,
    )

    assert round(x_world, 2) == 5.0
    assert round(y_world, 2) == 5.0
    assert round(speed_kph, 2) == 3.6
