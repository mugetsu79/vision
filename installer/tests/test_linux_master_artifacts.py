from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
MASTER_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.master.yml"
MASTER_SERVICE = REPO_ROOT / "infra" / "install" / "systemd" / "vezor-master.service"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "install-master.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "uninstall.sh"

FORBIDDEN_PRODUCT_STRINGS = (
    "ARGUS_API_BEARER_TOKEN",
    "Bearer ",
    "admin-dev",
    "argus-admin-pass",
    "make dev-up",
    "pnpm dev",
    "uvicorn argus.main:app --reload",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_linux_master_systemd_service_is_restartable_appliance_wrapper() -> None:
    service = _read(MASTER_SERVICE)

    assert "Description=Vezor Master Appliance" in service
    assert "After=network-online.target" in service
    assert "Restart=on-failure" in service
    assert "Environment=VEZOR_MASTER_CONFIG=/etc/vezor/master.json" in service
    assert "--config /etc/vezor/master.json" in service
    assert "StateDirectory=vezor" in service
    assert "LogsDirectory=vezor" in service
    assert "make dev-up" not in service


def test_linux_master_compose_profile_contains_required_product_services() -> None:
    compose = _read(MASTER_COMPOSE)

    for service_name in (
        "postgres",
        "redis",
        "nats",
        "minio",
        "mediamtx",
        "keycloak",
        "backend",
        "frontend",
        "vezor-supervisor",
    ):
        assert f"  {service_name}:" in compose

    assert "/var/lib/vezor/postgres:/var/lib/postgresql/data" in compose
    assert "/var/lib/vezor/minio:/data" in compose
    assert "/etc/vezor/master.json:/etc/vezor/master.json:ro" in compose
    assert "/etc/vezor/supervisor.json:/etc/vezor/supervisor.json:ro" in compose


def test_linux_master_artifacts_do_not_embed_dev_credentials_or_bearer_tokens() -> None:
    combined = "\n".join(
        _read(path)
        for path in (MASTER_COMPOSE, MASTER_SERVICE, INSTALL_SCRIPT, UNINSTALL_SCRIPT)
    )

    for forbidden in FORBIDDEN_PRODUCT_STRINGS:
        assert forbidden not in combined


def test_linux_master_install_script_exposes_safe_install_options() -> None:
    script = _read(INSTALL_SCRIPT)

    for option in (
        "--dry-run",
        "--version",
        "--manifest",
        "--public-url",
        "--data-dir",
        "--config-dir",
    ):
        assert option in script

    assert "systemctl enable vezor-master.service" in script
    assert "systemctl start vezor-master.service" in script
    assert "first-run" in script
    assert "$CONFIG_DIR/master.env" in script
    assert "$CONFIG_DIR/supervisor.json" in script
    assert "$CONFIG_DIR/secrets/postgres_password" in script
    assert "$CONFIG_DIR/nats/nats.conf" in script
    assert "$CONFIG_DIR/mediamtx/mediamtx.yml" in script
    assert "manifest_image_ref backend" in script


def test_linux_uninstall_preserves_data_unless_explicitly_confirmed() -> None:
    script = _read(UNINSTALL_SCRIPT)

    assert "--purge-data" in script
    assert "delete-vezor-data" in script
    assert "Preserving Vezor data" in script
