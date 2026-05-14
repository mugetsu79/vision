from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
COMPOSE = REPO_ROOT / "infra" / "install" / "compose" / "compose.master.yml"
DOCKERFILE = REPO_ROOT / "frontend" / "Dockerfile"
INDEX_HTML = REPO_ROOT / "frontend" / "index.html"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_appliance_has_runtime_config_injection() -> None:
    dockerfile = _read(DOCKERFILE)
    index_html = _read(INDEX_HTML)

    assert '<script src="/config.js"></script>' in index_html
    assert "config.template.js" in dockerfile
    assert "/etc/vezor/frontend/config.template.js" in dockerfile
    assert "10-vezor-config.sh" in dockerfile
    assert "/docker-entrypoint.d/10-vezor-config.sh" in dockerfile


def test_frontend_appliance_host_port_targets_nginx_listener() -> None:
    compose = _read(COMPOSE)

    assert '"${VEZOR_FRONTEND_BIND:-0.0.0.0}:3000:8080"' in compose
