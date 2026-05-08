from pathlib import Path

EDGE_COMPOSE_PATH = Path(__file__).resolve().parents[3] / "infra" / "docker-compose.edge.yml"


def test_edge_compose_requires_master_runtime_environment() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "${ARGUS_EDGE_CAMERA_ID:?" in compose
    assert "${ARGUS_API_BASE_URL:?" in compose
    assert "${ARGUS_API_BEARER_TOKEN:?" in compose
    assert "${ARGUS_DB_URL:?" in compose
    assert "${ARGUS_NATS_URL:?" in compose
    assert "${ARGUS_MINIO_ENDPOINT:?" in compose
    assert "YOLO_CONFIG_DIR: /tmp" in compose


def test_edge_compose_passes_jetson_ort_wheel_build_arg() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "JETSON_ORT_WHEEL_URL: ${JETSON_ORT_WHEEL_URL:-}" in compose


def test_edge_compose_forwards_jetson_rtsp_tuning_environment() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "ARGUS_JETSON_RTSP_PROTOCOLS: ${ARGUS_JETSON_RTSP_PROTOCOLS:-tcp}" in compose
    assert "ARGUS_JETSON_RTSP_LATENCY_MS: ${ARGUS_JETSON_RTSP_LATENCY_MS:-200}" in compose
    assert (
        "ARGUS_JETSON_RTSP_DROP_ON_LATENCY: "
        "${ARGUS_JETSON_RTSP_DROP_ON_LATENCY:-true}"
    ) in compose


def test_edge_mediamtx_jwks_points_at_master_backend() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "MTX_AUTHJWTJWKS: ${ARGUS_API_BASE_URL:?" in compose
    assert "/.well-known/argus/mediamtx/jwks.json" in compose


def test_edge_compose_does_not_default_master_services_to_jetson_host() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")
    db_fallback = "ARGUS_DB_URL:-postgresql+asyncpg://argus:argus@host.docker.internal:5432/argus"

    assert "ARGUS_API_BASE_URL:-http://host.docker.internal:8000" not in compose
    assert db_fallback not in compose
    assert "ARGUS_NATS_URL:-nats://nats-leaf:4222" not in compose
    assert "ARGUS_MINIO_ENDPOINT:-host.docker.internal:9000" not in compose
