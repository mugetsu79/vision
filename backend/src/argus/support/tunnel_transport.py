from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer


class SupportTunnelRequest(BaseModel):
    tunnel_id: UUID
    node_id: UUID
    transport: Literal["ssh_reverse"]
    relay_host: str
    allowed_ports: list[int] = Field(default_factory=list)
    credential_ref: str
    expires_at: datetime
    private_key: None = None

    @field_serializer("tunnel_id", "node_id")
    def _serialize_uuid(self, value: UUID) -> str:
        return str(value)

    @field_serializer("expires_at")
    def _serialize_expires_at(self, value: datetime) -> str:
        return value.isoformat()


class SupportTunnelTransport(Protocol):
    def build_request(
        self,
        *,
        node_id: UUID,
        relay_host: str,
        allowed_ports: Sequence[int],
        credential_ref: str,
        expires_at: datetime,
        tunnel_id: UUID | None = None,
    ) -> SupportTunnelRequest: ...


class SshReverseTunnelTransport:
    transport = "ssh_reverse"

    def build_request(
        self,
        *,
        node_id: UUID,
        relay_host: str,
        allowed_ports: Sequence[int],
        credential_ref: str,
        expires_at: datetime,
        tunnel_id: UUID | None = None,
    ) -> SupportTunnelRequest:
        validate_support_tunnel_parameters(relay_host=relay_host, allowed_ports=allowed_ports)
        return SupportTunnelRequest(
            tunnel_id=tunnel_id or uuid4(),
            node_id=node_id,
            transport="ssh_reverse",
            relay_host=relay_host,
            allowed_ports=[int(port) for port in allowed_ports],
            credential_ref=credential_ref,
            expires_at=expires_at,
        )


def validate_support_tunnel_parameters(
    *,
    relay_host: str,
    allowed_ports: Sequence[int],
) -> None:
    if (
        not relay_host
        or relay_host.startswith("-")
        or any(char.isspace() or ord(char) < 32 for char in relay_host)
    ):
        raise ValueError("Unsafe support tunnel relay host.")
    for port in allowed_ports:
        if int(port) < 1 or int(port) > 65535:
            raise ValueError("Support tunnel allowed port must be between 1 and 65535.")
