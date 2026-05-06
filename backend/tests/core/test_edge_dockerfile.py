import ast
from pathlib import Path

EDGE_DOCKERFILE_PATH = Path(__file__).resolve().parents[2] / "Dockerfile.edge"
BACKEND_ROOT = EDGE_DOCKERFILE_PATH.parent
ARGUS_SOURCE_ROOT = BACKEND_ROOT / "src" / "argus"
PYTHON_310_ASSERTION = (
    'python -c "import sys; assert sys.version_info[:2] == (3, 10), sys.version"'
)
JETSON_ORT_INSTALL_COMMAND = (
    '"$UV_PROJECT_ENVIRONMENT/bin/pip" install --no-cache-dir "$JETSON_ORT_WHEEL_URL"'
)


def test_edge_dockerfile_uses_system_python_310_virtualenv() -> None:
    dockerfile = EDGE_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert 'python3 -m venv "$UV_PROJECT_ENVIRONMENT"' in dockerfile
    assert PYTHON_310_ASSERTION in dockerfile
    assert "uv python install 3.12" not in dockerfile
    assert "--managed-python" not in dockerfile
    assert 'chown -R argus:argus /app "$UV_PROJECT_ENVIRONMENT"' in dockerfile


def test_edge_dockerfile_installs_jetson_onnxruntime_wheel_after_base_deps() -> None:
    dockerfile = EDGE_DOCKERFILE_PATH.read_text(encoding="utf-8")

    assert "requirements-edge.txt" in dockerfile
    assert 'uv pip install --python "$UV_PROJECT_ENVIRONMENT/bin/python"' in dockerfile
    assert "--no-cache -r requirements-edge.txt" in dockerfile
    assert 'if [ -n "$JETSON_ORT_WHEEL_URL" ]' in dockerfile
    assert JETSON_ORT_INSTALL_COMMAND in dockerfile


def test_edge_dockerfile_smoke_tests_python_stdlib_before_runtime() -> None:
    dockerfile = EDGE_DOCKERFILE_PATH.read_text(encoding="utf-8")
    smoke_test = '/app/.venv/bin/python -c "import encodings, sys; print(sys.version)"'

    assert smoke_test in dockerfile
    assert dockerfile.index("USER argus") < dockerfile.index(smoke_test)


def test_argus_runtime_sources_parse_as_python_310() -> None:
    for path in ARGUS_SOURCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path), feature_version=(3, 10))


def test_argus_runtime_uses_compat_shims_for_python_310_stdlib_gaps() -> None:
    disallowed_imports = (
        "from datetime import UTC",
        "from enum import StrEnum",
    )

    offenders = {
        path.relative_to(BACKEND_ROOT): disallowed
        for path in ARGUS_SOURCE_ROOT.rglob("*.py")
        if path.name != "compat.py"
        for disallowed in disallowed_imports
        if disallowed in path.read_text(encoding="utf-8")
    }

    assert offenders == {}
