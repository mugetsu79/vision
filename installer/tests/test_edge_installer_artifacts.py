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


def test_edge_install_script_accepts_pairing_and_unpaired_modes() -> None:
    script = _read(INSTALL_SCRIPT)

    for option in ("--api-url", "--pairing-code", "--session-id", "--unpaired"):
        assert option in script

    assert "scripts/jetson-preflight.sh --installer --json" in script
    assert "/etc/vezor/edge.json" in script
    assert "/etc/vezor/supervisor.json" in script
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
    assert "/etc/vezor/edge.json:/etc/vezor/edge.json:ro" in compose
    assert "/etc/vezor/supervisor.json:/etc/vezor/supervisor.json:ro" in compose
    assert "/run/vezor/credentials:/run/vezor/credentials:ro" in compose


def test_jetson_preflight_supports_installer_json_mode() -> None:
    preflight = _read(PREFLIGHT)

    assert "--installer" in preflight
    assert "--json" in preflight
    assert "check_port_available" in preflight
    assert "nvidia-container-toolkit" in preflight
    assert "Docker Compose v2 plugin is available" in preflight
