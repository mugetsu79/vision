from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from argus.support.tunnel_transport import (
    SupportTunnelRequest,
    validate_support_tunnel_parameters,
)


class ProcessAdapter(Protocol):
    def run(self, command: list[str]) -> None: ...


class NodeCredentialStore:
    def __init__(self) -> None:
        self._private_key_paths: dict[str, str] = {}

    def put_reference(self, credential_ref: str, *, private_key_path: str) -> None:
        if not credential_ref.startswith("node-local:"):
            raise ValueError("Support tunnel credentials must use a node-local reference.")
        self._private_key_paths[credential_ref] = private_key_path

    def resolve_private_key_path(self, credential_ref: str) -> str:
        try:
            return self._private_key_paths[credential_ref]
        except KeyError as exc:
            raise KeyError(f"Node-local credential reference not found: {credential_ref}") from exc


class FakeProcessAdapter:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> None:
        self.commands.append(list(command))


@dataclass(frozen=True, slots=True)
class SupportTunnelResult:
    tunnel_id: UUID
    node_id: UUID
    status: str
    transport: str


class SupervisorSupportTunnelRunner:
    def __init__(
        self,
        *,
        credential_store: NodeCredentialStore,
        process_adapter: ProcessAdapter,
    ) -> None:
        self.credential_store = credential_store
        self.process_adapter = process_adapter

    def open(self, request: SupportTunnelRequest) -> SupportTunnelResult:
        if request.transport != "ssh_reverse":
            raise ValueError(f"Unsupported support tunnel transport: {request.transport}")
        validate_support_tunnel_parameters(
            relay_host=request.relay_host,
            allowed_ports=request.allowed_ports,
        )
        private_key_path = self.credential_store.resolve_private_key_path(request.credential_ref)
        self.process_adapter.run(_ssh_reverse_command(request, private_key_path=private_key_path))
        return SupportTunnelResult(
            tunnel_id=request.tunnel_id,
            node_id=request.node_id,
            status="active",
            transport=request.transport,
        )


def _ssh_reverse_command(
    request: SupportTunnelRequest,
    *,
    private_key_path: str,
) -> list[str]:
    command = ["ssh", "-N"]
    for port in request.allowed_ports:
        command.extend(["-R", f"{port}:localhost:{port}"])
    command.extend(
        [
            "-i",
            private_key_path,
            "-o",
            "ExitOnForwardFailure=yes",
            "--",
            request.relay_host,
        ]
    )
    return command
