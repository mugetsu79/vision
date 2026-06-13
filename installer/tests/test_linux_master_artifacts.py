from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
MASTER_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.master.yml"
MASTER_SERVICE = REPO_ROOT / "infra" / "install" / "systemd" / "vezor-master.service"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "install-master.sh"
UNINSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "uninstall.sh"
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
    "pnpm dev",
    "uvicorn argus.main:app --reload",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _service_block(compose: str, service_name: str) -> str:
    start = compose.index(f"  {service_name}:\n")
    lines = compose[start:].splitlines()
    block = [lines[0]]
    for line in lines[1:]:
        if line.startswith("  ") and not line.startswith("    "):
            break
        block.append(line)
    return "\n".join(block)


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

    assert "${VEZOR_DATA_DIR:-/var/lib/vezor}/postgres:/var/lib/postgresql/data" in compose
    assert "${VEZOR_DATA_DIR:-/var/lib/vezor}/minio:/data" in compose
    assert "${VEZOR_DATA_DIR:-/var/lib/vezor}/evidence:/var/lib/vezor/evidence" in compose
    assert "ARGUS_INCIDENT_LOCAL_STORAGE_ROOT: /var/lib/vezor/evidence" in compose
    assert '"${VEZOR_MEDIAMTX_WEBRTC_UDP_BIND:-0.0.0.0}:8189:8189/udp"' in compose
    assert "${VEZOR_CONFIG_DIR:-/etc/vezor}/master.json:/etc/vezor/master.json:ro" in compose
    assert (
        "${VEZOR_CONFIG_DIR:-/etc/vezor}/supervisor.json:"
        "/etc/vezor/supervisor.json:ro"
    ) in compose
    assert (
        "${VEZOR_CREDENTIALS_HOST_DIR:-/var/lib/vezor/credentials}"
        ":/run/vezor/credentials:ro"
    ) in compose
    assert "ARGUS_KEYCLOAK_ISSUER" in compose
    assert "ARGUS_KEYCLOAK_FRONTEND_CLIENT_ID" in compose
    assert "ARGUS_CORS_ALLOWED_ORIGINS" in compose
    assert "${VEZOR_PUBLIC_FRONTEND_URL:-http://localhost:3000}" in compose
    assert "backend_db_url:" in compose
    assert "central_supervisor_credential:" in compose
    assert (
        "file: ${VEZOR_CONFIG_DIR:-/etc/vezor}/secrets/central_supervisor_credential"
        in compose
    )
    assert "target: ARGUS_DB_URL" in compose
    assert "target: ARGUS_MINIO_ACCESS_KEY" in compose
    assert "target: ARGUS_MINIO_SECRET_KEY" in compose
    assert "ARGUS_DB_URL: postgresql" not in compose
    assert "target: ARGUS_KEYCLOAK_ADMIN_USERNAME" in compose
    assert "target: ARGUS_KEYCLOAK_ADMIN_PASSWORD" in compose
    assert "link_reflector_secret:" in compose
    assert (
        "${VEZOR_LINK_REFLECTOR_SECRET_FILE:-${VEZOR_CONFIG_DIR:-/etc/vezor}"
        "/secrets/link_reflector_secret}"
    ) in compose
    assert "target: ARGUS_LINK_REFLECTOR_SECRET" in compose
    assert "target: ARGUS_CENTRAL_SUPERVISOR_CREDENTIAL" in compose
    assert "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS" in compose


def test_linux_master_compose_mounts_link_throughput_payload_read_only() -> None:
    compose = _read(MASTER_COMPOSE)
    backend = _service_block(compose, "backend")

    assert "ARGUS_LINK_THROUGHPUT_PAYLOAD_PATH" in backend
    assert "ARGUS_LINK_THROUGHPUT_PAYLOAD_MAX_BYTES" in backend
    assert "ARGUS_LINK_THROUGHPUT_PAYLOAD_PUBLIC_URL" in backend
    assert (
        "${VEZOR_LINK_THROUGHPUT_HOST_DIR:-${VEZOR_DATA_DIR:-/var/lib/vezor}"
        "/link-throughput}:/var/lib/vezor/link-throughput:ro"
    ) in backend


def test_linux_master_compose_disables_unconfigured_tracing_by_default() -> None:
    compose = _read(MASTER_COMPOSE)
    backend = _service_block(compose, "backend")

    assert "ARGUS_ENABLE_TRACING: ${VEZOR_ENABLE_TRACING:-false}" in backend
    assert "ARGUS_OTLP_ENDPOINT: ${VEZOR_OTLP_ENDPOINT:-http://otel-collector:4318}" in backend


def test_linux_master_compose_runs_backend_with_product_environment_defaults() -> None:
    compose = _read(MASTER_COMPOSE)
    backend = _service_block(compose, "backend")

    assert "ARGUS_ENVIRONMENT: ${VEZOR_ENVIRONMENT:-production}" in backend


def test_linux_master_supervisor_provides_runtime_worker_connectivity() -> None:
    compose = _read(MASTER_COMPOSE)
    supervisor = _service_block(compose, "vezor-supervisor")

    assert "${VEZOR_MASTER_ENV_FILE:-/etc/vezor/master.env}" in supervisor
    assert "ARGUS_NATS_URL: nats://nats:4222" in supervisor
    assert "ARGUS_REDIS_URL: redis://redis:6379/0" in supervisor
    assert "ARGUS_MEDIAMTX_API_URL: http://mediamtx:9997" in supervisor
    assert "ARGUS_MEDIAMTX_RTSP_BASE_URL: rtsp://mediamtx:8554" in supervisor
    assert "ARGUS_MEDIAMTX_WEBRTC_BASE_URL: http://mediamtx:8889" in supervisor
    assert "ARGUS_MEDIAMTX_HLS_BASE_URL: http://mediamtx:8888" in supervisor
    assert "ARGUS_MEDIAMTX_MJPEG_BASE_URL: http://mediamtx:8888" in supervisor
    assert "ARGUS_MEDIAMTX_WHIP_BASE_URL: http://mediamtx:8889" in supervisor
    assert "ARGUS_MINIO_ENDPOINT: minio:9000" in supervisor
    assert 'ARGUS_MINIO_SECURE: "false"' in supervisor
    assert "${VEZOR_DATA_DIR:-/var/lib/vezor}/models:/models:ro" in supervisor
    assert "target: ARGUS_DB_URL" in supervisor
    assert "target: ARGUS_MINIO_ACCESS_KEY" in supervisor
    assert "target: ARGUS_MINIO_SECRET_KEY" in supervisor


def test_linux_master_supervisor_caps_worker_thread_fanout() -> None:
    compose = _read(MASTER_COMPOSE)
    supervisor = _service_block(compose, "vezor-supervisor")

    assert "OMP_NUM_THREADS: ${VEZOR_WORKER_OMP_NUM_THREADS:-1}" in supervisor
    assert "OPENBLAS_NUM_THREADS: ${VEZOR_WORKER_OPENBLAS_NUM_THREADS:-1}" in supervisor
    assert "MKL_NUM_THREADS: ${VEZOR_WORKER_MKL_NUM_THREADS:-1}" in supervisor
    assert "NUMEXPR_NUM_THREADS: ${VEZOR_WORKER_NUMEXPR_NUM_THREADS:-1}" in supervisor
    assert (
        "ARGUS_INFERENCE_SESSION_INTER_OP_THREADS: "
        "${VEZOR_WORKER_INFERENCE_SESSION_INTER_OP_THREADS:-1}"
    ) in supervisor
    assert (
        "ARGUS_INFERENCE_SESSION_INTRA_OP_THREADS: "
        "${VEZOR_WORKER_INFERENCE_SESSION_INTRA_OP_THREADS:-2}"
    ) in supervisor
    assert (
        "ARGUS_CPU_FALLBACK_PROCESSING_FPS_CAP: "
        "${VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP:-}"
    ) in supervisor


def test_linux_master_nats_healthcheck_uses_nats_server_binary() -> None:
    compose = _read(MASTER_COMPOSE)

    assert 'test: ["CMD", "/nats-server", "-t", "-c", "/etc/nats/nats.conf"]' in compose
    assert 'test: ["CMD", "wget", "-q", "-O", "-", "http://127.0.0.1:8222/healthz"]' not in compose


def test_linux_master_postgres_preloads_timescaledb_for_existing_volumes() -> None:
    compose = _read(MASTER_COMPOSE)

    assert 'command: ["postgres", "-c", "shared_preload_libraries=timescaledb"]' in compose


def test_linux_master_keycloak_first_boot_does_not_use_optimized_mode() -> None:
    compose = _read(MASTER_COMPOSE)

    assert 'exec /opt/keycloak/bin/kc.sh start' in compose
    assert 'command: ["start", "--optimized"]' not in compose


def test_linux_master_keycloak_exports_secret_files_before_start() -> None:
    compose = _read(MASTER_COMPOSE)

    assert 'entrypoint: ["/bin/sh", "-c"]' in compose
    assert 'KC_BOOTSTRAP_ADMIN_USERNAME="$(cat /run/secrets/keycloak_admin_username)"' in compose
    assert 'KC_BOOTSTRAP_ADMIN_PASSWORD="$(cat /run/secrets/keycloak_admin_password)"' in compose
    assert 'KC_DB_PASSWORD="$(cat /run/secrets/postgres_password)"' in compose
    assert "KC_DB_PASSWORD_FILE" not in compose
    assert "KC_BOOTSTRAP_ADMIN_USERNAME_FILE" not in compose
    assert "KC_BOOTSTRAP_ADMIN_PASSWORD_FILE" not in compose


def test_linux_master_keycloak_has_container_native_healthcheck() -> None:
    compose = _read(MASTER_COMPOSE)

    assert "timeout 3 bash -c '</dev/tcp/127.0.0.1/8080'" in compose
    assert "start_period: 30s" in compose
    assert "retries: 30" in compose
    assert "keycloak:\n        condition: service_healthy" in compose


def test_linux_master_compose_uses_installer_runtime_entrypoints() -> None:
    compose = _read(MASTER_COMPOSE)

    assert "      - -lc" not in compose
    assert "      - -c" in compose
    assert "/app/.venv/bin/alembic upgrade head && /app/.venv/bin/uvicorn" in compose
    assert "--no-access-log" in compose
    assert "      - /app/.venv/bin/python" in compose
    assert '["CMD", "/app/.venv/bin/python", "-m", "argus.supervisor.runner"' in compose


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
    assert "write_systemd_path_override" in script
    assert 'Environment="VEZOR_MASTER_CONFIG=$MASTER_CONFIG"' in script
    assert 'Environment="VEZOR_MASTER_ENV_FILE=$MASTER_ENV"' in script
    assert 'ExecStart=/opt/vezor/current/bin/vezor-master up --config "$MASTER_CONFIG"' in script
    assert 'ExecStop=/opt/vezor/current/bin/vezor-master down --config "$MASTER_CONFIG"' in script
    assert "first-run" in script
    assert "$CONFIG_DIR/master.env" in script
    assert "$CONFIG_DIR/supervisor.json" in script
    assert "$CONFIG_DIR/secrets/postgres_password" in script
    assert "$CONFIG_DIR/secrets/backend_db_url" in script
    assert "$CONFIG_DIR/secrets/link_reflector_secret" in script
    assert "$CONFIG_DIR/secrets/central_supervisor_credential" in script
    assert "write_backend_db_url_secret" in script
    assert (
        'write_prefixed_secret_if_missing "$CONFIG_DIR/secrets/central_supervisor_credential" '
        '"vzcred_"'
    ) in script
    assert (
        'run install -m 0640 "$CONFIG_DIR/secrets/central_supervisor_credential" '
        '"$DATA_DIR/credentials/supervisor.credential"'
    ) in script
    assert "$CONFIG_DIR/nats/nats.conf" in script
    assert "$CONFIG_DIR/mediamtx/mediamtx.yml" in script
    assert "$DATA_DIR/credentials" in script
    assert "VEZOR_CONFIG_DIR=$CONFIG_DIR" in script
    assert "VEZOR_DATA_DIR=$DATA_DIR" in script
    assert "VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials" in script
    assert "check_udp_port_available" in script
    assert "for port in 8189 8622" in script
    assert "VEZOR_LINK_REFLECTOR_ENABLED=true" in script
    assert "VEZOR_LINK_REFLECTOR_SECRET_FILE=$CONFIG_DIR/secrets/link_reflector_secret" in script
    assert "VEZOR_PUBLIC_KEYCLOAK_URL=" in script
    assert "VEZOR_PUBLIC_OIDC_AUTHORITY=$PUBLIC_OIDC_AUTHORITY" in script
    assert "${PUBLIC_URL%:*}" not in script
    assert "VEZOR_OIDC_CLIENT_ID=argus-frontend" in script
    assert 'chmod 0644 "$MASTER_ENV"' in script
    assert 'old_umask="$(umask)"' in script
    assert "manifest_image_ref backend" in script
    assert "timescale/timescaledb:latest-pg16" in script


def test_linux_master_install_creates_link_throughput_payload() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "VEZOR_LINK_THROUGHPUT_DIR" in script
    assert "vezor-speed-test-64MiB.bin" in script
    assert "67108864" in script
    assert "vezor-link-throughput-v1" in script
    assert "create_link_throughput_payload" in script
    assert "sha256sum" in script or "shasum -a 256" in script
    assert "VEZOR_LINK_THROUGHPUT_PAYLOAD_PUBLIC_URL" in script


def test_linux_master_installs_bundled_yolo26_models() -> None:
    script = _read(INSTALL_SCRIPT)
    function_start = script.index("install_bundled_models() {")
    function_end = script.index("\n}\n\nmanifest_image_ref", function_start)
    function_block = script[function_start:function_end]

    assert "install_bundled_models" in script
    assert "/opt/vezor/current/installer/assets/models" in script
    assert "$DATA_DIR/models/yolo26n.onnx" in script
    assert "$DATA_DIR/models/yolo26s.onnx" in script
    assert "sha256 mismatch for bundled model" in script
    assert 'if [[ "$DRY_RUN" -eq 0 && ! -f "$manifest_path" ]]; then' in function_block
    assert 'if [[ ! -f "$manifest_path" ]]; then' not in function_block
    copy_index = function_block.index(
        'run install -m 0644 "$bundle_dir/yolo26n.onnx" "$DATA_DIR/models/yolo26n.onnx"'
    )
    dry_run_index = function_block.index('if [[ "$DRY_RUN" -eq 1 ]]; then')
    assert copy_index < dry_run_index


def test_linux_master_installer_exposes_browser_auth_for_non_loopback_public_url() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "public_hostname_from_url" in script
    assert "public_origin_with_port" in script
    assert "oidc_disable_pkce_for_public_url" in script
    assert 'KEYCLOAK_BIND="0.0.0.0"' in script
    assert "printf 'true\\n'" in script
    assert (
        'OIDC_DISABLE_PKCE="$(oidc_disable_pkce_for_public_url '
        '"$PUBLIC_URL" "$PUBLIC_HOSTNAME")"'
    ) in script
    assert 'PUBLIC_API_BASE_URL="$(public_origin_with_port "$PUBLIC_URL" 8000)"' in script
    assert 'PUBLIC_KEYCLOAK_URL="$(public_origin_with_port "$PUBLIC_URL" 8080)"' in script
    assert 'PUBLIC_OIDC_AUTHORITY="$PUBLIC_KEYCLOAK_URL/realms/argus-dev"' in script
    assert "VEZOR_KEYCLOAK_BIND=$KEYCLOAK_BIND" in script
    assert "VEZOR_KEYCLOAK_HOSTNAME=$PUBLIC_KEYCLOAK_URL" in script
    assert "VEZOR_OIDC_DISABLE_PKCE=$OIDC_DISABLE_PKCE" in script


def test_linux_master_installer_renders_mediamtx_for_public_network_host() -> None:
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


def test_linux_master_installer_preserves_existing_central_supervisor_identity() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "read_existing_supervisor_id" in script
    assert 'CENTRAL_SUPERVISOR_ID="$(read_existing_supervisor_id "$SUPERVISOR_CONFIG")"' in script
    assert 'CENTRAL_SUPERVISOR_ID="${CENTRAL_SUPERVISOR_ID:-vezor-master}"' in script
    assert '"supervisor_id": "$CENTRAL_SUPERVISOR_ID"' in script


def test_linux_dev_installer_builds_local_master_images_before_systemd_start() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "manifest_release_channel" in script
    assert "build_local_master_images" in script
    assert '[[ "$(manifest_release_channel)" != "dev" ]]' in script
    assert (
        '$CONTAINER_ENGINE build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current'
    ) in script
    assert (
        '$CONTAINER_ENGINE build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current/backend'
    ) not in script
    assert (
        '$CONTAINER_ENGINE build -f /opt/vezor/current/frontend/Dockerfile '
        '-t "$FRONTEND_IMAGE"'
    ) in script
    assert '$CONTAINER_ENGINE tag "$BACKEND_IMAGE" "$SUPERVISOR_IMAGE"' in script
    assert "build_local_master_images" in script.split("run systemctl daemon-reload")[0]


def test_linux_master_packaging_keeps_fleetops_pack_routes_and_api_assets() -> None:
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
        '$CONTAINER_ENGINE build -f /opt/vezor/current/backend/Dockerfile '
        '-t "$BACKEND_IMAGE" /opt/vezor/current'
    ) in script
    assert (
        '$CONTAINER_ENGINE build -f /opt/vezor/current/backend/Dockerfile '
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


def test_linux_uninstall_preserves_data_unless_explicitly_confirmed() -> None:
    script = _read(UNINSTALL_SCRIPT)

    assert "--purge-data" in script
    assert "delete-vezor-data" in script
    assert "Preserving Vezor data" in script
