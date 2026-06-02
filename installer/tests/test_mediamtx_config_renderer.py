from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
RENDERER = REPO_ROOT / "installer" / "lib" / "render_mediamtx_config.py"
SOURCE_CONFIG = REPO_ROOT / "infra" / "mediamtx" / "mediamtx.yml"


def _render(tmp_path: Path, *args: str) -> str:
    dest = tmp_path / "mediamtx.yml"
    subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--source",
            str(SOURCE_CONFIG),
            "--dest",
            str(dest),
            *args,
        ],
        check=True,
    )
    return dest.read_text(encoding="utf-8")


def _list_values(config: str, key: str) -> list[str]:
    lines = config.splitlines()
    for index, line in enumerate(lines):
        if line == f"{key}:":
            values: list[str] = []
            for item in lines[index + 1 :]:
                if not item.startswith("  - "):
                    break
                values.append(item.removeprefix("  - "))
            return values
    raise AssertionError(f"{key} not found in rendered config")


def test_renderer_adds_public_master_origin_and_webrtc_host(tmp_path: Path) -> None:
    config = _render(
        tmp_path,
        "--frontend-origin",
        "http://192.168.1.25:3000",
        "--frontend-origin",
        "http://localhost:3000",
        "--frontend-origin",
        "http://127.0.0.1:3000",
        "--frontend-origin",
        "http://localhost:3000",
        "--webrtc-host",
        "192.168.1.25",
        "--webrtc-host",
        "localhost",
        "--webrtc-host",
        "127.0.0.1",
        "--webrtc-host",
        "localhost",
    )

    for key in ("apiAllowOrigins", "webrtcAllowOrigins", "hlsAllowOrigins"):
        values = _list_values(config, key)
        assert values == [
            "http://192.168.1.25:3000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    assert _list_values(config, "webrtcAdditionalHosts") == [
        "192.168.1.25",
        "localhost",
        "127.0.0.1",
    ]
    assert "~^cameras/[^/]+/annotated(?:-[A-Za-z0-9_.-]+)?$" in config


def test_renderer_rewrites_jwks_and_edge_origin_and_host(tmp_path: Path) -> None:
    config = _render(
        tmp_path,
        "--jwks-url",
        "http://192.168.1.25:8000/.well-known/argus/mediamtx/jwks.json",
        "--frontend-origin",
        "http://192.168.1.25:3000",
        "--webrtc-host",
        "jetson-01.local",
    )

    assert (
        "authJWTJWKS: http://192.168.1.25:8000/"
        ".well-known/argus/mediamtx/jwks.json"
    ) in config
    for key in ("apiAllowOrigins", "webrtcAllowOrigins", "hlsAllowOrigins"):
        assert _list_values(config, key) == ["http://192.168.1.25:3000"]
    assert _list_values(config, "webrtcAdditionalHosts") == ["jetson-01.local"]
