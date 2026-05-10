from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Register a validated runtime artifact candidate.")
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--source-model", required=True)
    parser.add_argument("--prebuilt-engine", required=True)
    parser.add_argument("--target-profile", required=True)
    parser.add_argument("--class", dest="classes", action="append", required=True)
    parser.add_argument("--input-width", type=int, required=True)
    parser.add_argument("--input-height", type=int, required=True)
    args = parser.parse_args(argv)

    started_at = time.perf_counter()
    payload = build_fixed_vocab_artifact_payload(
        source_model_path=Path(args.source_model),
        prebuilt_engine_path=Path(args.prebuilt_engine),
        classes=args.classes,
        input_shape={"width": args.input_width, "height": args.input_height},
        target_profile=args.target_profile,
        build_duration_seconds=time.perf_counter() - started_at,
    )
    response = post_json(
        (
            f"{args.api_base_url.rstrip('/')}/api/v1/models/"
            f"{args.model_id}/runtime-artifacts"
        ),
        args.bearer_token,
        payload,
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
