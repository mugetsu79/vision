from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from argus.core.config import Settings
from argus.services.identity_bootstrap import KeycloakBootstrapProvisioner


@pytest.mark.asyncio
async def test_keycloak_bootstrap_provisioner_creates_realm_client_and_admin_user() -> None:
    calls: list[tuple[str, str, dict[str, object] | str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body: dict[str, object] | str | None
        if request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content.decode("utf-8"))
        else:
            body = request.content.decode("utf-8") if request.content else None
        calls.append((request.method, request.url.path, body))

        if request.url.path == "/realms/master/protocol/openid-connect/token":
            assert "client_id=admin-cli" in str(body)
            return httpx.Response(200, json={"access_token": "admin-token"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor":
            return httpx.Response(404)
        if request.method == "POST" and request.url.path == "/admin/realms":
            return httpx.Response(201)
        if request.method == "GET" and request.url.path.startswith("/admin/realms/vezor/roles/"):
            role_name = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"id": f"role-{role_name}", "name": role_name})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/clients":
            if not any(
                method == "POST" and path == "/admin/realms/vezor/clients"
                for method, path, _body in calls
            ):
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[{"id": "client-uuid", "clientId": "argus-frontend"}],
            )
        if request.method == "POST" and request.url.path == "/admin/realms/vezor/clients":
            return httpx.Response(201)
        if request.method == "PUT" and request.url.path == (
            "/admin/realms/vezor/clients/client-uuid"
        ):
            return httpx.Response(204)
        if request.method == "GET" and request.url.path.endswith("/protocol-mappers/models"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path.endswith("/protocol-mappers/models"):
            return httpx.Response(201)
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/users":
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path == "/admin/realms/vezor/users":
            return httpx.Response(
                201,
                headers={"Location": "http://keycloak/admin/realms/vezor/users/kc-user-123"},
            )
        if request.method == "PUT" and request.url.path.endswith("/reset-password"):
            return httpx.Response(204)
        if request.method == "GET" and request.url.path.endswith("/role-mappings/realm"):
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path.endswith("/role-mappings/realm"):
            return httpx.Response(204)
        return httpx.Response(500, json={"unexpected": request.url.path})

    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_issuer="http://127.0.0.1:8080/realms/vezor",
        keycloak_admin_username="admin",
        keycloak_admin_password=SecretStr("admin-password"),
        keycloak_frontend_client_id="argus-frontend",
        keycloak_frontend_url="http://127.0.0.1:3000",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://keycloak:8080",
    ) as http_client:
        provisioner = KeycloakBootstrapProvisioner(settings, http_client=http_client)

        subject = await provisioner.provision_tenant_admin(
            tenant_id=UUID("00000000-0000-0000-0000-000000000921"),
            tenant_name="Vezor Pilot",
            tenant_slug="vezor-pilot",
            admin_email="admin@vezor.local",
            admin_password="first-run-password",
        )

    assert subject == "kc-user-123"
    user_create_body = next(
        body
        for method, path, body in calls
        if method == "POST" and path == "/admin/realms/vezor/users"
    )
    assert user_create_body == {
        "username": "admin@vezor.local",
        "email": "admin@vezor.local",
        "enabled": True,
        "emailVerified": True,
        "requiredActions": [],
        "attributes": {
            "tenant": ["vezor-pilot"],
            "tenant_id": ["00000000-0000-0000-0000-000000000921"],
        },
    }
    password_reset_body = next(
        body for method, path, body in calls if method == "PUT" and path.endswith("/reset-password")
    )
    assert password_reset_body == {
        "type": "password",
        "value": "first-run-password",
        "temporary": False,
    }
