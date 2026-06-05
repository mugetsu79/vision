from __future__ import annotations

from dataclasses import dataclass, field

JsonObject = dict[str, object]


@dataclass(frozen=True, slots=True)
class MaritimeRuntimeContribution:
    pack_id: str
    manifest_version: str
    enabled: bool
    implementation_commitment: bool
    required_core_capabilities: list[str]
    engine_required_capabilities: list[str]
    scene_templates: list[JsonObject] = field(default_factory=list)
    model_presets: JsonObject = field(default_factory=dict)
    evidence_fields: list[str] = field(default_factory=list)
    integrations: list[JsonObject] = field(default_factory=list)
    ui_labels: dict[str, str] = field(default_factory=dict)
    ui_panels: list[str] = field(default_factory=list)
    billing_labels: list[str] = field(default_factory=list)
    billing_meters: list[str] = field(default_factory=list)
