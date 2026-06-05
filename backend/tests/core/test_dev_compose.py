from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[3]
DEV_COMPOSE = REPO_ROOT / "infra" / "docker-compose.dev.yml"


def test_backend_dev_service_mounts_pack_manifests() -> None:
    compose = yaml.safe_load(DEV_COMPOSE.read_text(encoding="utf-8"))

    backend_volumes = compose["services"]["backend"]["volumes"]

    assert "../packs:/workspace/packs:ro" in backend_volumes
