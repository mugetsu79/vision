from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from argus.scripts.build_runtime_artifact import sha256_file


def patch_json(
    url: str,
    token: str,
    payload: dict[str, object],
    *,
    client: Any | None = None,
) -> dict[str, object]:
    if client is None:
        import httpx

        client = httpx
    response = client.patch(
        url,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return dict(response.json())


def build_validation_patch(
    *,
    artifact_path: Path,
    expected_sha256: str,
    target_profile: str,
    host_profile: str | None = None,
    validation_duration_seconds: float | None = None,
) -> dict[str, object]:
    if host_profile is not None and host_profile != target_profile:
        return {
            "validation_status": "target_mismatch",
            "validation_error": (
                f"Host profile {host_profile!r} does not match target_profile {target_profile!r}."
            ),
            "validation_duration_seconds": validation_duration_seconds,
        }
    if not artifact_path.exists():
        return {
            "validation_status": "invalid",
            "validation_error": f"Artifact file does not exist: {artifact_path}",
            "validation_duration_seconds": validation_duration_seconds,
        }
    actual_sha256 = sha256_file(artifact_path)
    if actual_sha256 != expected_sha256:
        return {
            "validation_status": "invalid",
            "validation_error": (
                f"Artifact sha256 mismatch: expected {expected_sha256}, got {actual_sha256}."
            ),
            "sha256": actual_sha256,
            "validation_duration_seconds": validation_duration_seconds,
        }
    return {
        "validation_status": "valid",
        "validation_error": None,
        "sha256": actual_sha256,
        "size_bytes": artifact_path.stat().st_size,
        "validation_duration_seconds": validation_duration_seconds,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and patch a runtime artifact status.")
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--bearer-token", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--artifact-id", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--target-profile", required=True)
    parser.add_argument("--host-profile")
    args = parser.parse_args(argv)

    started_at = time.perf_counter()
    payload = build_validation_patch(
        artifact_path=Path(args.artifact_path),
        expected_sha256=args.expected_sha256,
        target_profile=args.target_profile,
        host_profile=args.host_profile,
        validation_duration_seconds=time.perf_counter() - started_at,
    )
    response = patch_json(
        (
            f"{args.api_base_url.rstrip('/')}/api/v1/models/"
            f"{args.model_id}/runtime-artifacts/{args.artifact_id}"
        ),
        args.bearer_token,
        payload,
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
