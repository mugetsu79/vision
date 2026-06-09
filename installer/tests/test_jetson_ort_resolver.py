from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from vezor_installer.jetson_ort import resolve_jetson_ort_wheel
from vezor_installer.manifest import Manifest


REPO_ROOT = Path(__file__).parents[2]


def test_resolves_matching_jetson_ort_wheel_without_manual_url() -> None:
    preflight = {
        "arch": "arm64",
        "jetpack": "6.2",
        "l4t": "36.4.0",
        "python_abi": "cp310",
    }
    wheels = [
        {
            "jetpack": "6.2",
            "l4t": "36.4",
            "python": "cp310",
            "arch": "aarch64",
            "url": "https://example.invalid/ort-gpu.whl",
            "sha256": "b" * 64,
        }
    ]

    resolved = resolve_jetson_ort_wheel(preflight, wheels)

    assert resolved.url == "https://example.invalid/ort-gpu.whl"
    assert resolved.sha256 == "b" * 64


def test_resolver_fails_closed_when_no_wheel_matches() -> None:
    preflight = {
        "arch": "arm64",
        "jetpack": "6.2",
        "l4t": "36.4.0",
        "python_abi": "cp310",
    }

    with pytest.raises(ValueError, match="No Jetson GPU ONNX Runtime wheel"):
        resolve_jetson_ort_wheel(preflight, [])


def test_resolver_cli_emits_url_and_sha256_exports(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    preflight_path = tmp_path / "preflight.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": "dev-local",
                "release_channel": "dev",
                "images": {
                    "backend": {"reference": "vezor/backend:portable-demo"},
                    "frontend": {"reference": "vezor/frontend:portable-demo"},
                    "postgres": {"reference": "postgres:16"},
                    "redis": {"reference": "redis:7"},
                    "nats": {"reference": "nats:2"},
                    "minio": {"reference": "minio/minio:latest"},
                    "mediamtx": {"reference": "bluenviron/mediamtx:latest"},
                    "keycloak": {"reference": "quay.io/keycloak/keycloak:latest"},
                    "supervisor": {"reference": "vezor/backend:portable-demo"},
                    "edge-worker": {"reference": "vezor/edge-worker:portable-demo"},
                },
                "package_targets": [
                    {
                        "name": "linux-master",
                        "os": "linux",
                        "role": "master",
                        "architectures": ["amd64"],
                    },
                    {
                        "name": "macos-master",
                        "os": "darwin",
                        "role": "master",
                        "architectures": ["arm64"],
                    },
                    {
                        "name": "jetson-edge",
                        "os": "linux",
                        "role": "edge",
                        "architectures": ["arm64"],
                    },
                ],
                "minimum_versions": {
                    "python": "3.12",
                    "container_engine": "24.0",
                    "compose": "2.24",
                    "jetpack": "6.0",
                },
                "jetson_ort_wheels": [
                    {
                        "jetpack": "6.2",
                        "l4t": "36.4",
                        "python": "cp310",
                        "arch": "aarch64",
                        "url": "https://example.invalid/ort-gpu.whl",
                        "sha256": "c" * 64,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    preflight_path.write_text(
        json.dumps(
            {
                "arch": "arm64",
                "jetpack": "6.2",
                "l4t": "36.4.4",
                "python_abi": "cp310",
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "vezor_installer.jetson_ort",
            str(manifest_path),
            str(preflight_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert 'JETSON_ORT_WHEEL_URL="https://example.invalid/ort-gpu.whl"' in result.stdout
    assert f'JETSON_ORT_WHEEL_SHA256="{"c" * 64}"' in result.stdout


def test_dev_manifest_resolves_jetpack_62_l4t_365_gpu_ort_wheel() -> None:
    manifest = Manifest.model_validate_json(
        (REPO_ROOT / "installer" / "manifests" / "dev-example.json").read_text(
            encoding="utf-8"
        )
    )

    resolved = resolve_jetson_ort_wheel(
        {
            "arch": "aarch64",
            "jetpack": "6.2",
            "l4t": "36.5.0-20260115194252",
            "python_abi": "cp310",
        },
        manifest.jetson_ort_wheels,
    )

    assert resolved.url == (
        "https://pypi.jetson-ai-lab.io/jp6/cu126/+f/d98/0b934b9a29c1a/"
        "onnxruntime_gpu-1.24.0-cp310-cp310-linux_aarch64.whl"
    )
    assert resolved.sha256 == (
        "d980b934b9a29c1a9d6f39751edd7662b69fadd75556a10ff363773a58ce0950"
    )
