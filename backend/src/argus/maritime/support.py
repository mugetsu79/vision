from __future__ import annotations

from argus.maritime.contracts import JsonObject


def maritime_support_checklist_payload() -> JsonObject:
    return {
        "pack_id": "maritime-fleet",
        "sections": {
            "vessel_network": {
                "label": "Vessel network assumptions",
                "checks": [
                    "Confirm master and edge nodes are on the intended shipboard segment.",
                    "Record fallback path for local-only operation during link loss.",
                ],
            },
            "satellite_link": {
                "label": "Satellite-link notes",
                "checks": [
                    "Confirm low-bandwidth priority lanes are configured.",
                    "Record relay host and outage escalation contact.",
                ],
            },
            "eto_handoff": {
                "label": "ETO handoff",
                "checks": [
                    "Share node-local credential reference names.",
                    "Confirm break-glass closure and credential rotation procedure.",
                ],
            },
            "camera_naming": {
                "label": "Camera naming defaults",
                "checks": [
                    "Use stable location labels for decks, gangways, and loading spaces.",
                    "Keep source credentials in the local credential boundary.",
                ],
            },
            "shipboard_roles": {
                "label": "Shipboard support roles",
                "checks": ["Map captain, ETO, fleet admin, and NOC operator contacts."],
            },
        },
    }


def maritime_support_diagnostics_payload() -> JsonObject:
    return {
        "pack_id": "maritime-fleet",
        "groups": {
            "satellite_link": {
                "label": "Satellite link",
                "checks": ["link_state", "managed_link_gb", "last_successful_sync"],
            },
            "shipboard_network": {
                "label": "Shipboard network",
                "checks": ["master_readiness", "edge_pairing", "camera_reachability"],
            },
            "evidence_path": {
                "label": "Evidence path",
                "checks": ["evidence_storage", "link_state", "support_readiness"],
            },
            "support_roles": {
                "label": "Support roles",
                "checks": ["identity", "billing_entitlement", "support_readiness"],
            },
        },
    }
