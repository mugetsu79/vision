from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from vezor_installer.model_bundle import build_manifest_entry, verify_model_bundle

REPO_ROOT = Path(__file__).parents[2]
BUNDLE_DIR = REPO_ROOT / "installer" / "assets" / "models"


def test_bundled_yolo26_models_are_present_and_manifested() -> None:
    result = verify_model_bundle(BUNDLE_DIR)

    assert result.required_catalog_ids == {
        "yolo26n-coco-onnx",
        "yolo26s-coco-onnx",
    }
    assert result.missing_files == []
    assert result.hash_mismatches == []
    assert result.diagnostics == []
    assert result.files_by_catalog_id["yolo26n-coco-onnx"].name == "yolo26n.onnx"
    assert result.files_by_catalog_id["yolo26s-coco-onnx"].name == "yolo26s.onnx"


def test_verify_model_bundle_detects_missing_model_file(tmp_path: Path) -> None:
    _write_model(tmp_path / "yolo26s.onnx", b"small-model")
    _write_manifest(
        tmp_path,
        [
            _manifest_entry("yolo26n-coco-onnx", "yolo26n.onnx", b"nano-model"),
            _manifest_entry("yolo26s-coco-onnx", "yolo26s.onnx", b"small-model"),
        ],
    )

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == ["yolo26n.onnx"]
    assert result.hash_mismatches == []
    assert result.diagnostics == []


def test_verify_model_bundle_detects_missing_required_manifest_entry(tmp_path: Path) -> None:
    yolo26n = tmp_path / "yolo26n.onnx"
    _write_model(yolo26n, b"nano-model")
    _write_manifest(
        tmp_path,
        [build_manifest_entry(catalog_id="yolo26n-coco-onnx", file_path=yolo26n)],
    )

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == ["yolo26s-coco-onnx:manifest-entry"]
    assert result.hash_mismatches == []
    assert result.diagnostics == []


def test_verify_model_bundle_detects_sha_mismatch(tmp_path: Path) -> None:
    _write_complete_bundle(
        tmp_path,
        yolo26n_entry=_manifest_entry(
            "yolo26n-coco-onnx",
            "yolo26n.onnx",
            b"nano-model",
            sha256="0" * 64,
        ),
    )

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == []
    assert result.hash_mismatches == ["yolo26n.onnx"]
    assert result.diagnostics == []


def test_verify_model_bundle_detects_size_mismatch(tmp_path: Path) -> None:
    _write_complete_bundle(
        tmp_path,
        yolo26n_entry=_manifest_entry(
            "yolo26n-coco-onnx",
            "yolo26n.onnx",
            b"nano-model",
            size_bytes=1,
        ),
    )

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == []
    assert result.hash_mismatches == []
    assert result.diagnostics == ["yolo26n.onnx:size-mismatch"]


@pytest.mark.parametrize("unsafe_path", ["../outside.onnx", "/tmp/outside.onnx"])
def test_verify_model_bundle_detects_unsafe_manifest_path(
    tmp_path: Path, unsafe_path: str
) -> None:
    _write_model(tmp_path / "yolo26s.onnx", b"small-model")
    _write_manifest(
        tmp_path,
        [
            _manifest_entry("yolo26n-coco-onnx", unsafe_path, b"outside-model"),
            _manifest_entry("yolo26s-coco-onnx", "yolo26s.onnx", b"small-model"),
        ],
    )

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == ["yolo26n-coco-onnx:manifest-entry"]
    assert result.hash_mismatches == []
    assert result.diagnostics == [f"{unsafe_path}:unsafe-path"]
    assert "yolo26n-coco-onnx" not in result.files_by_catalog_id


def test_verify_model_bundle_detects_unsupported_schema_version(tmp_path: Path) -> None:
    _write_complete_bundle(tmp_path, schema_version=2)

    result = verify_model_bundle(tmp_path)

    assert result.missing_files == []
    assert result.hash_mismatches == []
    assert result.diagnostics == ["manifest.json:unsupported-schema-version:2"]


def _write_complete_bundle(
    bundle_dir: Path,
    *,
    schema_version: int = 1,
    yolo26n_entry: dict[str, object] | None = None,
) -> None:
    _write_model(bundle_dir / "yolo26n.onnx", b"nano-model")
    _write_model(bundle_dir / "yolo26s.onnx", b"small-model")
    _write_manifest(
        bundle_dir,
        [
            yolo26n_entry
            or _manifest_entry("yolo26n-coco-onnx", "yolo26n.onnx", b"nano-model"),
            _manifest_entry("yolo26s-coco-onnx", "yolo26s.onnx", b"small-model"),
        ],
        schema_version=schema_version,
    )


def _write_manifest(
    bundle_dir: Path, models: list[dict[str, object]], *, schema_version: int = 1
) -> None:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_text(
        json.dumps({"schema_version": schema_version, "models": models}),
        encoding="utf-8",
    )


def _write_model(path: Path, data: bytes) -> None:
    path.write_bytes(data)


def _manifest_entry(
    catalog_id: str,
    path: str,
    data: bytes,
    *,
    sha256: str | None = None,
    size_bytes: int | None = None,
) -> dict[str, object]:
    return {
        "catalog_id": catalog_id,
        "path": path,
        "sha256": sha256 or hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data) if size_bytes is None else size_bytes,
    }
