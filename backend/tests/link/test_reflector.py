from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from argus.core.config import Settings
from argus.link.reflector import start_reflector, stop_reflector
from argus.link.udp_sequence import build_probe_packet, parse_probe_packet


def test_link_reflector_settings_default_to_disabled() -> None:
    settings = Settings(_env_file=None)

    assert settings.link_reflector_enabled is False
    assert settings.link_reflector_bind_address == "0.0.0.0"
    assert settings.link_reflector_public_address is None
    assert settings.link_reflector_port == 8622
    assert settings.link_reflector_key_id == "master-reflector-default"
    assert settings.link_reflector_secret is None
    assert settings.link_reflector_rate_limit_pps == 100
    assert settings.link_reflector_allowed_source_cidr_list == ()


def test_link_reflector_allowed_source_cidrs_accept_comma_separated_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS",
        "192.0.2.0/24, 198.51.100.0/24",
    )

    settings = Settings(_env_file=None)

    assert settings.link_reflector_allowed_source_cidr_list == (
        "192.0.2.0/24",
        "198.51.100.0/24",
    )


def test_link_reflector_allowed_source_cidrs_accept_json_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS",
        '["192.0.2.0/24", "198.51.100.0/24"]',
    )

    settings = Settings(_env_file=None)

    assert settings.link_reflector_allowed_source_cidr_list == (
        "192.0.2.0/24",
        "198.51.100.0/24",
    )


def test_link_reflector_allowed_source_cidrs_reject_malformed_json_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS", '["192.0.2.0/24"')

    with pytest.raises(ValueError, match="valid JSON array"):
        Settings(_env_file=None)


def test_link_reflector_allowed_source_cidrs_reject_invalid_cidr_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS", "not-a-cidr")

    with pytest.raises(ValueError, match="valid CIDR"):
        Settings(_env_file=None)


def test_master_deployment_manifests_include_disabled_reflector_configuration() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = (root / "../infra/install/compose/compose.master.yml").resolve()
    helm_values = (root / "../infra/helm/argus/values.yaml").resolve()
    helm_deployment = (
        root / "../infra/helm/argus/templates/deployment-central-backend.yaml"
    ).resolve()
    helm_service = (root / "../infra/helm/argus/templates/service-backend.yaml").resolve()

    compose_text = compose.read_text(encoding="utf-8")
    helm_values_text = helm_values.read_text(encoding="utf-8")
    helm_deployment_text = helm_deployment.read_text(encoding="utf-8")
    helm_service_text = helm_service.read_text(encoding="utf-8")

    assert "ARGUS_LINK_REFLECTOR_ENABLED" in compose_text
    assert "VEZOR_LINK_REFLECTOR_ENABLED:-false" in compose_text
    assert "target: ARGUS_LINK_REFLECTOR_SECRET" in compose_text
    assert "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS" in compose_text
    assert "8622/udp" in compose_text
    assert "reflector:" in helm_values_text
    assert "enabled: false" in helm_values_text
    assert "secretName:" in helm_values_text
    assert "ARGUS_LINK_REFLECTOR_SECRET" in helm_deployment_text
    assert "ARGUS_LINK_REFLECTOR_ALLOWED_SOURCE_CIDRS" in helm_deployment_text
    assert "ARGUS_LINK_REFLECTOR_ENABLED" in helm_deployment_text
    assert "fail \"central.backend.reflector.secretName is required" in helm_deployment_text
    assert "link-reflector" in helm_service_text


def test_link_reflector_settings_accept_secret() -> None:
    settings = Settings(
        _env_file=None,
        link_reflector_enabled=True,
        link_reflector_secret=SecretStr("test-secret"),
    )

    assert settings.link_reflector_enabled is True
    assert settings.link_reflector_secret is not None
    assert settings.link_reflector_secret.get_secret_value() == "test-secret"


@pytest.mark.asyncio
async def test_udp_reflector_replies_to_authenticated_request() -> None:
    secret = b"reflector-secret"
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=secret,
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        request = build_probe_packet(
            session_id=bytes.fromhex("44" * 16),
            sequence=17,
            transmit_ns=123_456,
            nonce=99,
            secret=secret,
            reply=False,
        )

        response = await _send_udp_packet(request, host="127.0.0.1", port=runtime.port)

        decoded = parse_probe_packet(response, secret=secret)
        assert decoded.reply is True
        assert decoded.session_id == bytes.fromhex("44" * 16)
        assert decoded.sequence == 17
        assert decoded.transmit_ns == 123_456
        assert decoded.nonce == 99
        assert len(response) <= len(request)
    finally:
        stop_reflector(runtime)


@pytest.mark.asyncio
async def test_udp_reflector_drops_unauthenticated_request() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
    )
    assert runtime is not None
    try:
        request = build_probe_packet(
            session_id=bytes.fromhex("55" * 16),
            sequence=3,
            transmit_ns=123_456,
            nonce=77,
            secret=b"wrong-secret",
            reply=False,
        )

        with pytest.raises(TimeoutError):
            await _send_udp_packet(
                request,
                host="127.0.0.1",
                port=runtime.port,
                wait_seconds=0.1,
            )
    finally:
        stop_reflector(runtime)


@pytest.mark.asyncio
async def test_udp_reflector_drops_disallowed_source_cidr() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
        allowed_source_cidrs=["192.0.2.0/24"],
    )
    assert runtime is not None
    try:
        request = build_probe_packet(
            session_id=bytes.fromhex("66" * 16),
            sequence=5,
            transmit_ns=123_456,
            nonce=88,
            secret=b"reflector-secret",
            reply=False,
        )

        with pytest.raises(TimeoutError):
            await _send_udp_packet(
                request,
                host="127.0.0.1",
                port=runtime.port,
                wait_seconds=0.1,
            )
    finally:
        stop_reflector(runtime)


@pytest.mark.asyncio
async def test_udp_reflector_disabled_profile_does_not_bind() -> None:
    runtime = await start_reflector(
        bind_host="127.0.0.1",
        port=0,
        secret=b"reflector-secret",
        key_id="master-reflector-test",
        enabled=False,
    )

    assert runtime is None


async def _send_udp_packet(
    payload: bytes,
    *,
    host: str,
    port: int,
    wait_seconds: float = 1.0,
) -> bytes:
    loop = asyncio.get_running_loop()
    response: asyncio.Future[bytes] = loop.create_future()

    class ClientProtocol(asyncio.DatagramProtocol):
        transport: asyncio.DatagramTransport

        def connection_made(self, transport: asyncio.BaseTransport) -> None:
            self.transport = transport  # type: ignore[assignment]
            self.transport.sendto(payload, (host, port))

        def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
            if not response.done():
                response.set_result(data)

        def error_received(self, exc: Exception) -> None:
            if not response.done():
                response.set_exception(exc)

    transport, _ = await loop.create_datagram_endpoint(
        ClientProtocol,
        local_addr=("127.0.0.1", 0),
    )
    try:
        return await asyncio.wait_for(response, timeout=wait_seconds)
    finally:
        transport.close()
