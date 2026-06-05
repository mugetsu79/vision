from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PackStatus = Literal["planned_mvp", "designed_not_implemented", "active", "retired"]

RUNTIME_ENABLED_STATUSES: set[str] = {"planned_mvp", "active"}
DESIGNED_ONLY_STATUSES: set[str] = {"designed_not_implemented"}
DESIGNED_ONLY_INTEGRATION_STATUSES: set[str] = {"design_only", "research_only"}
KNOWN_CORE_EXTENSION_POINTS: set[str] = {
    "BillingNode",
    "Evidence",
    "EvidenceCollection",
    "EvidenceExport",
    "LinkContext",
    "LinkPassport",
    "PrivacyPolicy",
    "RoleLabel",
    "RotationGroup",
    "Scene",
    "SceneContract",
    "SceneZoneLabel",
    "Signal",
    "SignalContext",
    "SignalDimension",
    "Site",
    "SiteContext",
    "SiteGroup",
    "SiteSubdivision",
    "RuntimePassport",
}


class PackRegistryError(ValueError):
    """Raised when pack manifests cannot be loaded or validated."""


class PackMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=1)
    product_name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    status: PackStatus
    wedge: str = Field(min_length=1)
    sales_motion: str = Field(min_length=1)
    implementation_commitment: bool


class PackEngineRequirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_version: str = Field(min_length=1)
    required_capabilities: list[str] = Field(default_factory=list)

    @field_validator("required_capabilities")
    @classmethod
    def validate_capabilities(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "required_capabilities")


class PackEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    extends: str = Field(min_length=1)
    storage: Literal["pack"]
    purpose: str = Field(min_length=1)


class PackSceneTemplate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=1)
    outcome: str = Field(min_length=1)
    primitives: list[str] = Field(default_factory=list)

    @field_validator("primitives")
    @classmethod
    def validate_primitives(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "primitives")


class PackModelPreset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    status: str | None = None
    classes: list[str] = Field(default_factory=list)
    scenes: list[str] = Field(default_factory=list)
    max_terms: int | None = Field(default=None, gt=0)
    terms: list[str] = Field(default_factory=list)

    @field_validator("classes", "scenes", "terms")
    @classmethod
    def validate_string_lists(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "preset values")


class PackModelPresets(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fixed_vocab: list[PackModelPreset] = Field(default_factory=list)
    open_vocab: list[PackModelPreset] = Field(default_factory=list)


class PackIntegration(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    status: str = Field(min_length=1)
    protocol: str = Field(min_length=1)


class PackEvidenceContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(default_factory=list)

    @field_validator("fields")
    @classmethod
    def validate_fields(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "fields")


class PackBilling(BaseModel):
    model_config = ConfigDict(extra="allow")

    hierarchy_labels: list[str] = Field(default_factory=list)
    meters: list[str] = Field(default_factory=list)

    @field_validator("hierarchy_labels", "meters")
    @classmethod
    def validate_billing_lists(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "billing values")


class PackUiExtensions(BaseModel):
    model_config = ConfigDict(extra="allow")

    navigation_labels: dict[str, str] = Field(default_factory=dict)
    panels: list[str] = Field(default_factory=list)

    @field_validator("panels")
    @classmethod
    def validate_panels(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "panels")


class PackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_version: Literal["vezor.io/v1alpha1"]
    kind: Literal["Pack"]
    metadata: PackMetadata
    activation_conditions: list[str] = Field(default_factory=list)
    engine: PackEngineRequirements
    entities: list[PackEntity] = Field(default_factory=list)
    scene_templates: list[PackSceneTemplate] = Field(default_factory=list)
    model_presets: PackModelPresets
    integrations: list[PackIntegration] = Field(default_factory=list)
    privacy_defaults: dict[str, Any] = Field(default_factory=dict)
    evidence_context: PackEvidenceContext
    billing: PackBilling
    ui_extensions: PackUiExtensions
    allowed_core_dependencies: list[str] = Field(default_factory=list)
    forbidden_dependencies: list[str] = Field(default_factory=list)

    @property
    def is_runtime_enabled(self) -> bool:
        return self.metadata.status in RUNTIME_ENABLED_STATUSES

    @field_validator("activation_conditions", "allowed_core_dependencies", "forbidden_dependencies")
    @classmethod
    def validate_unique_strings(cls, value: list[str]) -> list[str]:
        return _unique_non_empty(value, "manifest values")

    @model_validator(mode="after")
    def validate_status_semantics(self) -> PackManifest:
        unknown_core_dependencies = sorted(
            set(self.allowed_core_dependencies) - KNOWN_CORE_EXTENSION_POINTS
        )
        if unknown_core_dependencies:
            joined = ", ".join(unknown_core_dependencies)
            raise PackRegistryError(f"unknown core extension points: {joined}")
        undeclared_entity_extensions = sorted(
            {entity.extends for entity in self.entities} - set(self.allowed_core_dependencies)
        )
        if undeclared_entity_extensions:
            joined = ", ".join(undeclared_entity_extensions)
            raise PackRegistryError(
                f"entity extends values must be declared core dependencies: {joined}"
            )
        if self.metadata.status in DESIGNED_ONLY_STATUSES:
            if self.metadata.implementation_commitment:
                raise PackRegistryError("designed-only packs cannot commit to implementation")
            if self.metadata.sales_motion != "none":
                raise PackRegistryError("designed-only packs must have sales_motion set to none")
            if not self.activation_conditions:
                raise PackRegistryError("designed-only packs must declare activation conditions")
            invalid_integrations = [
                integration.id
                for integration in self.integrations
                if integration.status not in DESIGNED_ONLY_INTEGRATION_STATUSES
            ]
            if invalid_integrations:
                joined = ", ".join(sorted(invalid_integrations))
                raise PackRegistryError(
                    f"designed-only integrations must be design_only or research_only: {joined}"
                )
        if self.metadata.status in RUNTIME_ENABLED_STATUSES and not (
            self.metadata.implementation_commitment
        ):
            raise PackRegistryError("runtime-enabled packs must commit to implementation")
        return self


class PackRegistry:
    def __init__(self, packs_root: Path | None = None) -> None:
        self.packs_root = packs_root or default_packs_root()
        self._manifests = tuple(load_pack_manifests(self.packs_root))
        self._by_id = {manifest.metadata.id: manifest for manifest in self._manifests}
        if len(self._by_id) != len(self._manifests):
            raise PackRegistryError("pack manifest ids must be unique")

    def list_packs(self) -> list[PackManifest]:
        return list(self._manifests)

    def list_runtime_enabled_packs(self) -> list[PackManifest]:
        return [manifest for manifest in self._manifests if manifest.is_runtime_enabled]

    def get_pack(self, pack_id: str) -> PackManifest:
        return self._by_id[pack_id]


def default_packs_root() -> Path:
    return Path(__file__).resolve().parents[4] / "packs"


def load_pack_manifests(packs_root: Path) -> list[PackManifest]:
    if not packs_root.exists():
        raise PackRegistryError(f"pack root does not exist: {packs_root}")
    manifest_paths = sorted(packs_root.glob("*/pack.yaml"))
    manifests = [load_pack_manifest(path) for path in manifest_paths]
    ids = [manifest.metadata.id for manifest in manifests]
    if len(ids) != len(set(ids)):
        raise PackRegistryError("pack manifest ids must be unique")
    return manifests


def load_pack_manifest(manifest_path: Path) -> PackManifest:
    try:
        raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PackRegistryError(f"could not read pack manifest: {manifest_path}") from exc
    except yaml.YAMLError as exc:
        raise PackRegistryError(f"could not parse pack manifest: {manifest_path}") from exc
    if not isinstance(raw, dict):
        raise PackRegistryError(f"pack manifest must be a mapping: {manifest_path}")
    try:
        return PackManifest.model_validate(raw)
    except ValueError as exc:
        raise PackRegistryError(f"invalid pack manifest {manifest_path}: {exc}") from exc


def _unique_non_empty(values: list[str], field_name: str) -> list[str]:
    normalized = [value.strip() for value in values]
    if any(not value for value in normalized):
        raise ValueError(f"{field_name} cannot contain empty strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} cannot contain duplicates")
    return normalized
