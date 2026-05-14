from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]

WRAPPERS = (
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


def test_appliance_driver_supports_service_required_commands() -> None:
    driver = _read(REPO_ROOT / "bin" / "vezor-appliance")

    assert 'DEFAULT_CONFIG="/etc/vezor/master.json"' in driver
    assert 'DEFAULT_CONFIG="/etc/vezor/edge.json"' in driver
    assert 'run_compose up -d --remove-orphans' in driver
    assert 'run_compose down "${EXTRA_ARGS[@]}"' in driver
    assert "VEZOR_MASTER_ENV_FILE" in driver
    assert "VEZOR_EDGE_ENV_FILE" in driver
    assert "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin" in driver
    assert 'if [[ "$COMMAND" == "-h" || "$COMMAND" == "--help" ]]' in driver


def test_vezorctl_wrapper_uses_installer_tooling_without_static_tokens() -> None:
    wrapper = _read(REPO_ROOT / "bin" / "vezorctl")

    assert "installer/.venv/bin/vezorctl" in wrapper
    assert 'uv run --project "$ROOT_DIR/installer" vezorctl "$@"' in wrapper
    assert "ARGUS_API_BEARER_TOKEN" not in wrapper
