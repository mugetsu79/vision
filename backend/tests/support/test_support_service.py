from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from argus.support.service import SupportService
from argus.support.tunnel_transport import SshReverseTunnelTransport

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
SITE_ID = UUID("00000000-0000-4000-8000-000000000002")
NODE_ID = UUID("00000000-0000-4000-8000-000000000030")


@pytest.fixture
def support_service() -> SupportService:
    return SupportService()


def test_packless_support_bundle_redacts_secrets(support_service: SupportService) -> None:
    bundle = support_service.generate_bundle(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        diagnostics={
            "rtsp_url": "rtsp://user:password@camera.local/stream",
            "api_key": "secret-token",
        },
    )

    serialized = json.dumps(bundle.payload)

    assert "password" not in serialized
    assert "secret-token" not in serialized
    assert "rtsp://user:****@camera.local/stream" in serialized


def test_support_session_records_billable_duration(
    support_service: SupportService,
) -> None:
    session = support_service.create_session(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        operator_id="noc-1",
    )

    closed = support_service.close_session(
        session.id,
        ended_at=session.started_at + timedelta(minutes=90),
    )

    assert closed.billable_duration_minutes == 90
    assert closed.usage_meter_key == "support_session_hour"


def test_ssh_reverse_tunnel_transport_uses_node_local_credential_references() -> None:
    request = SshReverseTunnelTransport().build_request(
        node_id=NODE_ID,
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
        credential_ref="node-local:ssh/support-tunnel",
        expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    assert request.transport == "ssh_reverse"
    assert request.credential_ref == "node-local:ssh/support-tunnel"
    assert request.private_key is None
    assert "IdentityFile" not in json.dumps(request.model_dump())


def test_ssh_reverse_tunnel_transport_rejects_unsafe_parameters() -> None:
    transport = SshReverseTunnelTransport()

    with pytest.raises(ValueError, match="relay host"):
        transport.build_request(
            node_id=NODE_ID,
            relay_host="-oProxyCommand=bad",
            allowed_ports=[22],
            credential_ref="node-local:ssh/support-tunnel",
            expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        )

    with pytest.raises(ValueError, match="allowed port"):
        transport.build_request(
            node_id=NODE_ID,
            relay_host="noc-relay.mugetsu.tech",
            allowed_ports=[0],
            credential_ref="node-local:ssh/support-tunnel",
            expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
        )


def test_backend_does_not_invoke_ssh_directly(
    support_service: SupportService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invoked = False

    def fake_run(*args: object, **kwargs: object) -> None:
        nonlocal invoked
        invoked = True

    monkeypatch.setattr(subprocess, "run", fake_run)

    tunnel = support_service.request_tunnel(
        tenant_id=TENANT_ID,
        site_id=SITE_ID,
        node_id=NODE_ID,
        transport="ssh_reverse",
        credential_ref="node-local:ssh/support-tunnel",
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
    )

    assert tunnel.status == "requested"
    assert tunnel.dispatch_method in {"supervisor_poll", "nats_push"}
    assert invoked is False


def test_break_glass_records_reason_scope_actor_and_closure(
    support_service: SupportService,
) -> None:
    record = support_service.open_break_glass(
        reason="restore camera access",
        scope={"site_id": str(SITE_ID)},
        actor_id="captain",
        approver_id="fleet-admin",
    )

    closed = support_service.close_break_glass(
        record.id,
        closure_notes="rotated temporary credential",
    )

    assert closed.reason == "restore camera access"
    assert closed.ended_at is not None
    assert closed.closure_notes == "rotated temporary credential"


def test_onboarding_checks_cover_identity_master_edge_camera_model_link_evidence_billing_support(
    support_service: SupportService,
) -> None:
    run = support_service.run_onboarding_checks(tenant_id=TENANT_ID, site_id=SITE_ID)

    assert {check.key for check in run.checks} >= {
        "identity",
        "master_readiness",
        "edge_pairing",
        "camera_reachability",
        "model_runtime",
        "link_state",
        "evidence_storage",
        "billing_entitlement",
        "support_readiness",
    }
