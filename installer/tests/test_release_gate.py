from __future__ import annotations

import json
import re
from pathlib import Path

from vezor_installer.manifest import Manifest

REPO_ROOT = Path(__file__).parents[2]
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate-installers.sh"
PRODUCT_GUIDE = REPO_ROOT / "docs" / "product-installer-and-first-run-guide.md"
MAKEFILE = REPO_ROOT / "Makefile"

REQUIRED_FILES = (
    REPO_ROOT / "installer" / "manifests" / "dev-example.json",
    REPO_ROOT / "installer" / "linux" / "install-master.sh",
    REPO_ROOT / "installer" / "linux" / "install-edge.sh",
    REPO_ROOT / "installer" / "linux" / "uninstall.sh",
    REPO_ROOT / "installer" / "macos" / "install-master.sh",
    REPO_ROOT / "installer" / "macos" / "uninstall.sh",
    REPO_ROOT / "bin" / "vezor-appliance",
    REPO_ROOT / "bin" / "vezor-master",
    REPO_ROOT / "bin" / "vezor-edge",
    REPO_ROOT / "bin" / "vezorctl",
    REPO_ROOT / "infra" / "install" / "compose" / "compose.master.yml",
    REPO_ROOT / "infra" / "install" / "compose" / "compose.supervisor.yml",
    REPO_ROOT / "infra" / "install" / "systemd" / "vezor-master.service",
    REPO_ROOT / "infra" / "install" / "systemd" / "vezor-edge.service",
    REPO_ROOT / "infra" / "install" / "launchd" / "com.vezor.master.plist",
    PRODUCT_GUIDE,
)

PRODUCT_ARTIFACTS = tuple(path for path in REQUIRED_FILES if path.suffix != ".md")
EXECUTABLE_INSTALLER_SCRIPTS = (
    REPO_ROOT / "installer" / "linux" / "install-master.sh",
    REPO_ROOT / "installer" / "linux" / "install-edge.sh",
    REPO_ROOT / "installer" / "linux" / "uninstall.sh",
    REPO_ROOT / "installer" / "macos" / "install-master.sh",
    REPO_ROOT / "installer" / "macos" / "uninstall.sh",
)
DEV_ONLY_PATTERNS = (
    "ARGUS_API_BEARER_TOKEN",
    "Bearer ",
    "admin-dev",
    "argus-admin-pass",
    "make dev-up",
    "docker compose up",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_release_gate_script_exists_and_runs_installer_checks() -> None:
    script = _read(VALIDATE_SCRIPT)

    assert "python3 -m uv run --project installer pytest installer/tests -q" in script
    assert "bash -n installer/linux/install-master.sh" in script
    assert "bash -n installer/linux/install-edge.sh" in script
    assert "bash -n bin/vezor-appliance" in script
    assert "bash -n bin/vezor-master" in script
    assert "bash -n bin/vezor-edge" in script
    assert "bash -n bin/vezorctl" in script
    assert 'test -x "$executable"' in script
    assert "installer/manifests/dev-example.json" in script
    assert "docker compose -f infra/install/compose/compose.master.yml config" in script
    assert "docker unavailable" in script


def test_makefile_exposes_installer_release_gate() -> None:
    makefile = _read(MAKEFILE)

    assert "verify-installers:" in makefile
    assert "./scripts/validate-installers.sh" in makefile


def test_release_gate_required_files_exist_without_deepstream_dependency() -> None:
    missing = [str(path.relative_to(REPO_ROOT)) for path in REQUIRED_FILES if not path.exists()]

    assert missing == []
    assert not any("deepstream" in str(path).lower() for path in REQUIRED_FILES)
    assert "deepstream" not in _read(VALIDATE_SCRIPT).lower()


def test_installer_shell_scripts_are_directly_executable() -> None:
    not_executable = [
        str(path.relative_to(REPO_ROOT))
        for path in EXECUTABLE_INSTALLER_SCRIPTS
        if not path.stat().st_mode & 0o111
    ]

    assert not_executable == []


def test_release_gate_manifest_validation_passes() -> None:
    manifest_path = REPO_ROOT / "installer" / "manifests" / "dev-example.json"
    manifest = Manifest.model_validate(json.loads(_read(manifest_path)))

    assert manifest.target_names == {"linux-master", "macos-master", "jetson-edge"}


def test_product_artifacts_do_not_embed_dev_commands_or_static_secrets() -> None:
    combined = "\n".join(_read(path) for path in PRODUCT_ARTIFACTS)

    for pattern in DEV_ONLY_PATTERNS:
        assert pattern not in combined


def test_product_guide_labels_dev_and_break_glass_commands() -> None:
    guide = _read(PRODUCT_GUIDE)
    hits = [
        line
        for line in guide.splitlines()
        if re.search(
            r"make dev-up|docker compose -f infra/docker-compose|docker compose up|ARGUS_API_BEARER_TOKEN",
            line,
        )
    ]

    assert all(
        "Development fallback" in line or "Break-glass" in line for line in hits
    )
