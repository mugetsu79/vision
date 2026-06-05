from __future__ import annotations

from pathlib import Path

import pytest

from argus.services.pack_registry import (
    PackRegistry,
    PackRegistryError,
    default_packs_root,
    load_pack_manifest,
    load_pack_manifests,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKS_ROOT = REPO_ROOT / "packs"


def test_default_packs_root_points_to_repo_packs_directory() -> None:
    assert default_packs_root() == PACKS_ROOT


def test_load_pack_manifests_returns_expected_repo_packs() -> None:
    manifests = load_pack_manifests(PACKS_ROOT)

    ids = {manifest.metadata.id for manifest in manifests}

    assert ids == {"maritime-fleet", "traffic-public-space"}


def test_manifest_entities_extend_declared_core_dependencies() -> None:
    manifests = load_pack_manifests(PACKS_ROOT)

    for manifest in manifests:
        allowed = set(manifest.allowed_core_dependencies)
        entity_extensions = {entity.extends for entity in manifest.entities}
        assert entity_extensions <= allowed


def test_maritime_pack_is_planned_mvp() -> None:
    manifest = load_pack_manifest(PACKS_ROOT / "maritime-fleet" / "pack.yaml")

    assert manifest.metadata.id == "maritime-fleet"
    assert manifest.metadata.status == "planned_mvp"
    assert manifest.metadata.implementation_commitment is True
    assert manifest.is_runtime_enabled is True
    assert {entity.name for entity in manifest.entities} >= {"Vessel", "Voyage", "PortCall"}


def test_traffic_pack_is_designed_not_implemented() -> None:
    manifest = load_pack_manifest(PACKS_ROOT / "traffic-public-space" / "pack.yaml")

    assert manifest.metadata.id == "traffic-public-space"
    assert manifest.metadata.status == "designed_not_implemented"
    assert manifest.metadata.implementation_commitment is False
    assert manifest.metadata.sales_motion == "none"
    assert manifest.is_runtime_enabled is False
    assert manifest.activation_conditions
    assert {entity.name for entity in manifest.entities} >= {
        "Intersection",
        "CurbZone",
        "TrafficStudy",
    }


def test_designed_only_pack_cannot_claim_implemented_integrations(tmp_path: Path) -> None:
    manifest_path = tmp_path / "pack.yaml"
    manifest_path.write_text(
        """
api_version: vezor.io/v1alpha1
kind: Pack
metadata:
  id: invalid-designed-pack
  name: Invalid Designed Pack
  product_name: Invalid Pack
  owner: product
  status: designed_not_implemented
  wedge: invalid
  sales_motion: none
  implementation_commitment: false
activation_conditions:
  - activation requires a dated decision
engine:
  min_version: 0.1.0
  required_capabilities: [scenes, pack_registry]
entities: []
scene_templates: []
model_presets:
  fixed_vocab: []
  open_vocab: []
integrations:
  - id: invalid-live-adapter
    status: planned_mvp
    protocol: API
evidence_context:
  fields: []
billing:
  status: design_artifact_only
  meters: []
ui_extensions:
  status: design_artifact_only
  panels: []
allowed_core_dependencies: [Scene]
forbidden_dependencies: [invalid_dependency]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PackRegistryError, match="designed-only integrations"):
        load_pack_manifest(manifest_path)


def test_entity_extends_must_be_declared_core_dependency(tmp_path: Path) -> None:
    manifest_path = tmp_path / "pack.yaml"
    manifest_path.write_text(
        """
api_version: vezor.io/v1alpha1
kind: Pack
metadata:
  id: invalid-extension-pack
  name: Invalid Extension Pack
  product_name: Invalid Pack
  owner: product
  status: planned_mvp
  wedge: invalid
  sales_motion: test
  implementation_commitment: true
engine:
  min_version: 0.1.0
  required_capabilities: [scenes, pack_registry]
entities:
  - name: InvalidEntity
    extends: Vessel
    storage: pack
    purpose: should not extend a vertical noun
scene_templates: []
model_presets:
  fixed_vocab: []
  open_vocab: []
integrations: []
evidence_context:
  fields: []
billing:
  meters: []
ui_extensions:
  panels: []
allowed_core_dependencies: [Scene]
forbidden_dependencies: [invalid_dependency]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(PackRegistryError, match="entity extends values"):
        load_pack_manifest(manifest_path)


def test_registry_get_pack_returns_by_id_and_raises_for_unknown_pack() -> None:
    registry = PackRegistry(PACKS_ROOT)

    assert registry.get_pack("maritime-fleet").metadata.name == "Maritime Fleet Pack"

    with pytest.raises(KeyError):
        registry.get_pack("missing-pack")


def test_registry_lists_runtime_enabled_packs() -> None:
    registry = PackRegistry(PACKS_ROOT)

    runtime_ids = {manifest.metadata.id for manifest in registry.list_runtime_enabled_packs()}

    assert runtime_ids == {"maritime-fleet"}
