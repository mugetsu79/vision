from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from argus.services.model_catalog import list_model_catalog_entries


def build_model_create_payload(
    *,
    catalog_id: str,
    artifact_path: Path,
    classes: list[str] | None,
) -> dict[str, Any]:
    entry = next(item for item in list_model_catalog_entries() if item.id == catalog_id)
    data = artifact_path.read_bytes()
    capability_config = entry.capability_config.model_dump(mode="json")
    capability_config["catalog_id"] = entry.id
    return {
        "name": entry.name,
        "version": entry.version,
        "task": entry.task.value,
        "path": str(artifact_path),
        "format": entry.format.value,
        "capability": entry.capability.value,
        "capability_config": capability_config,
        "classes": classes if classes is not None else list(entry.classes),
        "input_shape": entry.input_shape,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "license": entry.license,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-id", required=True)
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--class", dest="classes", action="append")
    parser.add_argument("--api-base-url")
    parser.add_argument("--bearer-token")
    args = parser.parse_args()
    payload = build_model_create_payload(
        catalog_id=args.catalog_id,
        artifact_path=Path(args.artifact_path),
        classes=args.classes,
    )
    if not args.api_base_url:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return

    import httpx

    response = httpx.post(
        f"{args.api_base_url.rstrip('/')}/api/v1/models",
        headers={"Authorization": f"Bearer {args.bearer_token}"},
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2, sort_keys=True))
