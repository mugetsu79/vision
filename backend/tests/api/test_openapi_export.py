from __future__ import annotations

import json
from pathlib import Path

from argus.scripts.export_openapi_schema import export_openapi_schema


def test_openapi_export_writes_fleetops_schema(tmp_path: Path) -> None:
    output_path = tmp_path / "openapi.json"

    export_openapi_schema(output_path)

    schema = json.loads(output_path.read_text(encoding="utf-8"))
    paths = schema["paths"]
    assert "/api/v1/maritime/runtime" in paths
    assert "/api/v1/link/sites/{site_id}/status" in paths
    assert "/api/v1/fleet/exceptions" in paths
    assert "/api/v1/billing/invoice-runs" in paths
    assert "/api/v1/support/bundles" in paths

    assert _get_response_schema_ref(schema, "/api/v1/billing/invoice-runs").endswith(
        "/InvoiceRunListResponse"
    )
    assert _get_response_schema_ref(schema, "/api/v1/support/bundles").endswith(
        "/SupportBundleListResponse"
    )
    assert _get_response_schema_ref(
        schema, "/api/v1/maritime/vessels/{vessel_id}/link-status"
    ).endswith("/MaritimeVesselLinkStatusResponse")


def _get_response_schema_ref(schema: dict[str, object], path: str) -> str:
    paths = schema["paths"]
    assert isinstance(paths, dict)
    operation = paths[path]["get"]
    response = operation["responses"]["200"]
    return response["content"]["application/json"]["schema"]["$ref"]
