from pathlib import Path

EDGE_COMPOSE_PATH = Path(__file__).resolve().parents[3] / "infra" / "docker-compose.edge.yml"


def test_edge_compose_requires_master_runtime_environment() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")

    assert "${ARGUS_EDGE_CAMERA_ID:?" in compose
    assert "${ARGUS_API_BASE_URL:?" in compose
    assert "${ARGUS_API_BEARER_TOKEN:?" in compose
    assert "${ARGUS_DB_URL:?" in compose
    assert "${ARGUS_MINIO_ENDPOINT:?" in compose


def test_edge_compose_does_not_default_master_services_to_jetson_host() -> None:
    compose = EDGE_COMPOSE_PATH.read_text(encoding="utf-8")
    db_fallback = "ARGUS_DB_URL:-postgresql+asyncpg://argus:argus@host.docker.internal:5432/argus"

    assert "ARGUS_API_BASE_URL:-http://host.docker.internal:8000" not in compose
    assert db_fallback not in compose
    assert "ARGUS_MINIO_ENDPOINT:-host.docker.internal:9000" not in compose
