from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

from argus.vision.vocabulary import hash_vocabulary, normalize_vocabulary_terms

_OPEN_VOCAB_EXPORT_METADATA = {
    "onnx": ("onnx_export", "onnxruntime"),
    "engine": ("tensorrt_engine", "tensorrt_engine"),
}


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_size(path: Path) -> int:
    return path.stat().st_size


def post_json(
    url: str,
    token: str,
    payload: dict[str, object],
    *,
    client: Any | None = None,
) -> dict[str, object]:
    if client is None:
        import httpx

        client = httpx
    response = client.post(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return dict(response.json())


def build_fixed_vocab_artifact_payload(
    *,
    source_model_path: Path,
    prebuilt_engine_path: Path,
    classes: list[str],
    input_shape: dict[str, int],
    target_profile: str,
    build_duration_seconds: float | None = None,
) -> dict[str, object]:
    if not source_model_path.exists():
        raise FileNotFoundError(f"Source model does not exist: {source_model_path}")
    if not prebuilt_engine_path.exists():
        raise FileNotFoundError(f"Prebuilt engine does not exist: {prebuilt_engine_path}")
    return {
        "scope": "model",
        "kind": "tensorrt_engine",
        "capability": "fixed_vocab",
        "runtime_backend": "tensorrt_engine",
        "path": str(prebuilt_engine_path),
        "target_profile": target_profile,
        "precision": "fp16",
        "input_shape": dict(input_shape),
        "classes": list(classes),
        "source_model_sha256": sha256_file(source_model_path),
        "sha256": sha256_file(prebuilt_engine_path),
        "size_bytes": file_size(prebuilt_engine_path),
        "builder": {"mode": "prebuilt_engine"},
        "runtime_versions": {},
        "build_duration_seconds": build_duration_seconds,
    }


def build_open_vocab_scene_artifact_payloads(
    *,
    source_model_path: Path,
    camera_id: str,
    runtime_vocabulary: Iterable[object],
    export_formats: Sequence[str],
    input_shape: dict[str, int],
    target_profile: str,
    vocabulary_version: int | None = None,
    yoloe_loader: Callable[[str], Any] | None = None,
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
        started_at = time.perf_counter()
        export_result = model.export(format=export_format)
        build_duration_seconds = time.perf_counter() - started_at
        artifact_path = _coerce_export_path(export_result, export_format)
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
                "precision": "fp16",
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
                    "export_format": export_format,
                    "vocabulary_hash": vocabulary_hash,
                },
                "runtime_versions": {},
                "build_duration_seconds": build_duration_seconds,
            }
        )
    return payloads


def _load_yoloe(source_model_path: str) -> Any:
    from ultralytics import YOLOE

    return YOLOE(source_model_path)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register a validated runtime artifact candidate.")
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--source-model")
    parser.add_argument("--prebuilt-engine")
    parser.add_argument("--target-profile", required=True)
    parser.add_argument("--class", dest="classes", action="append")
    parser.add_argument("--input-width", type=int, required=True)
    parser.add_argument("--input-height", type=int, required=True)
    parser.add_argument("--camera-id")
    parser.add_argument("--runtime-vocabulary")
    parser.add_argument("--vocabulary-version", type=int)
    parser.add_argument("--open-vocab-source-pt")
    parser.add_argument(
        "--export-format",
        dest="export_formats",
        action="append",
        choices=sorted(_OPEN_VOCAB_EXPORT_METADATA),
    )
    args = parser.parse_args(argv)

    started_at = time.perf_counter()
    if args.open_vocab_source_pt:
        if not args.camera_id:
            parser.error("--camera-id is required with --open-vocab-source-pt")
        if not args.runtime_vocabulary:
            parser.error("--runtime-vocabulary is required with --open-vocab-source-pt")
        if not args.export_formats:
            parser.error("--export-format is required with --open-vocab-source-pt")
        payloads = build_open_vocab_scene_artifact_payloads(
            source_model_path=Path(args.open_vocab_source_pt),
            camera_id=args.camera_id,
            runtime_vocabulary=args.runtime_vocabulary.split(","),
            export_formats=args.export_formats,
            input_shape={"width": args.input_width, "height": args.input_height},
            target_profile=args.target_profile,
            vocabulary_version=args.vocabulary_version,
        )
    else:
        if not args.source_model:
            parser.error("--source-model is required without --open-vocab-source-pt")
        if not args.prebuilt_engine:
            parser.error("--prebuilt-engine is required without --open-vocab-source-pt")
        if not args.classes:
            parser.error("--class is required without --open-vocab-source-pt")
        payloads = [
            build_fixed_vocab_artifact_payload(
                source_model_path=Path(args.source_model),
                prebuilt_engine_path=Path(args.prebuilt_engine),
                classes=args.classes,
                input_shape={"width": args.input_width, "height": args.input_height},
                target_profile=args.target_profile,
                build_duration_seconds=time.perf_counter() - started_at,
            )
        ]
    url = (
        f"{args.api_base_url.rstrip('/')}/api/v1/models/"
        f"{args.model_id}/runtime-artifacts"
    )
    responses = [
        post_json(
            url,
            args.bearer_token,
            payload,
        )
        for payload in payloads
    ]
    print(json.dumps(responses[0] if len(responses) == 1 else responses, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
