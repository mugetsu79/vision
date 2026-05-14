from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vezor_installer.manifest import Manifest


def _manifest_payload() -> dict[str, object]:
    return {
        "version": "2026.5.14-test",
        "release_channel": "pilot",
        "images": {
            "backend": {
                "reference": "ghcr.io/vezor/backend@sha256:" + "a" * 64,
            },
            "frontend": {
                "reference": "ghcr.io/vezor/frontend@sha256:" + "b" * 64,
            },
            "postgres": {
                "reference": "postgres@sha256:" + "c" * 64,
            },
            "redis": {
                "reference": "redis@sha256:" + "d" * 64,
            },
            "nats": {
                "reference": "nats@sha256:" + "e" * 64,
            },
            "minio": {
                "reference": "minio/minio@sha256:" + "f" * 64,
            },
            "mediamtx": {
                "reference": "bluenviron/mediamtx@sha256:" + "1" * 64,
            },
            "keycloak": {
                "reference": "quay.io/keycloak/keycloak@sha256:" + "2" * 64,
            },
            "supervisor": {
                "reference": "ghcr.io/vezor/supervisor@sha256:" + "3" * 64,
            },
            "edge-worker": {
                "reference": "ghcr.io/vezor/edge-worker@sha256:" + "4" * 64,
            },
        },
        "package_targets": [
            {
                "name": "linux-master",
                "os": "linux",
                "role": "master",
                "architectures": ["amd64"],
                "ports": [80, 443, 8000],
            },
            {
                "name": "macos-master",
                "os": "darwin",
                "role": "master",
                "architectures": ["arm64", "amd64"],
                "ports": [3000, 8000],
            },
            {
                "name": "jetson-edge",
                "os": "linux",
                "role": "edge",
                "architectures": ["arm64"],
                "ports": [8554, 9108],
            },
        ],
        "minimum_versions": {
            "python": "3.12",
            "container_engine": "24.0",
            "compose": "2.24",
            "jetpack": "6.0",
        },
    }


def test_manifest_loads_required_product_targets() -> None:
    manifest = Manifest.model_validate(_manifest_payload())

    assert manifest.version == "2026.5.14-test"
    assert manifest.release_channel == "pilot"
    assert manifest.target_names == {"linux-master", "macos-master", "jetson-edge"}
    assert manifest.image_names >= {"backend", "frontend", "supervisor", "edge-worker"}


def test_production_manifest_requires_digest_references() -> None:
    payload = _manifest_payload()
    images = payload["images"]
    assert isinstance(images, dict)
    backend = images["backend"]
    assert isinstance(backend, dict)
    backend["reference"] = "ghcr.io/vezor/backend:latest"

    with pytest.raises(ValidationError, match="must use immutable digest references"):
        Manifest.model_validate(payload)


def test_dev_manifest_may_use_non_digest_references() -> None:
    payload = _manifest_payload()
    payload["release_channel"] = "dev"
    images = payload["images"]
    assert isinstance(images, dict)
    backend = images["backend"]
    assert isinstance(backend, dict)
    backend["reference"] = "ghcr.io/vezor/backend:dev"

    manifest = Manifest.model_validate(payload)

    assert manifest.release_channel == "dev"
    assert manifest.images["backend"].reference == "ghcr.io/vezor/backend:dev"


def test_manifest_rejects_duplicate_ports_inside_target() -> None:
    payload = _manifest_payload()
    targets = payload["package_targets"]
    assert isinstance(targets, list)
    linux_master = targets[0]
    assert isinstance(linux_master, dict)
    linux_master["ports"] = [80, 443, 80]

    with pytest.raises(ValidationError, match="ports must be unique"):
        Manifest.model_validate(payload)


def test_manifest_rejects_missing_required_targets() -> None:
    payload = _manifest_payload()
    payload["package_targets"] = [
        target
        for target in payload["package_targets"]  # type: ignore[index]
        if target["name"] != "jetson-edge"
    ]

    with pytest.raises(ValidationError, match="missing required package targets"):
        Manifest.model_validate(payload)


def test_dev_example_manifest_is_valid() -> None:
    path = Path(__file__).parents[1] / "manifests" / "dev-example.json"
    manifest = Manifest.model_validate(json.loads(path.read_text(encoding="utf-8")))

    assert manifest.release_channel == "dev"
    assert manifest.target_names == {"linux-master", "macos-master", "jetson-edge"}
