from __future__ import annotations

import tomllib
from pathlib import Path

PYPROJECT_PATH = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _vision_dependencies() -> list[str]:
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    dependency_groups = pyproject["dependency-groups"]
    return dependency_groups["vision"]


def _model_metadata_dependencies() -> list[str]:
    with PYPROJECT_PATH.open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    dependency_groups = pyproject["dependency-groups"]
    return dependency_groups["model-metadata"]


def test_model_metadata_group_uses_cpu_onnxruntime_for_backend_registration() -> None:
    model_metadata_dependencies = _model_metadata_dependencies()

    assert "onnxruntime>=1.20; sys_platform == 'linux'" in model_metadata_dependencies
    assert (
        "onnxruntime==1.17.3; sys_platform == 'darwin' and platform_machine == 'x86_64'"
        in model_metadata_dependencies
    )
    assert (
        "onnxruntime>=1.20; sys_platform == 'darwin' and platform_machine != 'x86_64'"
        in model_metadata_dependencies
    )


def test_vision_group_uses_intel_macos_compatible_onnxruntime() -> None:
    vision_dependencies = _vision_dependencies()

    assert (
        "onnxruntime==1.17.3; sys_platform == 'darwin' and platform_machine == 'x86_64'"
        in vision_dependencies
    )
    assert (
        "onnxruntime>=1.20; sys_platform == 'darwin' and platform_machine != 'x86_64'"
        in vision_dependencies
    )


def test_vision_group_uses_intel_macos_compatible_torch_stack() -> None:
    vision_dependencies = _vision_dependencies()

    assert (
        "torch==2.2.2; sys_platform == 'darwin' and platform_machine == 'x86_64'"
        in vision_dependencies
    )
    assert (
        "torchvision==0.17.2; sys_platform == 'darwin' and platform_machine == 'x86_64'"
        in vision_dependencies
    )
