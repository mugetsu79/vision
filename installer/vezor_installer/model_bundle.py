from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_CATALOG_IDS = frozenset({"yolo26n-coco-onnx", "yolo26s-coco-onnx"})


@dataclass(frozen=True, slots=True)
class ModelBundleVerification:
    required_catalog_ids: set[str]
    files_by_catalog_id: dict[str, Path]
    missing_files: list[str]
    hash_mismatches: list[str]
    diagnostics: list[str]


def verify_model_bundle(bundle_dir: Path) -> ModelBundleVerification:
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("models", [])
    files_by_catalog_id: dict[str, Path] = {}
    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    diagnostics: list[str] = []
    schema_version = manifest.get("schema_version")
    if schema_version != 1:
        diagnostics.append(f"manifest.json:unsupported-schema-version:{schema_version}")
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        catalog_id = str(entry.get("catalog_id", ""))
        relative_path = str(entry.get("path", ""))
        if catalog_id not in REQUIRED_CATALOG_IDS:
            continue
        if not _is_safe_bundle_filename(relative_path):
            diagnostics.append(f"{relative_path}:unsafe-path")
            continue
        model_path = bundle_dir / relative_path
        files_by_catalog_id[catalog_id] = model_path
        if not model_path.exists():
            missing_files.append(relative_path)
            continue
        expected_size = entry.get("size_bytes")
        if not isinstance(expected_size, int) or model_path.stat().st_size != expected_size:
            diagnostics.append(f"{relative_path}:size-mismatch")
        actual_sha = _sha256_file(model_path)
        expected_sha = str(entry.get("sha256", ""))
        if actual_sha != expected_sha:
            hash_mismatches.append(relative_path)
    for catalog_id in sorted(REQUIRED_CATALOG_IDS - set(files_by_catalog_id)):
        missing_files.append(f"{catalog_id}:manifest-entry")
    return ModelBundleVerification(
        required_catalog_ids=set(REQUIRED_CATALOG_IDS),
        files_by_catalog_id=files_by_catalog_id,
        missing_files=missing_files,
        hash_mismatches=hash_mismatches,
        diagnostics=diagnostics,
    )


def build_manifest_entry(*, catalog_id: str, file_path: Path) -> dict[str, Any]:
    return {
        "catalog_id": catalog_id,
        "path": file_path.name,
        "sha256": _sha256_file(file_path),
        "size_bytes": file_path.stat().st_size,
    }


def _is_safe_bundle_filename(relative_path: str) -> bool:
    path = Path(relative_path)
    return bool(relative_path) and not path.is_absolute() and path.name == relative_path


def _sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as model_file:
        for chunk in iter(lambda: model_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
