from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from argus.api.contracts import DeploymentModelInventoryItem
from argus.compat import UTC


class InventoryScanner:
    def __init__(
        self,
        *,
        reported_at: Callable[[], datetime] | None = None,
        target_profile: str | None = None,
        runtime_versions: Mapping[str, Any] | None = None,
    ) -> None:
        self.reported_at = reported_at or (lambda: datetime.now(tz=UTC))
        self.target_profile = target_profile
        self.runtime_versions = dict(runtime_versions or {})

    def scan_models(
        self,
        models: Iterable[Mapping[str, Any]],
    ) -> list[DeploymentModelInventoryItem]:
        return self.scan_assets(models, asset_kind="model")

    def scan_assets(
        self,
        assets: Iterable[Mapping[str, Any]],
        *,
        asset_kind: str,
    ) -> list[DeploymentModelInventoryItem]:
        items: list[DeploymentModelInventoryItem] = []
        for asset in assets:
            local_path = Path(asset["local_path"])
            if not local_path.exists() or not local_path.is_file():
                continue
            runtime_versions = asset.get("runtime_versions")
            target_profile = asset.get("target_profile", self.target_profile)
            items.append(
                DeploymentModelInventoryItem(
                    asset_kind=asset_kind,  # type: ignore[arg-type]
                    asset_id=_asset_id(asset["asset_id"]),
                    local_path=str(local_path),
                    sha256=_sha256_file(local_path),
                    size_bytes=local_path.stat().st_size,
                    target_profile=target_profile if isinstance(target_profile, str) else None,
                    runtime_versions=(
                        dict(runtime_versions)
                        if isinstance(runtime_versions, Mapping)
                        else dict(self.runtime_versions)
                    ),
                    reported_at=self.reported_at(),
                )
            )
        return items


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset_id(value: object) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))
