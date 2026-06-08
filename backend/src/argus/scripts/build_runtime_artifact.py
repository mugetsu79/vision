from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from argus.vision.runtime_artifact_builder import (
    build_fixed_vocab_artifact_payload,
    build_open_vocab_scene_artifact_payloads,
    file_size,
    sha256_file,
)

__all__ = [
    "build_fixed_vocab_artifact_payload",
    "build_open_vocab_scene_artifact_payloads",
    "file_size",
    "post_json",
    "sha256_file",
]

_OPEN_VOCAB_EXPORT_METADATA = {
    "onnx": ("onnx_export", "onnxruntime"),
    "engine": ("tensorrt_engine", "tensorrt_engine"),
}


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
