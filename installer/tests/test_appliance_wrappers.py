from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

WRAPPERS = (
    REPO_ROOT / "bin" / "vezor",
    REPO_ROOT / "bin" / "vezor-appliance",
    REPO_ROOT / "bin" / "vezor-master",
    REPO_ROOT / "bin" / "vezor-edge",
    REPO_ROOT / "bin" / "vezorctl",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_appliance_wrapper_entrypoints_exist_and_are_executable() -> None:
    for path in WRAPPERS:
        assert path.exists(), path
        assert os.access(path, os.X_OK), path


def test_appliance_wrappers_are_valid_bash() -> None:
    for path in WRAPPERS:
        result = subprocess.run(["bash", "-n", str(path)], check=False)
        assert result.returncode == 0, path


def test_master_and_edge_wrappers_delegate_to_appliance_driver() -> None:
    assert 'exec "$ROOT_DIR/bin/vezor-appliance" master "$@"' in _read(
        REPO_ROOT / "bin" / "vezor-master"
    )
    assert 'exec "$ROOT_DIR/bin/vezor-appliance" edge "$@"' in _read(
        REPO_ROOT / "bin" / "vezor-edge"
    )


def test_vezor_front_door_delegates_to_existing_installers_and_tools() -> None:
    wrapper = _read(REPO_ROOT / "bin" / "vezor")

    assert '"$ROOT_DIR/installer/macos/install-master.sh"' in wrapper
    assert '"$ROOT_DIR/installer/linux/install-master.sh"' in wrapper
    assert '"$ROOT_DIR/installer/linux/install-edge.sh"' in wrapper
    assert 'exec "$ROOT_DIR/bin/vezor-master" "$@"' in wrapper
    assert 'exec "$ROOT_DIR/bin/vezor-edge" "$@"' in wrapper
    assert 'exec "$ROOT_DIR/bin/vezorctl" "$@"' in wrapper
    assert '"$ROOT_DIR/scripts/validate-installers.sh"' in wrapper
    assert "ARGUS_API_BEARER_TOKEN" not in wrapper


def test_vezor_status_uses_local_cli_status_command() -> None:
    wrapper = _read(REPO_ROOT / "bin" / "vezor")

    assert 'exec "$ROOT_DIR/bin/vezorctl" status "$@"' in wrapper


def test_appliance_driver_supports_service_required_commands() -> None:
    driver = _read(REPO_ROOT / "bin" / "vezor-appliance")

    assert 'DEFAULT_CONFIG="/etc/vezor/master.json"' in driver
    assert 'DEFAULT_CONFIG="/etc/vezor/edge.json"' in driver
    assert 'run_compose up -d --remove-orphans' in driver
    assert 'run_compose_with_extra_args down' in driver
    assert "VEZOR_MASTER_ENV_FILE" in driver
    assert "VEZOR_EDGE_ENV_FILE" in driver
    assert 'json_config_value config_dir "/etc/vezor"' in driver
    assert 'ENV_FILE="${VEZOR_MASTER_ENV_FILE:-$CONFIG_DIR/master.env}"' in driver
    assert driver.index('source "$ENV_FILE"') < driver.index('env_override="${!COMPOSE_ENV_VAR:-}"')
    assert "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin" in driver
    assert 'if [[ "$COMMAND" == "-h" || "$COMMAND" == "--help" ]]' in driver


def test_appliance_driver_handles_empty_extra_args_under_macos_bash() -> None:
    result = subprocess.run(
        [
            "/bin/bash",
            str(REPO_ROOT / "bin" / "vezor-appliance"),
            "master",
            "status",
            "--config",
            "/tmp/vezor-missing-config.json",
        ],
        check=False,
        capture_output=True,
        env={"PATH": "/usr/bin:/bin", "VEZOR_CONTAINER_ENGINE": "unsupported"},
        text=True,
    )

    assert result.returncode != 0
    assert "unbound variable" not in result.stderr
    assert "Unsupported container engine: unsupported" in result.stderr


def test_vezorctl_wrapper_uses_installer_tooling_without_static_tokens() -> None:
    wrapper = _read(REPO_ROOT / "bin" / "vezorctl")

    assert "installer/.venv/bin/vezorctl" in wrapper
    assert 'uv run --project "$ROOT_DIR/installer" vezorctl "$@"' in wrapper
    assert 'python3.12 -m uv run --project "$ROOT_DIR/installer" vezorctl "$@"' in wrapper
    assert "ARGUS_API_BEARER_TOKEN" not in wrapper
