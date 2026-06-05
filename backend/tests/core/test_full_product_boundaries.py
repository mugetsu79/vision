from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from argus.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_traffic_has_no_runtime_module_or_route() -> None:
    app = create_app()

    assert importlib.util.find_spec("argus.traffic_public_space") is None
    route_paths = {_route_path(route) for route in app.routes}
    assert "/api/v1/traffic-public-space/runtime" not in route_paths
    assert "/api/v1/packs/traffic-public-space/runtime" not in route_paths


def test_core_contracts_do_not_contain_maritime_nouns() -> None:
    forbidden_identifier_patterns = [
        r"\bVessel\b",
        r"\bVoyage\b",
        r"\bPortCall\b",
        r"\bAIS\b",
        r"\bNMEA\b",
        r"\bMMSI\b",
        r"\bIMO\b",
        r"\bvessel_id\b",
        r"\bvoyage_id\b",
        r"\bport_call_id\b",
        r"\bmmsi\b",
        r"\bimo_number\b",
    ]
    scanned_paths = [
        REPO_ROOT / "backend/src/argus/link",
        REPO_ROOT / "backend/src/argus/fleet",
        REPO_ROOT / "backend/src/argus/billing",
        REPO_ROOT / "backend/src/argus/support",
        REPO_ROOT / "backend/src/argus/api/contracts.py",
    ]

    text = "\n".join(
        path.read_text(encoding="utf-8")
        for root in scanned_paths
        if root.exists()
        for path in ([root] if root.is_file() else root.rglob("*.py"))
    )
    hits = [pattern for pattern in forbidden_identifier_patterns if re.search(pattern, text)]
    assert hits == []


def test_maritime_runtime_is_the_only_implemented_pack_runtime() -> None:
    assert importlib.util.find_spec("argus.maritime") is not None
    assert importlib.util.find_spec("argus.home_lab") is None
    assert importlib.util.find_spec("argus.traffic_public_space") is None


def _route_path(route: object) -> str | None:
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else None
