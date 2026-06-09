from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterable, Sequence
from inspect import Parameter, signature
from pathlib import Path
from typing import Any

from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms

_OPEN_VOCAB_EXPORT_METADATA = {
    "onnx": ("onnx_export", "onnxruntime"),
    "engine": ("tensorrt_engine", "tensorrt_engine"),
    "onnx_export": ("onnx_export", "onnxruntime"),
    "tensorrt_engine": ("tensorrt_engine", "tensorrt_engine"),
}

_YOLOE_EXPORT_FORMAT = {
    "onnx": "onnx",
    "engine": "engine",
    "onnx_export": "onnx",
    "tensorrt_engine": "engine",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_size(path: Path) -> int:
    return path.stat().st_size


def build_fixed_vocab_artifact_payload(
    *,
    source_model_path: Path,
    prebuilt_engine_path: Path,
    classes: list[str],
    input_shape: dict[str, int],
    target_profile: str,
    camera_id: str | None = None,
    precision: str = "fp16",
    build_duration_seconds: float | None = None,
    runtime_versions: dict[str, object] | None = None,
    builder: dict[str, object] | None = None,
) -> dict[str, object]:
    if not source_model_path.exists():
        raise FileNotFoundError(f"Source model does not exist: {source_model_path}")
    if not prebuilt_engine_path.exists():
        raise FileNotFoundError(f"Prebuilt engine does not exist: {prebuilt_engine_path}")
    payload: dict[str, object] = {
        "scope": "model",
        "kind": "tensorrt_engine",
        "capability": "fixed_vocab",
        "runtime_backend": "tensorrt_engine",
        "path": str(prebuilt_engine_path),
        "target_profile": target_profile,
        "precision": precision,
        "input_shape": dict(input_shape),
        "classes": list(classes),
        "source_model_sha256": sha256_file(source_model_path),
        "sha256": sha256_file(prebuilt_engine_path),
        "size_bytes": file_size(prebuilt_engine_path),
        "builder": builder or {"mode": "prebuilt_engine"},
        "runtime_versions": runtime_versions or {},
        "build_duration_seconds": build_duration_seconds,
    }
    if camera_id is not None:
        payload["camera_id"] = camera_id
    return payload


def build_open_vocab_scene_artifact_payloads(
    *,
    source_model_path: Path,
    camera_id: str,
    runtime_vocabulary: Iterable[object],
    export_formats: Sequence[str],
    input_shape: dict[str, int],
    target_profile: str,
    precision: str = "fp16",
    vocabulary_version: int | None = None,
    yoloe_loader: Callable[[str], Any] | None = None,
    runtime_versions: dict[str, object] | None = None,
    output_dir: Path | None = None,
) -> list[dict[str, object]]:
    if not source_model_path.exists():
        raise FileNotFoundError(f"Open-vocab source model does not exist: {source_model_path}")
    terms = normalize_vocabulary_terms(runtime_vocabulary)
    if not terms:
        raise ValueError("runtime_vocabulary must include at least one term.")
    formats = list(export_formats)
    if not formats:
        raise ValueError("At least one export format is required.")
    unsupported_formats = [
        export_format
        for export_format in formats
        if export_format not in _OPEN_VOCAB_EXPORT_METADATA
    ]
    if unsupported_formats:
        raise ValueError(f"Unsupported open-vocab export format(s): {unsupported_formats}")

    loader = yoloe_loader or _load_yoloe
    vocabulary_hash = hash_vocabulary(terms)
    source_sha256 = sha256_file(source_model_path)
    model = loader(str(source_model_path))
    model.set_classes(terms)

    payloads: list[dict[str, object]] = []
    for export_format in formats:
        yoloe_format = _YOLOE_EXPORT_FORMAT[export_format]
        started_at = time.perf_counter()
        export_result = _export_yoloe(model, yoloe_format, output_dir)
        build_duration_seconds = time.perf_counter() - started_at
        artifact_path = _coerce_export_path(export_result, yoloe_format)
        kind, runtime_backend = _OPEN_VOCAB_EXPORT_METADATA[export_format]
        payloads.append(
            {
                "camera_id": camera_id,
                "scope": "scene",
                "kind": kind,
                "capability": "open_vocab",
                "runtime_backend": runtime_backend,
                "path": str(artifact_path),
                "target_profile": target_profile,
                "precision": precision,
                "input_shape": dict(input_shape),
                "classes": list(terms),
                "vocabulary_hash": vocabulary_hash,
                "vocabulary_version": vocabulary_version,
                "source_model_sha256": source_sha256,
                "sha256": sha256_file(artifact_path),
                "size_bytes": file_size(artifact_path),
                "builder": {
                    "mode": "open_vocab_yoloe_export",
                    "source_pt": str(source_model_path),
                    "export_format": yoloe_format,
                    "vocabulary_hash": vocabulary_hash,
                    "output_dir": str(output_dir) if output_dir is not None else None,
                },
                "runtime_versions": runtime_versions or {},
                "build_duration_seconds": build_duration_seconds,
            }
        )
    return payloads


def _load_yoloe(source_model_path: str) -> Any:
    from ultralytics import YOLOE  # type: ignore[attr-defined]

    return YOLOE(source_model_path)


def _export_yoloe(model: Any, export_format: str, output_dir: Path | None) -> object:
    export = model.export
    if output_dir is None or not _callable_accepts_project(export):
        return export(format=export_format)
    output_dir.mkdir(parents=True, exist_ok=True)
    return export(format=export_format, project=str(output_dir))


def _callable_accepts_project(callable_obj: Callable[..., object]) -> bool:
    try:
        parameters = signature(callable_obj).parameters.values()
    except (TypeError, ValueError):
        return True
    return any(
        parameter.name == "project" or parameter.kind is Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _coerce_export_path(export_result: object, export_format: str) -> Path:
    if isinstance(export_result, Path):
        path = export_result
    elif isinstance(export_result, str):
        path = Path(export_result)
    else:
        raise RuntimeError(
            f"YOLOE {export_format} export did not return a filesystem path."
        )
    if not path.exists():
        raise FileNotFoundError(f"YOLOE export did not produce an artifact: {path}")
    return path
