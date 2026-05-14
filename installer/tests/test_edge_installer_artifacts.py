from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
EDGE_SERVICE = REPO_ROOT / "infra" / "install" / "systemd" / "vezor-edge.service"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "install-edge.sh"
PREFLIGHT = REPO_ROOT / "scripts" / "jetson-preflight.sh"
SUPERVISOR_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.supervisor.yml"

FORBIDDEN_PRODUCT_STRINGS = (
    "ARGUS_API_BEARER_TOKEN",
    "Bearer ",
    "admin-dev",
    "argus-admin-pass",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_edge_systemd_service_is_restartable_appliance_wrapper() -> None:
    service = _read(EDGE_SERVICE)

    assert "Description=Vezor Edge Appliance" in service
    assert "After=network-online.target" in service
    assert "Restart=on-failure" in service
    assert "Environment=VEZOR_EDGE_CONFIG=/etc/vezor/edge.json" in service
    assert "Environment=VEZOR_SUPERVISOR_CONFIG=/etc/vezor/supervisor.json" in service
    assert "--config /etc/vezor/edge.json" in service
    assert "StateDirectory=vezor" in service
    assert "LogsDirectory=vezor" in service


def test_edge_install_script_accepts_pairing_unpaired_and_manifest_modes() -> None:
    script = _read(INSTALL_SCRIPT)

    for option in (
        "--api-url",
        "--pairing-code",
        "--session-id",
        "--unpaired",
        "--manifest",
        "--version",
        "--jetson-ort-wheel-url",
    ):
        assert option in script

    assert "manifest_image_ref edge-worker" in script
    assert "manifest_image_ref mediamtx" in script
    assert "build_local_edge_image" in script
    assert "/opt/vezor/current/backend/Dockerfile.edge" in script
    assert "JETSON_ORT_WHEEL_URL" in script
    assert "scripts/jetson-preflight.sh --installer --json" in script
    assert "/etc/vezor/edge.json" in script
    assert "/etc/vezor/supervisor.json" in script
    assert "$CONFIG_DIR/edge.env" in script
    assert "$CONFIG_DIR/mediamtx/mediamtx.yml" in script
    assert "$DATA_DIR/credentials" in script
    assert "VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials" in script
    assert 'chmod 0644 "$EDGE_ENV"' in script
    assert 'old_umask="$(umask)"' in script
    assert "--supervisor-id" in script
    assert '--credential-path "$DATA_DIR/credentials/supervisor.credential"' in script
    assert "systemctl enable vezor-edge.service" in script
    assert "systemctl start vezor-edge.service" in script


def test_edge_artifacts_do_not_embed_dev_credentials_or_bearer_tokens() -> None:
    combined = "\n".join(
        _read(path) for path in (EDGE_SERVICE, INSTALL_SCRIPT, PREFLIGHT, SUPERVISOR_COMPOSE)
    )

    for forbidden in FORBIDDEN_PRODUCT_STRINGS:
        assert forbidden not in combined


def test_supervisor_compose_profile_contains_edge_services_and_secret_mounts() -> None:
    compose = _read(SUPERVISOR_COMPOSE)

    assert "  mediamtx:" in compose
    assert "  vezor-supervisor:" in compose
    assert "${VEZOR_SUPERVISOR_IMAGE:?set VEZOR_SUPERVISOR_IMAGE}" in compose
    assert "${VEZOR_MEDIAMTX_IMAGE:?set VEZOR_MEDIAMTX_IMAGE}" in compose
    assert 'entrypoint: ["/app/.venv/bin/python", "-m", "argus.supervisor.runner"]' in compose
    assert "      - --config" in compose
    assert "ARGUS_MEDIAMTX_API_URL: http://mediamtx:9997" in compose
    assert "ARGUS_ENABLE_WORKER_METRICS_SERVER: \"true\"" in compose
    assert "ARGUS_PUBLISH_PROFILE: jetson-nano" in compose
    assert 'runtime: ${VEZOR_NVIDIA_RUNTIME:-nvidia}' in compose
    assert '"${VEZOR_WORKER_METRICS_BIND:-127.0.0.1}:9108:9108"' in compose
    assert "/etc/vezor/edge.json:/etc/vezor/edge.json:ro" in compose
    assert "/etc/vezor/supervisor.json:/etc/vezor/supervisor.json:ro" in compose
    assert (
        "${VEZOR_CREDENTIALS_HOST_DIR:-/var/lib/vezor/credentials}"
        ":/run/vezor/credentials:ro"
    ) in compose


def test_jetson_preflight_supports_installer_json_mode() -> None:
    preflight = _read(PREFLIGHT)

    assert "--installer" in preflight
    assert "--json" in preflight
    assert "check_port_available" in preflight
    assert "nvidia-container-toolkit" in preflight
    assert "Docker Compose v2 plugin is available" in preflight
