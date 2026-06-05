from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from argus.supervisor.support_tunnel import (
    FakeProcessAdapter,
    NodeCredentialStore,
    SupervisorSupportTunnelRunner,
)
from argus.support.tunnel_transport import SupportTunnelRequest

NODE_ID = UUID("00000000-0000-4000-8000-000000000030")


@pytest.fixture
def credential_store() -> NodeCredentialStore:
    return NodeCredentialStore()


@pytest.fixture
def process_adapter() -> FakeProcessAdapter:
    return FakeProcessAdapter()


def test_supervisor_resolves_node_local_credential_and_invokes_ssh_reverse_transport(
    credential_store: NodeCredentialStore,
    process_adapter: FakeProcessAdapter,
) -> None:
    credential_store.put_reference(
        "node-local:ssh/support-tunnel",
        private_key_path="/var/lib/vezor/ssh/support_tunnel",
    )
    request = SupportTunnelRequest(
        tunnel_id=UUID("00000000-0000-4000-8000-000000000031"),
        node_id=NODE_ID,
        transport="ssh_reverse",
        relay_host="noc-relay.mugetsu.tech",
        allowed_ports=[22, 8000],
        credential_ref="node-local:ssh/support-tunnel",
        expires_at=datetime(2026, 6, 5, 12, 0, tzinfo=UTC),
    )

    result = SupervisorSupportTunnelRunner(
        credential_store=credential_store,
        process_adapter=process_adapter,
    ).open(request)

    assert result.status == "active"
    assert process_adapter.commands[0][:3] == ["ssh", "-N", "-R"]
    assert "/var/lib/vezor/ssh/support_tunnel" in process_adapter.commands[0]
    assert "PRIVATE KEY" not in " ".join(process_adapter.commands[0])
