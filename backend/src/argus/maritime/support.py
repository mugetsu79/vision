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
        "label": "Support readiness",
        "groups": [
            {
                "id": "connectivity",
                "label": "Connectivity readiness",
                "status": "attention",
                "source": "core link",
                "checks": [
                    {
                        "key": "link_state",
                        "label": "Link state",
                        "status": "attention",
                        "source": "link passport",
                    },
                    {
                        "key": "active_connection",
                        "label": "Active connection",
                        "status": "ready",
                        "source": "core link connections",
                    },
                    {
                        "key": "queued_evidence",
                        "label": "Queued evidence work",
                        "status": "attention",
                        "source": "link queue",
                    },
                ],
                "next_action": "Review active connection and queued evidence work.",
            },
            {
                "id": "shipboard_network",
                "label": "Shipboard network readiness",
                "status": "ready",
                "source": "fleet runtime",
                "checks": [
                    {
                        "key": "master_readiness",
                        "label": "Master readiness",
                        "status": "ready",
                        "source": "fleet supervisor",
                    },
                    {
                        "key": "edge_pairing",
                        "label": "Edge pairing",
                        "status": "ready",
                        "source": "fleet nodes",
                    },
                    {
                        "key": "camera_reachability",
                        "label": "Camera reachability",
                        "status": "ready",
                        "source": "camera runtime",
                    },
                ],
                "next_action": "Confirm node and camera reachability before opening access.",
            },
            {
                "id": "evidence_path",
                "label": "Evidence path readiness",
                "status": "attention",
                "source": "evidence export",
                "checks": [
                    {
                        "key": "evidence_storage",
                        "label": "Evidence storage",
                        "status": "ready",
                        "source": "evidence service",
                    },
                    {
                        "key": "link_passport",
                        "label": "Link passport",
                        "status": "attention",
                        "source": "runtime passport",
                    },
                    {
                        "key": "export_context",
                        "label": "Export context",
                        "status": "ready",
                        "source": "maritime evidence context",
                    },
                ],
                "next_action": "Confirm evidence context and retry stalled transfer work.",
            },
            {
                "id": "access_and_roles",
                "label": "Access and roles readiness",
                "status": "ready",
                "source": "core support",
                "checks": [
                    {
                        "key": "identity",
                        "label": "Identity",
                        "status": "ready",
                        "source": "tenant identity",
                    },
                    {
                        "key": "billing_entitlement",
                        "label": "Billing entitlement",
                        "status": "ready",
                        "source": "core billing",
                    },
                    {
                        "key": "credential_boundary",
                        "label": "Credential boundary",
                        "status": "ready",
                        "source": "support tunnel",
                    },
                ],
                "next_action": "Confirm support contacts and credential references.",
            },
        ],
    }
