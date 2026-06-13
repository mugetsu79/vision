from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
EDGE_SERVICE = REPO_ROOT / "infra" / "install" / "systemd" / "vezor-edge.service"
EDGE_AGENT_SERVICE = REPO_ROOT / "infra" / "install" / "systemd" / "vezor-edge-agent.service"
INSTALL_SCRIPT = REPO_ROOT / "installer" / "linux" / "install-edge.sh"
PREFLIGHT = REPO_ROOT / "scripts" / "jetson-preflight.sh"
SUPERVISOR_COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.supervisor.yml"
EDGE_AGENT_WRAPPER = REPO_ROOT / "bin" / "vezor-edge-agent"
MEDIAMTX_CONFIG = REPO_ROOT / "infra" / "mediamtx" / "mediamtx.yml"
NATS_LEAF_CONFIG = REPO_ROOT / "infra" / "nats" / "leaf.conf"

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


def test_edge_agent_systemd_service_uses_node_credential_file_not_bearer_token() -> None:
    service = _read(EDGE_AGENT_SERVICE)
    wrapper = _read(EDGE_AGENT_WRAPPER)

    assert "Description=Vezor Core Link Edge Agent" in service
    assert "After=network-online.target docker.service vezor-edge.service" in service
    assert "EnvironmentFile=/etc/vezor/edge-agent.env" in service
    assert "ExecStart=/opt/vezor/current/bin/vezor-edge-agent" in service
    assert "--bearer-token-file" in wrapper
    assert "ARGUS_API_BEARER_TOKEN" not in service
    assert "ARGUS_API_BEARER_TOKEN" not in wrapper


def test_edge_agent_wrapper_removes_stale_container_before_systemd_restart() -> None:
    wrapper = _read(EDGE_AGENT_WRAPPER)

    assert '"$CONTAINER_ENGINE" rm -f vezor-edge-agent' in wrapper
    assert wrapper.index('rm -f vezor-edge-agent') < wrapper.index('"$CONTAINER_ENGINE" run')


def test_edge_installer_runs_initial_edge_throughput_sample() -> None:
    script = _read(INSTALL_SCRIPT)
    wrapper = _read(EDGE_AGENT_WRAPPER)

    assert "VEZOR_LINK_EDGE_AGENT_INCLUDE_THROUGHPUT=1" in script
    assert "vezor-edge-agent --once" in script
    assert "Initial edge-agent throughput sample" in script
    assert "--include-throughput" in wrapper


def test_edge_install_script_accepts_pairing_unpaired_and_manifest_modes() -> None:
    script = _read(INSTALL_SCRIPT)

    for option in (
        "--api-url",
        "--pairing-code",
        "--session-id",
        "--unpaired",
        "--manifest",
        "--version",
        "--frontend-url",
        "--public-stream-host",
        "--public-mediamtx-rtsp-url",
        "--jetson-ort-wheel-url",
        "--allow-cpu-onnx-runtime",
    ):
        assert option in script

    assert "manifest_image_ref edge-worker" in script
    assert "manifest_image_ref mediamtx" in script
    assert "manifest_image_ref nats" in script
    assert "build_local_edge_image" in script
    assert "/opt/vezor/current/backend/Dockerfile.edge" in script
    assert "JETSON_ORT_WHEEL_URL" in script
    assert "ALLOW_CPU_ONNX_RUNTIME" in script
    assert "PUBLIC_MEDIAMTX_RTSP_URL" in script
    assert "detect_public_stream_host" in script
    assert "existing_supervisor_config_value" in script
    assert "CONFIG_EDGE_NODE_ID" in script
    assert "Unpaired edge update requires an existing paired supervisor config" in script
    assert '"public_mediamtx_rtsp_url"' in script
    assert '"edge_node_id"' in script
    assert '"hostname"' in script
    assert "Jetson ONNX Runtime GPU wheel is required" in script
    assert "--build-arg \"ALLOW_CPU_ONNX_RUNTIME=$ALLOW_CPU_ONNX_RUNTIME\"" in script
    assert "scripts/jetson-preflight.sh --installer --json" in script
    assert "/etc/vezor/edge.json" in script
    assert "/etc/vezor/supervisor.json" in script
    assert "$CONFIG_DIR/edge.env" in script
    assert "$CONFIG_DIR/nats" in script
    assert "$CONFIG_DIR/nats/leaf.conf" in script
    assert "$CONFIG_DIR/mediamtx/mediamtx.yml" in script
    assert "write edge NATS leaf config" in script
    assert "master_nats_leaf_url" in script
    assert "write edge MediaMTX config" in script
    assert ".well-known/argus/mediamtx/jwks.json" in script
    assert "render_mediamtx_config.py" in script
    assert "--jwks-url \"${API_URL%/}/.well-known/argus/mediamtx/jwks.json\"" in script
    assert "--frontend-origin \"$FRONTEND_URL\"" in script
    assert "--webrtc-host \"$EDGE_STREAM_HOST\"" in script
    assert "$DATA_DIR/credentials" in script
    assert "VEZOR_CREDENTIALS_HOST_DIR=$DATA_DIR/credentials" in script
    assert "VEZOR_MODEL_HOST_DIR=$MODEL_DIR" in script
    assert "VEZOR_NATS_IMAGE=$NATS_IMAGE" in script
    assert "ARGUS_NATS_URL=nats://nats-leaf:4222" in script
    assert "VEZOR_NATS_LEAF_REMOTE_URL=$MASTER_NATS_LEAF_URL" in script
    assert 'chmod 0644 "$EDGE_ENV"' in script
    assert 'chmod 0644 "$EDGE_CONFIG" "$SUPERVISOR_CONFIG"' in script
    assert 'chown 10001:10001 "$DATA_DIR/credentials/supervisor.credential"' in script
    assert 'chown 10001:10001 "$MODEL_DIR"' in script
    assert 'old_umask="$(umask)"' in script
    assert "--supervisor-id" in script
    assert '--credential-path "$DATA_DIR/credentials/supervisor.credential"' in script
    assert "systemctl enable vezor-edge.service" in script
    assert "systemctl start vezor-edge.service" in script
    assert "$CONFIG_DIR/edge-agent.env" in script
    assert "ARGUS_LINK_EDGE_AGENT_CONFIG_URL" in script
    assert "install/systemd/vezor-edge-agent.service" in script
    assert "systemctl enable vezor-edge-agent.service" in script
    assert "systemctl start vezor-edge-agent.service" not in script


def test_edge_install_script_resolves_manifest_jetson_ort_wheel_before_build() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "JETSON_ORT_WHEEL_SHA256" in script
    assert "resolve_jetson_ort_wheel" in script
    assert "resolve_jetson_ort_from_manifest" in script
    assert "JETSON_PREFLIGHT_JSON" in script
    assert "run_installer_python" in script
    assert 'run_installer_python -m vezor_installer.jetson_ort' in script
    assert "python3 -m vezor_installer.jetson_ort" not in script
    assert "--build-arg \"JETSON_ORT_WHEEL_SHA256=$JETSON_ORT_WHEEL_SHA256\"" in script
    assert "Resolved Jetson GPU ONNX Runtime wheel from manifest." in script
    assert "Pass --jetson-ort-wheel-url" not in script


def test_edge_install_script_derives_network_reachable_mediamtx_inputs() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "frontend_url_from_api_url" in script
    assert "public_hostname_from_url" in script
    assert 'FRONTEND_URL="${2:?--frontend-url requires a value}"' in script
    assert 'FRONTEND_URL="$(frontend_url_from_api_url)"' in script
    assert 'EDGE_STREAM_HOST="$(public_hostname_from_url "$PUBLIC_MEDIAMTX_RTSP_URL")"' in script
    assert "f\"authJWTJWKS: {api_url}/.well-known/argus/mediamtx/jwks.json\"" not in script


def test_edge_install_script_claims_pairing_before_long_image_build() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "build_local_edge_image" in script
    assert 'run /opt/vezor/current/bin/vezorctl pair' in script
    assert script.index('run /opt/vezor/current/bin/vezorctl pair') < script.index(
        "\nbuild_local_edge_image\n"
    )


def test_edge_install_script_stops_existing_appliance_before_preflight_ports() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "stop_existing_edge_appliance" in script
    assert "systemctl stop vezor-edge.service" in script
    assert 'VEZOR_NATS_IMAGE="$NATS_IMAGE"' in script
    assert '"$RELEASE_DIR/bin/vezor-edge" down --config "$EDGE_CONFIG"' in script
    assert '"$CONTAINER_ENGINE" rm -f' in script
    assert "vezor-edge-mediamtx" in script
    assert "vezor-edge-nats-leaf" in script
    assert "vezor-supervisor" in script
    assert script.index("\nstop_existing_edge_appliance\n") < script.index(
        "scripts/jetson-preflight.sh --installer --json"
    )


def test_edge_install_script_shell_quotes_edge_agent_env_values() -> None:
    script = _read(INSTALL_SCRIPT)

    assert "shell_quote()" in script
    assert 'EDGE_AGENT_LABEL="$EDGE_NAME Core Link"' in script
    assert 'VEZOR_CONTAINER_ENGINE=$(shell_quote "$CONTAINER_ENGINE")' in script
    assert 'VEZOR_SUPERVISOR_IMAGE=$(shell_quote "$EDGE_WORKER_IMAGE")' in script
    assert 'ARGUS_API_BASE_URL=$(shell_quote "$API_URL")' in script
    assert (
        "ARGUS_LINK_EDGE_AGENT_CONFIG_URL="
        '$(shell_quote "${API_URL%/}/api/v1/link/control-targets/master/edge-agent-config")'
        in script
    )
    assert 'ARGUS_LINK_EDGE_AGENT_ID=$(shell_quote "$EDGE_NAME-core-link")' in script
    assert 'ARGUS_LINK_EDGE_AGENT_LABEL=$(shell_quote "$EDGE_AGENT_LABEL")' in script
    assert "ARGUS_LINK_EDGE_AGENT_LABEL=$EDGE_NAME Core Link" not in script


def test_edge_artifacts_do_not_embed_dev_credentials_or_bearer_tokens() -> None:
    combined = "\n".join(
        _read(path)
        for path in (
            EDGE_SERVICE,
            EDGE_AGENT_SERVICE,
            EDGE_AGENT_WRAPPER,
            INSTALL_SCRIPT,
            PREFLIGHT,
            SUPERVISOR_COMPOSE,
        )
    )

    for forbidden in FORBIDDEN_PRODUCT_STRINGS:
        assert forbidden not in combined


def test_mediamtx_config_allows_profile_suffixed_processed_paths() -> None:
    config = _read(MEDIAMTX_CONFIG)

    assert "~^cameras/[^/]+/annotated(?:-[A-Za-z0-9_.-]+)?$" in config
    assert "~^cameras/[^/]+/preview(?:-[A-Za-z0-9_.-]+)?$" in config
    assert "~^cameras/[^/]+/passthrough$" in config


def test_supervisor_compose_profile_contains_edge_services_and_secret_mounts() -> None:
    compose = _read(SUPERVISOR_COMPOSE)

    assert "  nats-leaf:" in compose
    assert "  mediamtx:" in compose
    assert "  vezor-supervisor:" in compose
    assert "${VEZOR_SUPERVISOR_IMAGE:?set VEZOR_SUPERVISOR_IMAGE}" in compose
    assert "${VEZOR_MEDIAMTX_IMAGE:?set VEZOR_MEDIAMTX_IMAGE}" in compose
    assert "${VEZOR_NATS_IMAGE:?set VEZOR_NATS_IMAGE}" in compose
    assert 'command: ["-js", "-c", "/etc/nats/nats.conf"]' in compose
    assert "/etc/vezor/nats/leaf.conf:/etc/nats/nats.conf:ro" in compose
    assert "/var/lib/vezor/nats:/data" in compose
    assert '"${VEZOR_EDGE_WEBRTC_UDP_BIND:-0.0.0.0}:8189:8189/udp"' in compose
    assert 'entrypoint: ["/app/.venv/bin/python", "-m", "argus.supervisor.runner"]' in compose
    assert "      - --config" in compose
    assert "ARGUS_NATS_URL: ${ARGUS_NATS_URL:-nats://nats-leaf:4222}" in compose
    assert 'ARGUS_NATS_MANAGE_STREAMS: "false"' in compose
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
    assert "${VEZOR_MODEL_HOST_DIR:-/var/lib/vezor/models}:/models" in compose
    assert "${VEZOR_MODEL_HOST_DIR:-/var/lib/vezor/models}:/models:ro" not in compose
    assert "      - nats-leaf" in compose


def test_supervisor_compose_caps_edge_worker_thread_fanout() -> None:
    compose = _read(SUPERVISOR_COMPOSE)

    assert "OMP_NUM_THREADS: ${VEZOR_WORKER_OMP_NUM_THREADS:-1}" in compose
    assert "OPENBLAS_NUM_THREADS: ${VEZOR_WORKER_OPENBLAS_NUM_THREADS:-1}" in compose
    assert "MKL_NUM_THREADS: ${VEZOR_WORKER_MKL_NUM_THREADS:-1}" in compose
    assert "NUMEXPR_NUM_THREADS: ${VEZOR_WORKER_NUMEXPR_NUM_THREADS:-1}" in compose
    assert (
        "ARGUS_INFERENCE_SESSION_INTER_OP_THREADS: "
        "${VEZOR_WORKER_INFERENCE_SESSION_INTER_OP_THREADS:-1}"
    ) in compose
    assert (
        "ARGUS_INFERENCE_SESSION_INTRA_OP_THREADS: "
        "${VEZOR_WORKER_INFERENCE_SESSION_INTRA_OP_THREADS:-2}"
    ) in compose
    assert (
        "ARGUS_CPU_FALLBACK_PROCESSING_FPS_CAP: "
        "${VEZOR_CPU_FALLBACK_PROCESSING_FPS_CAP:-}"
    ) in compose


def test_edge_nats_leaf_scopes_local_worker_permissions() -> None:
    config = _read(NATS_LEAF_CONFIG)

    assert "default_permissions" in config
    assert '"evt.edge.tracking.*"' in config
    assert '"evt.tracking.*"' not in config
    assert '"cmd.camera.*"' in config


def test_jetson_preflight_supports_installer_json_mode() -> None:
    preflight = _read(PREFLIGHT)

    assert "--installer" in preflight
    assert "--json" in preflight
    assert "check_port_available" in preflight
    assert "check_udp_port_available" in preflight
    assert "for port in 8189" in preflight
    assert "nvidia-container-toolkit" in preflight
    assert "Docker Compose v2 plugin is available" in preflight
