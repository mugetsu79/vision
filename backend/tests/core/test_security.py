from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient, Request, Response
from jose import jwt

from argus.core.config import Settings
from argus.core.security import (
    AuthenticatedUser,
    EdgeKeyMiddleware,
    SecurityService,
    decrypt_rtsp_url,
    encrypt_rtsp_url,
    require,
)
from argus.models.enums import RoleEnum

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]


def _b64url_uint(value: int) -> str:
    byte_length = max(1, (value.bit_length() + 7) // 8)
    return base64.urlsafe_b64encode(value.to_bytes(byte_length, "big")).rstrip(b"=").decode("utf-8")


def _build_security_transport(
    jwks_by_issuer: dict[str, dict[str, object]],
    jwks_uri_by_issuer: dict[str, str] | None = None,
):
    jwks_uri_by_issuer = jwks_uri_by_issuer or {}

    async def handler(request: Request) -> Response:
        for issuer, jwks in jwks_by_issuer.items():
            discovery_url = f"{issuer}/.well-known/openid-configuration"
            jwks_url = f"{issuer}/protocol/openid-connect/certs"

            if str(request.url) == discovery_url:
                return Response(
                    200,
                    json={
                        "issuer": issuer,
                        "jwks_uri": jwks_uri_by_issuer.get(issuer, jwks_url),
                    },
                )

            if str(request.url) == jwks_url:
                return Response(200, json=jwks)

        return Response(404)

    return handler


def _build_token(
    *,
    private_key_pem: bytes,
    issuer: str,
    subject: str,
    email: str,
    roles: list[str],
) -> str:
    now = datetime.now(tz=UTC)
    claims = {
        "sub": subject,
        "email": email,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "realm_access": {"roles": roles},
    }
    return jwt.encode(
        claims,
        private_key_pem,
        algorithm="RS256",
        headers={"kid": "test-kid"},
    )


@pytest.mark.asyncio
async def test_tenant_and_platform_admin_tokens_authorize_routes() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    internal_tenant_issuer = "https://sso.internal.example.com/realms/tenant-a"
    internal_platform_issuer = "https://sso.internal.example.com/realms/platform-admin"
    public_tenant_issuer = "https://auth.example.com/realms/tenant-a"
    public_platform_issuer = "https://auth.example.com/realms/platform-admin"
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_uint(public_numbers.n),
                "e": _b64url_uint(public_numbers.e),
            }
        ]
    }

    settings = Settings(
        _env_file=None,
        keycloak_server_url="https://sso.internal.example.com",
        keycloak_public_server_url="https://auth.example.com",
        keycloak_platform_realm="platform-admin",
        rtsp_encryption_key="argus-dev-rtsp-key",
        edge_api_keys={"edge-secret": ("/api/v1/edge/*",)},
        enable_startup_services=False,
    )
    transport = _build_security_transport(
        {
            internal_tenant_issuer: jwks,
            internal_platform_issuer: jwks,
        }
    )
    security_service = SecurityService.from_settings(settings, transport=transport)

    app = FastAPI()
    app.state.security = security_service
    app.add_middleware(EdgeKeyMiddleware, security_service=security_service)

    @app.get("/protected")
    async def protected(current_user: ViewerUser) -> dict[str, object]:
        return {
            "sub": current_user.subject,
            "role": current_user.role.value,
            "realm": current_user.realm,
            "is_superadmin": current_user.is_superadmin,
        }

    @app.get("/admin-only")
    async def admin_only(current_user: AdminUser) -> dict[str, str]:
        return {"sub": current_user.subject, "role": current_user.role.value}

    @app.post("/api/v1/edge/ping")
    async def edge_ping() -> dict[str, str]:
        return {"status": "ok"}

    tenant_token = _build_token(
        private_key_pem=private_key_pem,
        issuer=public_tenant_issuer,
        subject="tenant-user",
        email="viewer@example.com",
        roles=["viewer"],
    )
    platform_token = _build_token(
        private_key_pem=private_key_pem,
        issuer=public_platform_issuer,
        subject="platform-user",
        email="superadmin@example.com",
        roles=["superadmin"],
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        tenant_response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {tenant_token}"},
        )
        admin_denied = await client.get(
            "/admin-only",
            headers={"Authorization": f"Bearer {tenant_token}"},
        )
        platform_response = await client.get(
            "/protected",
            headers={"Authorization": f"Bearer {platform_token}"},
        )
        edge_missing_key = await client.post("/api/v1/edge/ping")
        edge_with_key = await client.post(
            "/api/v1/edge/ping",
            headers={"X-Edge-Key": "edge-secret"},
        )

    assert tenant_response.status_code == 200
    assert tenant_response.json()["realm"] == "tenant-a"
    assert tenant_response.json()["is_superadmin"] is False
    assert admin_denied.status_code == 403
    assert platform_response.status_code == 200
    assert platform_response.json()["realm"] == "platform-admin"
    assert platform_response.json()["is_superadmin"] is True
    assert edge_missing_key.status_code == 401
    assert edge_with_key.status_code == 200

    await security_service.close()


@pytest.mark.asyncio
async def test_browser_facing_keycloak_jwks_uri_resolves_to_internal_realm_base() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    internal_issuer = "http://keycloak:8080/realms/argus-dev"
    public_issuer = "http://127.0.0.1:8080/realms/argus-dev"
    public_jwks_url = f"{public_issuer}/protocol/openid-connect/certs"
    internal_jwks_url = f"{internal_issuer}/protocol/openid-connect/certs"
    requested_urls: list[str] = []
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "kid": "test-kid",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_uint(public_numbers.n),
                "e": _b64url_uint(public_numbers.e),
            }
        ]
    }

    async def handler(request: Request) -> Response:
        requested_urls.append(str(request.url))
        if str(request.url) == f"{internal_issuer}/.well-known/openid-configuration":
            return Response(
                200,
                json={"issuer": public_issuer, "jwks_uri": public_jwks_url},
            )
        if str(request.url) == internal_jwks_url:
            return Response(200, json=jwks)
        if str(request.url) == public_jwks_url:
            return Response(502)
        return Response(404)

    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_public_server_url="http://127.0.0.1:8080",
        rtsp_encryption_key="argus-dev-rtsp-key",
        enable_startup_services=False,
    )
    security_service = SecurityService.from_settings(settings, transport=handler)
    token = _build_token(
        private_key_pem=private_key_pem,
        issuer=public_issuer,
        subject="installer-user",
        email="installer@example.com",
        roles=["admin"],
    )

    user = await security_service.validate_token(token)

    assert user.subject == "installer-user"
    assert internal_jwks_url in requested_urls
    assert public_jwks_url not in requested_urls

    await security_service.close()


def test_rtsp_urls_round_trip_through_aes_gcm() -> None:
    settings = Settings(_env_file=None, rtsp_encryption_key="argus-dev-rtsp-key")
    plaintext = "rtsp://camera.internal/live"

    ciphertext = encrypt_rtsp_url(plaintext, settings)

    assert decrypt_rtsp_url(ciphertext, settings) == plaintext

    tampered_ciphertext = f"{ciphertext[:-1]}A" if ciphertext[-1] != "A" else f"{ciphertext[:-1]}B"
    with pytest.raises(ValueError):
        decrypt_rtsp_url(tampered_ciphertext, settings)
