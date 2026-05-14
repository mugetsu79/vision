from __future__ import annotations

import re
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReleaseChannel = Literal["dev", "pilot", "stable"]
PackageTargetName = Literal["linux-master", "macos-master", "jetson-edge"]
TargetOS = Literal["linux", "darwin"]
TargetRole = Literal["master", "edge"]

REQUIRED_TARGETS: frozenset[str] = frozenset(
    {"linux-master", "macos-master", "jetson-edge"}
)
_DIGEST_PATTERN = re.compile(r"@sha256:[0-9a-fA-F]{64}\b")


class ImageSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    reference: str = Field(min_length=1)

    @property
    def uses_digest(self) -> bool:
        return bool(_DIGEST_PATTERN.search(self.reference))

    @property
    def uses_latest_tag(self) -> bool:
        image_part = self.reference.split("@", 1)[0]
        return image_part.endswith(":latest")


class PackageTarget(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: PackageTargetName
    os: TargetOS
    role: TargetRole
    architectures: list[str] = Field(min_length=1)
    ports: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ports(self) -> Self:
        if len(set(self.ports)) != len(self.ports):
            raise ValueError("ports must be unique inside a package target")
        invalid_ports = [port for port in self.ports if port < 1 or port > 65535]
        if invalid_ports:
            raise ValueError("ports must be in the range 1-65535")
        return self


class MinimumVersions(BaseModel):
    model_config = ConfigDict(frozen=True)

    python: str
    container_engine: str
    compose: str
    jetpack: str | None = None


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    version: str = Field(min_length=1)
    release_channel: ReleaseChannel
    images: dict[str, ImageSpec] = Field(min_length=1)
    package_targets: list[PackageTarget] = Field(min_length=1)
    minimum_versions: MinimumVersions

    @model_validator(mode="after")
    def validate_product_manifest(self) -> Self:
        target_names = self.target_names
        missing = REQUIRED_TARGETS - target_names
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"missing required package targets: {names}")

        if self.release_channel != "dev":
            bad_refs = [
                name
                for name, image in sorted(self.images.items())
                if not image.uses_digest or image.uses_latest_tag
            ]
            if bad_refs:
                names = ", ".join(bad_refs)
                raise ValueError(
                    "non-dev release manifests must use immutable digest references "
                    f"without latest tags: {names}"
                )
        return self

    @property
    def target_names(self) -> set[str]:
        return {target.name for target in self.package_targets}

    @property
    def image_names(self) -> set[str]:
        return set(self.images)
