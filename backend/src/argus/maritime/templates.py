from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from argus.maritime.contracts import JsonObject
from argus.maritime.service import MARITIME_PACK_ID
from argus.services.pack_registry import PackRegistry

CORE_TEMPLATE_FIELDS = {
    "active_classes",
    "runtime_vocabulary",
    "detection_regions",
    "zones",
    "incident_rules",
    "evidence_recording_policy",
    "privacy_defaults",
}


class MaritimeTemplateError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MaritimeSceneTemplate:
    id: str
    name: str
    outcome: str
    primitives: list[str]
    execution_engine: str = "core_scene_contract"
    detector_override: str | None = None


class MaritimeTemplateService:
    def __init__(self, *, pack_registry: PackRegistry) -> None:
        self.pack_registry = pack_registry

    def list_templates(self) -> list[MaritimeSceneTemplate]:
        manifest = self.pack_registry.get_pack(MARITIME_PACK_ID)
        return [
            MaritimeSceneTemplate(
                id=template.id,
                name=template.name,
                outcome=template.outcome,
                primitives=list(template.primitives),
            )
            for template in manifest.scene_templates
        ]

    def get_template(self, template_id: str) -> MaritimeSceneTemplate:
        for template in self.list_templates():
            if template.id == template_id:
                return template
        raise MaritimeTemplateError("Maritime scene template not found.")

    def template_payload(self, template: MaritimeSceneTemplate) -> JsonObject:
        return {
            "id": template.id,
            "name": template.name,
            "outcome": template.outcome,
            "primitives": list(template.primitives),
            "execution_engine": template.execution_engine,
            "detector_override": template.detector_override,
        }

    def to_core_camera_payload(self, template: MaritimeSceneTemplate) -> JsonObject:
        try:
            payload = _TEMPLATE_CORE_PAYLOADS[template.id]
        except KeyError as exc:
            raise MaritimeTemplateError("Maritime scene template mapping not found.") from exc
        if set(payload) - CORE_TEMPLATE_FIELDS:
            raise MaritimeTemplateError("Maritime scene template contains non-core fields.")
        return _copy_json_object(payload)

    def to_camera_update_payload(self, template: MaritimeSceneTemplate) -> JsonObject:
        core_payload = self.to_core_camera_payload(template)
        update_payload: JsonObject = {}
        for key in ("active_classes", "runtime_vocabulary", "detection_regions", "zones"):
            if key in core_payload:
                update_payload[key] = core_payload[key]
        if "evidence_recording_policy" in core_payload:
            update_payload["recording_policy"] = core_payload["evidence_recording_policy"]
        if "privacy_defaults" in core_payload:
            update_payload["privacy"] = core_payload["privacy_defaults"]
        return update_payload

    def incident_rule_payloads(self, template: MaritimeSceneTemplate) -> list[JsonObject]:
        payload = self.to_core_camera_payload(template)
        rules = payload.get("incident_rules", [])
        if not isinstance(rules, list):
            raise MaritimeTemplateError("Maritime scene template incident_rules must be a list.")
        rule_payloads: list[JsonObject] = []
        for rule in rules:
            if not isinstance(rule, Mapping):
                raise MaritimeTemplateError(
                    "Maritime scene template incident_rules must contain objects."
                )
            rule_payloads.append(_copy_json_object(cast(Mapping[str, object], rule)))
        return rule_payloads


def _copy_json_object(value: Mapping[str, object]) -> JsonObject:
    return {
        str(key): _copy_json_value(item)
        for key, item in value.items()
    }


def _copy_json_value(value: object) -> object:
    if isinstance(value, dict):
        return _copy_json_object(cast(Mapping[str, object], value))
    if isinstance(value, list):
        return [_copy_json_value(item) for item in value]
    return value


_FULL_FRAME_REGION: JsonObject = {
    "id": "full-frame",
    "mode": "include",
    "polygon": [[0.0, 0.0], [1280.0, 0.0], [1280.0, 720.0], [0.0, 720.0]],
    "frame_size": {"width": 1280, "height": 720},
}
_PRIVACY_DEFAULTS: JsonObject = {
    "blur_faces": True,
    "blur_plates": True,
    "method": "gaussian",
    "strength": 7,
}
_EVENT_RECORDING: JsonObject = {
    "enabled": True,
    "mode": "event_clip",
    "pre_seconds": 4,
    "post_seconds": 8,
    "fps": 10,
    "max_duration_seconds": 15,
    "storage_profile": "central",
    "snapshot_enabled": True,
    "snapshot_offset_seconds": 0.0,
    "snapshot_quality": 85,
}

_TEMPLATE_CORE_PAYLOADS: dict[str, JsonObject] = {
    "gangway-access": {
        "active_classes": ["person"],
        "runtime_vocabulary": {
            "terms": ["person", "gangway", "boarding"],
            "source": "manual",
            "version": 1,
        },
        "detection_regions": [_FULL_FRAME_REGION],
        "zones": [
            {
                "id": "gangway-line",
                "type": "line",
                "class_names": ["person"],
                "points": [[320.0, 120.0], [320.0, 650.0]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ],
        "incident_rules": [
            {
                "name": "Gangway access",
                "incident_type": "gangway_access",
                "severity": "warning",
                "predicate": {
                    "class_names": ["person"],
                    "zone_ids": ["gangway-line"],
                    "min_confidence": 0.55,
                },
                "action": "record_clip",
                "cooldown_seconds": 30,
            }
        ],
        "evidence_recording_policy": _EVENT_RECORDING,
        "privacy_defaults": _PRIVACY_DEFAULTS,
    },
    "deck-presence": {
        "active_classes": ["person"],
        "runtime_vocabulary": {
            "terms": ["person", "deck", "restricted area"],
            "source": "manual",
            "version": 1,
        },
        "detection_regions": [_FULL_FRAME_REGION],
        "zones": [
            {
                "id": "deck-watch",
                "type": "polygon",
                "class_names": ["person"],
                "polygon": [[80.0, 140.0], [1180.0, 140.0], [1220.0, 680.0], [60.0, 680.0]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ],
        "incident_rules": [
            {
                "name": "Deck presence",
                "incident_type": "deck_presence",
                "severity": "warning",
                "predicate": {
                    "class_names": ["person"],
                    "zone_ids": ["deck-watch"],
                    "min_confidence": 0.55,
                },
                "action": "record_clip",
                "cooldown_seconds": 60,
            }
        ],
        "evidence_recording_policy": _EVENT_RECORDING,
        "privacy_defaults": _PRIVACY_DEFAULTS,
    },
    "engine-room-safety": {
        "active_classes": ["person"],
        "runtime_vocabulary": {
            "terms": ["person", "engine room", "machinery space"],
            "source": "manual",
            "version": 1,
        },
        "detection_regions": [_FULL_FRAME_REGION],
        "zones": [
            {
                "id": "machinery-restricted-zone",
                "type": "polygon",
                "class_names": ["person"],
                "polygon": [[160.0, 80.0], [1120.0, 80.0], [1120.0, 700.0], [160.0, 700.0]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ],
        "incident_rules": [
            {
                "name": "Engine room restricted presence",
                "incident_type": "engine_room_safety",
                "severity": "critical",
                "predicate": {
                    "class_names": ["person"],
                    "zone_ids": ["machinery-restricted-zone"],
                    "min_confidence": 0.6,
                },
                "action": "record_clip",
                "cooldown_seconds": 45,
            }
        ],
        "evidence_recording_policy": _EVENT_RECORDING,
        "privacy_defaults": _PRIVACY_DEFAULTS,
    },
    "cargo-work-area": {
        "active_classes": ["person", "truck"],
        "runtime_vocabulary": {
            "terms": ["person", "truck", "cargo", "work area"],
            "source": "manual",
            "version": 1,
        },
        "detection_regions": [_FULL_FRAME_REGION],
        "zones": [
            {
                "id": "cargo-zone",
                "type": "polygon",
                "class_names": ["person", "truck"],
                "polygon": [[40.0, 120.0], [1240.0, 120.0], [1240.0, 700.0], [40.0, 700.0]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ],
        "incident_rules": [
            {
                "name": "Cargo work area activity",
                "incident_type": "cargo_work_area",
                "severity": "warning",
                "predicate": {
                    "class_names": ["person", "truck"],
                    "zone_ids": ["cargo-zone"],
                    "min_confidence": 0.55,
                },
                "action": "record_clip",
                "cooldown_seconds": 60,
            }
        ],
        "evidence_recording_policy": _EVENT_RECORDING,
        "privacy_defaults": _PRIVACY_DEFAULTS,
    },
    "port-call-evidence": {
        "active_classes": ["person"],
        "runtime_vocabulary": {
            "terms": ["person", "port call", "evidence sync"],
            "source": "manual",
            "version": 1,
        },
        "detection_regions": [_FULL_FRAME_REGION],
        "zones": [
            {
                "id": "port-call-zone",
                "type": "polygon",
                "class_names": ["person"],
                "polygon": [[100.0, 100.0], [1180.0, 100.0], [1180.0, 680.0], [100.0, 680.0]],
                "frame_size": {"width": 1280, "height": 720},
            }
        ],
        "incident_rules": [
            {
                "name": "Port call evidence",
                "incident_type": "port_call_evidence",
                "severity": "warning",
                "predicate": {
                    "class_names": ["person"],
                    "zone_ids": ["port-call-zone"],
                    "min_confidence": 0.5,
                },
                "action": "record_clip",
                "cooldown_seconds": 90,
            }
        ],
        "evidence_recording_policy": _EVENT_RECORDING,
        "privacy_defaults": _PRIVACY_DEFAULTS,
    },
}
