from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from argus.billing.contracts import JsonObject, UsageRecord

MARITIME_BILLING_LABELS: tuple[str, ...] = (
    "reseller",
    "fleet_manager",
    "owner",
    "charterer",
    "vessel",
)
MARITIME_CAPACITY_GUARDRAILS: tuple[str, ...] = (
    "camera_capacity_tier",
    "managed_edge_node",
    "retained_evidence_gb",
    "managed_link_gb",
)
MARITIME_BASE_COMMERCIAL_UNIT = "vessel_month"
MARITIME_VALUE_METERS: tuple[str, ...] = (
    "evidence_pack_export",
    "support_session_hour",
    "managed_link_gb",
    "fleet_runtime_health",
    "operational_incident_resolved",
)


def maritime_billing_meter_catalog() -> JsonObject:
    return {
        "capacity_guardrails": list(MARITIME_CAPACITY_GUARDRAILS),
        "base_commercial_unit": MARITIME_BASE_COMMERCIAL_UNIT,
        "value_meters": list(MARITIME_VALUE_METERS),
    }


def maritime_billing_rollups_payload(
    *,
    usage_records: Sequence[UsageRecord],
) -> JsonObject:
    return {
        "labels": list(MARITIME_BILLING_LABELS),
        "meters": maritime_billing_meter_catalog(),
        "usage_totals": _usage_totals(usage_records),
    }


def maritime_billing_usage_payload(records: Sequence[UsageRecord]) -> JsonObject:
    return {
        "items": [
            {
                "id": str(record.id),
                "meter_key": record.meter_key,
                "label": maritime_meter_label(record.meter_key),
                "quantity": format(record.quantity, "f"),
                "account_id": str(record.account_id) if record.account_id is not None else None,
                "node_id": str(record.node_id) if record.node_id is not None else None,
                "source_object_type": record.source_object_type,
                "source_object_id": str(record.source_object_id),
                "occurred_on": record.occurred_on.isoformat(),
                "pack_id": record.pack_id,
                "metadata": record.metadata,
            }
            for record in records
        ],
    }


def maritime_meter_label(meter_key: str) -> str:
    labels = {
        "vessel_month": "vessel month",
        "managed_edge_node": "managed edge node",
        "camera_capacity_tier": "camera capacity tier",
        "retained_evidence_gb": "retained evidence GB",
        "evidence_pack_export": "evidence pack export",
        "support_session_hour": "support session hour",
        "managed_link_gb": "managed link GB",
        "fleet_runtime_health": "fleet runtime health",
        "operational_incident_resolved": "operational incident resolved",
    }
    return labels.get(meter_key, meter_key.replace("_", " "))


def _usage_totals(records: Sequence[UsageRecord]) -> dict[str, str]:
    totals: dict[str, Decimal] = {}
    for record in records:
        totals[record.meter_key] = totals.get(record.meter_key, Decimal("0")) + record.quantity
    return {meter_key: format(quantity, "f") for meter_key, quantity in totals.items()}
