from __future__ import annotations

from argus.vision.zones import Zones


def test_zones_map_points_to_expected_polygons(pedestrian_scene) -> None:
    zones = Zones(pedestrian_scene["zones"])

    assert zones.zone_for_point(40.0, 80.0) == "walkway"
    assert zones.zone_for_point(110.0, 80.0) == "restricted"
    assert zones.zone_for_point(-1.0, 5.0) is None
