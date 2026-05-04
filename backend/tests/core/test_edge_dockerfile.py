from pathlib import Path

EDGE_DOCKERFILE_PATH = Path(__file__).resolve().parents[2] / "Dockerfile.edge"


def test_edge_dockerfile_keeps_managed_python_outside_root_cache() -> None:
    dockerfile = EDGE_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "UV_PYTHON_INSTALL_DIR=/opt/uv-python" in dockerfile
    assert 'uv python install 3.12 --install-dir "$UV_PYTHON_INSTALL_DIR"' in dockerfile
    assert "--managed-python" in dockerfile
    assert 'chown -R argus:argus /app "$UV_PYTHON_INSTALL_DIR"' in dockerfile


def test_edge_dockerfile_smoke_tests_python_stdlib_before_runtime() -> None:
    dockerfile = EDGE_DOCKERFILE_PATH.read_text(encoding="utf-8")
    smoke_test = '/app/.venv/bin/python -c "import encodings, sys; print(sys.version)"'

    assert smoke_test in dockerfile
    assert dockerfile.index("USER argus") < dockerfile.index(smoke_test)
