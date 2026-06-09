from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).parents[3]
DOCKERFILE = REPO_ROOT / "backend" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
MAKEFILE = REPO_ROOT / "Makefile"


def test_central_dockerfile_supports_installer_compose_commands() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "distroless" not in dockerfile
    assert 'ENV PATH="/app/.venv/bin:$PATH"' in dockerfile
    assert "apt-get install -y --no-install-recommends curl" in dockerfile
    assert "CMD [" in dockerfile
    assert "ENTRYPOINT [" not in dockerfile


def test_central_dockerfile_installs_worker_vision_dependencies() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "--group vision" in dockerfile


def test_central_runtime_image_installs_processed_stream_publisher() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "ffmpeg" in dockerfile


def test_central_runtime_image_packages_pack_manifests() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    central_build_context = (
        "\t\t-f backend/Dockerfile \\\n"
        "\t\t-t $(REGISTRY)/argus-backend:$(TAG) \\\n"
        "\t\t."
    )

    assert "COPY packs ./packs" in dockerfile
    assert central_build_context in makefile


def test_central_dockerfile_installs_dependencies_before_source_copy() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    dependency_copy = (
        "COPY backend/pyproject.toml backend/uv.lock backend/alembic.ini "
        "backend/README.md ./"
    )
    sync_command = (
        "uv sync --locked --no-dev --no-install-project --group runtime --group llm --group vision"
    )
    source_copy = "COPY backend/src ./src"
    pack_copy = "COPY packs ./packs"

    assert dockerfile.index(dependency_copy) < dockerfile.index(sync_command)
    assert dockerfile.index(sync_command) < dockerfile.index(source_copy)
    assert dockerfile.index(sync_command) < dockerfile.index(pack_copy)


def test_central_repo_build_context_is_constrained() -> None:
    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()

    assert "*" in dockerignore
    assert "!backend/src/**" in dockerignore
    assert "!packs/**" in dockerignore
