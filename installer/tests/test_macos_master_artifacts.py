from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
MASTER_PLIST = REPO_ROOT / "infra" / "install" / "launchd" / "com.vezor.master.plist"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "macos" / "install-master.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "installer" / "macos" / "uninstall.sh"
BACKEND_DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
MARITIME_PACK = REPO_ROOT / "packs" / "maritime-fleet" / "pack.yaml"
TRAFFIC_PACK = REPO_ROOT / "packs" / "traffic-public-space" / "pack.yaml"
FRONTEND_ROUTER = REPO_ROOT / "frontend" / "src" / "app" / "router.tsx"
WORKSPACE_NAV = REPO_ROOT / "frontend" / "src" / "components" / "layout" / "workspace-nav.ts"
OPENAPI_JSON = REPO_ROOT / "frontend" / "src" / "lib" / "openapi.json"
API_TYPES = REPO_ROOT / "frontend" / "src" / "lib" / "api.generated.ts"

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
    assert "<key>SuccessfulExit</key>" in plist
    assert "<false/>" in plist
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
    assert "check_port_available" in script
    assert "check_udp_port_available" in script
    assert "for port in 3000 8000 8080 8554 8888 8889 9000" in script
    assert "for port in 8189" in script
    assert 'port_owner="$(lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null)"' in script
    assert 'port_owner="$(lsof -nP -iUDP:"$port" 2>/dev/null)"' in script
    assert 'printf \'%s\\n\' "$port_owner" >&2' in script
    assert "stop_existing_master" in script
    assert "launchctl bootstrap system" in script
    assert "$CONFIG_DIR/master.env" in script
    assert "$CONFIG_DIR/supervisor.json" in script
    assert "$CONFIG_DIR/secrets/postgres_password" in script
    assert "$CONFIG_DIR/secrets/backend_db_url" in script
    assert "write_backend_db_url_secret" in script
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


def test_macos_installer_makes_secrets_readable_by_docker_desktop() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "prepare_secret_for_docker_desktop" in script
    assert 'chgrp staff "$path"' in script
    assert 'chmod 0640 "$path"' in script
    assert 'prepare_secret_for_docker_desktop "$path"' in script


def test_macos_installer_makes_bound_config_files_readable_by_docker_desktop() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "prepare_config_for_docker_desktop" in script
    assert 'echo "[dry-run] set Docker Desktop-readable config permissions $path"' in script
    assert 'chgrp staff "$path"' in script
    assert 'chmod 0640 "$path"' in script
    assert 'prepare_config_for_docker_desktop "$MASTER_CONFIG"' in script
    assert 'prepare_config_for_docker_desktop "$SUPERVISOR_CONFIG"' in script


def test_macos_installer_preserves_existing_central_supervisor_identity() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "read_existing_supervisor_id" in script
    assert 'CENTRAL_SUPERVISOR_ID="$(read_existing_supervisor_id "$SUPERVISOR_CONFIG")"' in script
    assert 'CENTRAL_SUPERVISOR_ID="${CENTRAL_SUPERVISOR_ID:-central-master-1}"' in script
    assert '"supervisor_id": "$CENTRAL_SUPERVISOR_ID"' in script


def test_macos_installer_repairs_docker_desktop_writable_state_directories() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "docker_desktop_host_user" in script
    assert '${SUDO_USER:-}' in script
    assert 'stat -f "%Su" /dev/console' in script
    assert "prepare_data_dir_for_docker_desktop" in script
    assert 'chown -R "$owner:$group" "$path"' in script
    assert 'chmod -R u+rwX "$path"' in script
    assert "Docker Desktop-writable data permissions" in script

    for data_path in (
        "$DATA_DIR/postgres",
        "$DATA_DIR/redis",
        "$DATA_DIR/nats",
        "$DATA_DIR/minio",
        "$DATA_DIR/mediamtx",
        "$DATA_DIR/credentials",
        "$DATA_DIR/evidence",
        "$DATA_DIR/bootstrap",
    ):
        assert f'  "{data_path}" \\' in script

    assert 'prepare_data_dir_for_docker_desktop "$docker_data_dir"' in script


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
    assert "timescale/timescaledb:latest-pg16" in script


def test_macos_installer_exposes_browser_auth_for_non_loopback_public_url() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "public_hostname_from_url" in script
    assert "oidc_disable_pkce_for_public_url" in script
    assert 'KEYCLOAK_BIND="0.0.0.0"' in script
    assert "printf 'true\\n'" in script
    assert (
        'OIDC_DISABLE_PKCE="$(oidc_disable_pkce_for_public_url '
        '"$PUBLIC_URL" "$PUBLIC_HOSTNAME")"'
    ) in script
    assert "PUBLIC_KEYCLOAK_URL=\"${PUBLIC_URL%:*}:8080\"" in script
    assert "VEZOR_KEYCLOAK_BIND=$KEYCLOAK_BIND" in script
    assert "VEZOR_KEYCLOAK_HOSTNAME=$PUBLIC_KEYCLOAK_URL" in script
    assert "VEZOR_OIDC_DISABLE_PKCE=$OIDC_DISABLE_PKCE" in script


def test_macos_installer_renders_mediamtx_for_public_network_host() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "render_mediamtx_config.py" in script
    assert "--frontend-origin \"$PUBLIC_URL\"" in script
    assert "--frontend-origin \"http://localhost:3000\"" in script
    assert "--frontend-origin \"http://127.0.0.1:3000\"" in script
    assert "--webrtc-host \"$PUBLIC_HOSTNAME\"" in script
    assert "--webrtc-host \"localhost\"" in script
    assert "--webrtc-host \"127.0.0.1\"" in script
    assert (
        'run install -m 0644 /opt/vezor/current/infra/mediamtx/mediamtx.yml '
        '"$CONFIG_DIR/mediamtx/mediamtx.yml"'
    ) not in script


def test_macos_dev_installer_builds_local_master_images_before_launchd_start() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "manifest_release_channel" in script
    assert "build_local_master_images" in script
    assert '[[ "$(manifest_release_channel)" != "dev" ]]' in script
    assert (
        'docker build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current'
    ) in script
    assert (
        'docker build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current/backend'
    ) not in script
    assert 'docker build -f /opt/vezor/current/frontend/Dockerfile -t "$FRONTEND_IMAGE"' in script
    assert 'docker tag "$BACKEND_IMAGE" "$SUPERVISOR_IMAGE"' in script
    assert "build_local_master_images" in script.split("run launchctl bootstrap system")[0]


def test_macos_master_packaging_keeps_fleetops_pack_routes_and_api_assets() -> None:
    script = _read(INSTALL_SCRIPT)
    backend_dockerfile = _read(BACKEND_DOCKERFILE)
    dockerignore = _read(DOCKERIGNORE)
    maritime_pack = _read(MARITIME_PACK)
    traffic_pack = _read(TRAFFIC_PACK)
    router = _read(FRONTEND_ROUTER)
    workspace_nav = _read(WORKSPACE_NAV)
    openapi = _read(OPENAPI_JSON)
    api_types = _read(API_TYPES)

    assert (
        'docker build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current'
    ) in script
    assert (
        'docker build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current/backend'
    ) not in script
    assert "COPY packs ./packs" in backend_dockerfile
    assert "!packs/" in dockerignore
    assert "!packs/**" in dockerignore
    assert "id: maritime-fleet" in maritime_pack
    assert "product_name: Vezor FleetOps" in maritime_pack
    assert "id: traffic-public-space" in traffic_pack
    assert "status: designed_not_implemented" in traffic_pack
    assert "implementation_commitment: false" in traffic_pack
    assert "traffic_runtime_code_before_activation" in traffic_pack
    for route in (
        'path: "fleetops"',
        'path: "fleetops/vessels"',
        'path: "fleetops/vessels/:vesselId"',
        'path: "fleetops/evidence"',
        'path: "fleetops/billing"',
        'path: "fleetops/support"',
        'path: "fleetops/onboarding"',
    ):
        assert route in router
    assert 'label: "FleetOps"' in workspace_nav
    for path in (
        "/api/v1/maritime",
        "/api/v1/fleet",
        "/api/v1/link",
        "/api/v1/billing",
        "/api/v1/support",
        "/api/v1/packs/maritime-fleet/runtime",
    ):
        assert path in openapi
        assert path in api_types


def test_macos_installer_starts_master_synchronously_before_launchd_registration() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "start_local_master_containers" in script
    assert 'run /opt/vezor/current/bin/vezor-master up --config "$MASTER_CONFIG"' in script
    assert "start_local_master_containers" in script.split("run launchctl bootstrap system")[0]


def test_macos_uninstall_preserves_data_unless_explicitly_confirmed() -> None:
    script = _read(UNINSTALL_SCRIPT)

    assert "launchctl bootout system" in script
    assert "--purge-data" in script
    assert "delete-vezor-data" in script
    assert "Preserving Vezor data" in script
