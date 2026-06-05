from __future__ import annotations

from argus.maritime.contracts import JsonObject, MaritimeRuntimeContribution
from argus.services.pack_registry import PackManifest, PackRegistry

MARITIME_PACK_ID = "maritime-fleet"
MARITIME_REQUIRED_CORE_CAPABILITIES = [
    "argus.link",
    "argus.fleet",
    "argus.billing",
    "argus.support",
]


class MaritimeRuntimeService:
    def __init__(self, *, pack_registry: PackRegistry) -> None:
        self.pack_registry = pack_registry

    def runtime(self) -> MaritimeRuntimeContribution:
        manifest = self._manifest()
        if not manifest.is_runtime_enabled:
            raise ValueError("Maritime runtime pack is not enabled.")
        if not manifest.metadata.implementation_commitment:
            raise ValueError("Maritime runtime pack has no implementation commitment.")
        return MaritimeRuntimeContribution(
            pack_id=manifest.metadata.id,
            manifest_version=manifest.api_version,
            enabled=manifest.is_runtime_enabled,
            implementation_commitment=manifest.metadata.implementation_commitment,
            required_core_capabilities=list(MARITIME_REQUIRED_CORE_CAPABILITIES),
            engine_required_capabilities=list(manifest.engine.required_capabilities),
            scene_templates=[
                template.model_dump(mode="python") for template in manifest.scene_templates
            ],
            model_presets=manifest.model_presets.model_dump(mode="python"),
            evidence_fields=list(manifest.evidence_context.fields),
            integrations=[
                integration.model_dump(mode="python") for integration in manifest.integrations
            ],
            ui_labels=dict(manifest.ui_extensions.navigation_labels),
            ui_panels=list(manifest.ui_extensions.panels),
            billing_labels=list(manifest.billing.hierarchy_labels),
            billing_meters=list(manifest.billing.meters),
        )

    def runtime_payload(self) -> JsonObject:
        runtime = self.runtime()
        return {
            "pack_id": runtime.pack_id,
            "manifest_version": runtime.manifest_version,
            "enabled": runtime.enabled,
            "implementation_commitment": runtime.implementation_commitment,
            "required_core_capabilities": runtime.required_core_capabilities,
            "engine_required_capabilities": runtime.engine_required_capabilities,
            "scene_templates": runtime.scene_templates,
            "model_presets": runtime.model_presets,
            "evidence_fields": runtime.evidence_fields,
            "integrations": runtime.integrations,
            "ui_labels": runtime.ui_labels,
            "ui_panels": runtime.ui_panels,
            "billing_labels": runtime.billing_labels,
            "billing_meters": runtime.billing_meters,
        }

    def _manifest(self) -> PackManifest:
        try:
            manifest = self.pack_registry.get_pack(MARITIME_PACK_ID)
        except KeyError as exc:
            raise ValueError("Maritime runtime pack manifest not found.") from exc
        if manifest.metadata.id != MARITIME_PACK_ID:
            raise ValueError("Unexpected maritime runtime pack manifest.")
        return manifest
