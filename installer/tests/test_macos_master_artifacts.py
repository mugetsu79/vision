from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
MASTER_PLIST = REPO_ROOT / "infra" / "install" / "launchd" / "com.vezor.master.plist"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "macos" / "install-master.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "installer" / "macos" / "uninstall.sh"

FORBIDDEN_PRODUCT_STRINGS = (
    "ARGUS_API_BEARER_TOKEN",
    "Bearer ",
    "admin-dev",
    "argus-admin-pass",
    "make dev-up",
    "docker compose up",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_macos_master_plist_is_launchd_owned_appliance() -> None:
    plist = _read(MASTER_PLIST)

    assert "<string>com.vezor.master</string>" in plist
    assert "<string>/opt/vezor/current/bin/vezor-master</string>" in plist
    assert "<string>--config</string>" in plist
    assert "<string>/etc/vezor/master.json</string>" in plist
    assert "<key>RunAtLoad</key>" in plist
    assert "<key>KeepAlive</key>" in plist
    assert "<string>/var/log/vezor/master.log</string>" in plist
    assert "<key>PATH</key>" in plist
    assert "/Applications/Docker.app/Contents/Resources/bin" in plist


def test_macos_master_artifacts_do_not_embed_dev_credentials_or_bearer_tokens() -> None:
    combined = "\n".join(_read(path) for path in (MASTER_PLIST, INSTALL_SCRIPT, UNINSTALL_SCRIPT))

    for forbidden in FORBIDDEN_PRODUCT_STRINGS:
        assert forbidden not in combined


def test_macos_installer_validates_target_and_dependencies() -> None:
    script = _read(INSTALL_SCRIPT)

    assert '[[ "$(uname -s)" != "Darwin" ]]' in script
    assert "This installer target is macOS master" in script
    assert "arm64" in script
    assert "x86_64" in script
    assert "/Applications/Docker.app" in script
    assert "launchctl bootstrap system" in script
    assert "$CONFIG_DIR/master.env" in script
    assert "$CONFIG_DIR/supervisor.json" in script
    assert "$CONFIG_DIR/secrets/postgres_password" in script
    assert "$CONFIG_DIR/nats/nats.conf" in script
    assert "$CONFIG_DIR/mediamtx/mediamtx.yml" in script
    assert "$DATA_DIR/credentials" in script
    assert "VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials" in script
    assert "VEZOR_PUBLIC_KEYCLOAK_URL=" in script
    assert "VEZOR_PUBLIC_OIDC_AUTHORITY=${PUBLIC_URL%:*}:8080/realms/argus-dev" in script
    assert "VEZOR_OIDC_CLIENT_ID=argus-frontend" in script
    assert "  /run/vezor" not in script
    assert 'chmod 0644 "$MASTER_ENV"' in script
    assert 'old_umask="$(umask)"' in script


def test_macos_installer_exposes_safe_install_options() -> None:
    script = _read(INSTALL_SCRIPT)

    for option in (
        "--dry-run",
        "--version",
        "--manifest",
        "--public-url",
        "--data-dir",
    ):
        assert option in script

    assert "first-run" in script
    assert "/etc/vezor/master.json" in script
    assert "manifest_image_ref backend" in script


def test_macos_uninstall_preserves_data_unless_explicitly_confirmed() -> None:
    script = _read(UNINSTALL_SCRIPT)

    assert "launchctl bootout system" in script
    assert "--purge-data" in script
    assert "delete-vezor-data" in script
    assert "Preserving Vezor data" in script
