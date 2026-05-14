from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"


def test_central_dockerfile_supports_installer_compose_commands() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "distroless" not in dockerfile
    assert 'ENV PATH="/app/.venv/bin:$PATH"' in dockerfile
    assert "apt-get install -y --no-install-recommends curl" in dockerfile
    assert "CMD [" in dockerfile
    assert "ENTRYPOINT [" not in dockerfile
