from __future__ import annotations

import json
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr

from argus.core.config import Settings
from argus.models.enums import RoleEnum
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
            client_id = request.url.params.get("clientId")
            posted_client = next(
                (
                    body
                    for method, path, body in calls
                    if method == "POST"
                    and path == "/admin/realms/vezor/clients"
                    and isinstance(body, dict)
                    and body.get("clientId") == client_id
                ),
                None,
            )
            if posted_client is None:
                return httpx.Response(200, json=[])
            return httpx.Response(
                200,
                json=[
                    {
                        "id": f"{client_id}-uuid",
                        "clientId": client_id,
                    }
                ],
            )
        if request.method == "POST" and request.url.path == "/admin/realms/vezor/clients":
            return httpx.Response(201)
        if request.method == "PUT" and request.url.path.startswith(
            "/admin/realms/vezor/clients/"
        ):
            return httpx.Response(204)
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/users/profile":
            return httpx.Response(
                200,
                json={
                    "attributes": [
                        {
                            "name": "username",
                            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
                        }
                    ],
                    "groups": [{"name": "user-metadata"}],
                },
            )
        if request.method == "PUT" and request.url.path == "/admin/realms/vezor/users/profile":
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
            admin_first_name="Vezor",
            admin_last_name="Admin",
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
        "firstName": "Vezor",
        "lastName": "Admin",
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
    mapper_client_uuids = {
        path.split("/clients/", 1)[1].split("/", 1)[0]
        for method, path, _body in calls
        if method == "POST" and path.endswith("/protocol-mappers/models")
    }
    assert mapper_client_uuids == {"argus-frontend-uuid", "argus-cli-uuid"}
    profile_update_body = next(
        body
        for method, path, body in calls
        if method == "PUT" and path == "/admin/realms/vezor/users/profile"
    )
    assert isinstance(profile_update_body, dict)
    profile_attribute_names = [
        attribute.get("name")
        for attribute in profile_update_body["attributes"]
        if isinstance(attribute, dict)
    ]
    assert profile_attribute_names == ["username", "tenant", "tenant_id"]
    tenant_attributes = {
        attribute["name"]: attribute
        for attribute in profile_update_body["attributes"]
        if isinstance(attribute, dict) and attribute.get("name") in {"tenant", "tenant_id"}
    }
    assert tenant_attributes == {
        "tenant": {
            "name": "tenant",
            "displayName": "Tenant",
            "multivalued": False,
            "permissions": {"view": ["admin"], "edit": ["admin"]},
            "validations": {"length": {"max": 255}},
        },
        "tenant_id": {
            "name": "tenant_id",
            "displayName": "Tenant ID",
            "multivalued": False,
            "permissions": {"view": ["admin"], "edit": ["admin"]},
            "validations": {"length": {"max": 64}},
        },
    }


@pytest.mark.asyncio
async def test_keycloak_bootstrap_provisioner_creates_tenant_user_with_selected_role() -> None:
    calls: list[tuple[str, str, dict[str, object] | str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body: dict[str, object] | str | None
        if request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content.decode("utf-8"))
        else:
            body = request.content.decode("utf-8") if request.content else None
        calls.append((request.method, request.url.path, body))

        if request.url.path == "/realms/master/protocol/openid-connect/token":
            return httpx.Response(200, json={"access_token": "admin-token"})
        if request.method == "GET" and request.url.path.startswith("/admin/realms/vezor/roles/"):
            role_name = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"id": f"role-{role_name}", "name": role_name})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/users":
            return httpx.Response(200, json=[])
        if request.method == "POST" and request.url.path == "/admin/realms/vezor/users":
            return httpx.Response(
                201,
                headers={"Location": "http://keycloak/admin/realms/vezor/users/kc-operator-123"},
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
    )
    tenant_id = UUID("00000000-0000-0000-0000-000000000931")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://keycloak:8080",
    ) as http_client:
        provisioner = KeycloakBootstrapProvisioner(settings, http_client=http_client)

        subject = await provisioner.provision_tenant_user(
            tenant_id=tenant_id,
            tenant_slug="acme",
            email="ops@acme.example",
            temporary_password="change-me-now",
            first_name="Ops",
            last_name="Lead",
            role=RoleEnum.OPERATOR,
        )

    assert subject == "kc-operator-123"
    post_user_payload = next(
        body
        for method, path, body in calls
        if method == "POST" and path == "/admin/realms/vezor/users"
    )
    assert isinstance(post_user_payload, dict)
    assert post_user_payload["attributes"] == {
        "tenant": ["acme"],
        "tenant_id": [str(tenant_id)],
    }
    role_mapping_payload = next(
        body
        for method, path, body in calls
        if method == "POST" and path.endswith("/role-mappings/realm")
    )
    assert isinstance(role_mapping_payload, list)
    assert role_mapping_payload[0]["name"] == "operator"
    password_reset_payload = next(
        body for method, path, body in calls if method == "PUT" and path.endswith("/reset-password")
    )
    assert isinstance(password_reset_payload, dict)
    assert password_reset_payload["temporary"] is True


@pytest.mark.asyncio
async def test_keycloak_bootstrap_provisioner_updates_tenant_user_profile_role_and_password(
) -> None:
    calls: list[tuple[str, str, dict[str, object] | str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body: dict[str, object] | str | None
        if request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content.decode("utf-8"))
        else:
            body = request.content.decode("utf-8") if request.content else None
        calls.append((request.method, request.url.path, body))

        if request.url.path == "/realms/master/protocol/openid-connect/token":
            return httpx.Response(200, json={"access_token": "admin-token"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/users/kc-ops-1":
            return httpx.Response(
                200,
                json={
                    "id": "kc-ops-1",
                    "username": "ops@acme.example",
                    "email": "ops@acme.example",
                    "firstName": "Ops",
                    "lastName": "Lead",
                    "enabled": True,
                },
            )
        if request.method == "PUT" and request.url.path == "/admin/realms/vezor/users/kc-ops-1":
            return httpx.Response(204)
        if request.method == "GET" and request.url.path.startswith("/admin/realms/vezor/roles/"):
            role_name = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"id": f"role-{role_name}", "name": role_name})
        if request.method == "GET" and request.url.path.endswith("/role-mappings/realm"):
            return httpx.Response(
                200,
                json=[{"id": "role-operator", "name": "operator"}],
            )
        if request.method == "DELETE" and request.url.path.endswith("/role-mappings/realm"):
            return httpx.Response(204)
        if request.method == "POST" and request.url.path.endswith("/role-mappings/realm"):
            return httpx.Response(204)
        if request.method == "PUT" and request.url.path.endswith("/reset-password"):
            return httpx.Response(204)
        return httpx.Response(500, json={"unexpected": request.url.path})

    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_issuer="http://127.0.0.1:8080/realms/vezor",
        keycloak_admin_username="admin",
        keycloak_admin_password=SecretStr("admin-password"),
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://keycloak:8080",
    ) as http_client:
        provisioner = KeycloakBootstrapProvisioner(settings, http_client=http_client)

        await provisioner.update_tenant_user(
            user_id="kc-ops-1",
            first_name="Operations",
            last_name="Lead",
            enabled=False,
        )
        await provisioner.set_tenant_user_role(user_id="kc-ops-1", role=RoleEnum.ADMIN)
        await provisioner.reset_tenant_user_password(
            user_id="kc-ops-1",
            temporary_password="change-me-now",
        )

    profile_update_payload = next(
        body
        for method, path, body in calls
        if method == "PUT" and path == "/admin/realms/vezor/users/kc-ops-1"
    )
    assert isinstance(profile_update_payload, dict)
    assert profile_update_payload["firstName"] == "Operations"
    assert profile_update_payload["enabled"] is False
    deleted_role_payload = next(
        body
        for method, path, body in calls
        if method == "DELETE" and path.endswith("/role-mappings/realm")
    )
    assert deleted_role_payload == [{"id": "role-operator", "name": "operator"}]
    assigned_role_payload = next(
        body
        for method, path, body in calls
        if method == "POST" and path.endswith("/role-mappings/realm")
    )
    assert assigned_role_payload == [{"id": "role-admin", "name": "admin"}]
    reset_payload = next(
        body for method, path, body in calls if method == "PUT" and path.endswith("/reset-password")
    )
    assert isinstance(reset_payload, dict)
    assert reset_payload["temporary"] is True


@pytest.mark.asyncio
async def test_keycloak_bootstrap_provisioner_reconciles_existing_frontend_client_url() -> None:
    calls: list[tuple[str, str, dict[str, object] | str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body: dict[str, object] | str | None
        if request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content.decode("utf-8"))
        else:
            body = request.content.decode("utf-8") if request.content else None
        calls.append((request.method, request.url.path, body))

        if request.url.path == "/realms/master/protocol/openid-connect/token":
            return httpx.Response(200, json={"access_token": "admin-token"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor":
            return httpx.Response(200, json={"realm": "vezor"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/clients":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "client-uuid",
                        "clientId": "argus-frontend",
                        "redirectUris": ["http://localhost:3000/*"],
                        "webOrigins": ["http://localhost:3000"],
                    }
                ],
            )
        if request.method == "PUT" and request.url.path == (
            "/admin/realms/vezor/clients/client-uuid"
        ):
            return httpx.Response(204)
        return httpx.Response(500, json={"unexpected": request.url.path})

    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_issuer="http://192.168.8.199:8080/realms/vezor",
        keycloak_admin_username="admin",
        keycloak_admin_password=SecretStr("admin-password"),
        keycloak_frontend_client_id="argus-frontend",
        keycloak_frontend_url="http://192.168.8.199:3000",
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://keycloak:8080",
    ) as http_client:
        provisioner = KeycloakBootstrapProvisioner(settings, http_client=http_client)

        reconciled = await provisioner.reconcile_frontend_client()

    assert reconciled is True
    client_update_body = next(
        body
        for method, path, body in calls
        if method == "PUT" and path == "/admin/realms/vezor/clients/client-uuid"
    )
    assert isinstance(client_update_body, dict)
    assert "http://192.168.8.199:3000/*" in client_update_body["redirectUris"]
    assert "http://192.168.8.199:3000" in client_update_body["webOrigins"]


@pytest.mark.asyncio
async def test_keycloak_bootstrap_provisioner_removes_pkce_for_lan_http_compatibility() -> None:
    calls: list[tuple[str, str, dict[str, object] | str | None]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        body: dict[str, object] | str | None
        if request.headers.get("content-type", "").startswith("application/json"):
            body = json.loads(request.content.decode("utf-8"))
        else:
            body = request.content.decode("utf-8") if request.content else None
        calls.append((request.method, request.url.path, body))

        if request.url.path == "/realms/master/protocol/openid-connect/token":
            return httpx.Response(200, json={"access_token": "admin-token"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor":
            return httpx.Response(200, json={"realm": "vezor"})
        if request.method == "GET" and request.url.path == "/admin/realms/vezor/clients":
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "client-uuid",
                        "clientId": "argus-frontend",
                        "redirectUris": ["http://localhost:3000/*"],
                        "webOrigins": ["http://localhost:3000"],
                        "attributes": {
                            "pkce.code.challenge.method": "S256",
                            "client.session.idle.timeout": "300",
                        },
                    }
                ],
            )
        if request.method == "PUT" and request.url.path == (
            "/admin/realms/vezor/clients/client-uuid"
        ):
            return httpx.Response(204)
        return httpx.Response(500, json={"unexpected": request.url.path})

    settings = Settings(
        _env_file=None,
        keycloak_server_url="http://keycloak:8080",
        keycloak_issuer="http://192.168.8.199:8080/realms/vezor",
        keycloak_admin_username="admin",
        keycloak_admin_password=SecretStr("admin-password"),
        keycloak_frontend_client_id="argus-frontend",
        keycloak_frontend_url="http://192.168.8.199:3000",
        keycloak_frontend_disable_pkce=True,
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="http://keycloak:8080",
    ) as http_client:
        provisioner = KeycloakBootstrapProvisioner(settings, http_client=http_client)

        reconciled = await provisioner.reconcile_frontend_client()

    assert reconciled is True
    client_update_body = next(
        body
        for method, path, body in calls
        if method == "PUT" and path == "/admin/realms/vezor/clients/client-uuid"
    )
    assert isinstance(client_update_body, dict)
    assert client_update_body["attributes"] == {
        "client.session.idle.timeout": "300",
        "pkce.code.challenge.method": "",
    }
