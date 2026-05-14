from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx

from argus.core.config import Settings
from argus.models.enums import RoleEnum


class KeycloakBootstrapError(RuntimeError):
    """Raised when first-run identity provisioning cannot complete."""


class KeycloakBootstrapProvisioner:
    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not settings.keycloak_admin_username:
            raise ValueError("Keycloak admin username is required.")
        if settings.keycloak_admin_password is None:
            raise ValueError("Keycloak admin password is required.")

        self.settings = settings
        self.http_client = http_client or httpx.AsyncClient(timeout=10.0)
        self.owns_http_client = http_client is None
        self.base_url = settings.keycloak_server_url.rstrip("/")
        self.realm = settings.keycloak_bootstrap_realm
        self.admin_username = settings.keycloak_admin_username
        self.admin_password = settings.keycloak_admin_password.get_secret_value()

    async def close(self) -> None:
        if self.owns_http_client:
            await self.http_client.aclose()

    async def provision_tenant_admin(
        self,
        *,
        tenant_id: UUID,
        tenant_name: str,
        tenant_slug: str,
        admin_email: str,
        admin_password: str,
    ) -> str:
        token = await self._admin_token()
        await self._ensure_realm(token, tenant_name=tenant_name)
        for role in (RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN):
            await self._ensure_realm_role(token, role.value)
        client_id = await self._ensure_frontend_client(token)
        await self._ensure_user_attribute_mapper(token, client_id, "tenant_id")
        await self._ensure_user_attribute_mapper(token, client_id, "tenant")
        user_id = await self._ensure_admin_user(
            token,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            admin_email=admin_email,
            admin_password=admin_password,
        )
        await self._ensure_realm_role_assignment(token, user_id, RoleEnum.ADMIN.value)
        return user_id

    async def _admin_token(self) -> str:
        response = await self.http_client.post(
            f"{self.base_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": self.admin_username,
                "password": self.admin_password,
            },
        )
        self._raise_for_status(response, "request Keycloak admin token")
        token = response.json().get("access_token")
        if not isinstance(token, str) or not token:
            raise KeycloakBootstrapError("Keycloak admin token response was missing access_token.")
        return token

    async def _ensure_realm(self, token: str, *, tenant_name: str) -> None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}",
            headers=self._headers(token),
        )
        if response.status_code == 200:
            return
        if response.status_code != 404:
            self._raise_for_status(response, f"read Keycloak realm {self.realm}")

        create = await self.http_client.post(
            f"{self.base_url}/admin/realms",
            headers=self._headers(token),
            json={
                "realm": self.realm,
                "enabled": True,
                "displayName": self.settings.app_name,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "roles": {
                    "realm": [
                        {"name": RoleEnum.VIEWER.value},
                        {"name": RoleEnum.OPERATOR.value},
                        {"name": RoleEnum.ADMIN.value},
                    ]
                },
                "attributes": {"tenant_name": tenant_name},
            },
        )
        self._raise_for_status(create, f"create Keycloak realm {self.realm}")

    async def _ensure_realm_role(self, token: str, role_name: str) -> dict[str, Any]:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/roles/{role_name}",
            headers=self._headers(token),
        )
        if response.status_code == 404:
            create = await self.http_client.post(
                f"{self.base_url}/admin/realms/{self.realm}/roles",
                headers=self._headers(token),
                json={"name": role_name},
            )
            self._raise_for_status(create, f"create Keycloak role {role_name}")
            response = await self.http_client.get(
                f"{self.base_url}/admin/realms/{self.realm}/roles/{role_name}",
                headers=self._headers(token),
            )
        self._raise_for_status(response, f"read Keycloak role {role_name}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise KeycloakBootstrapError(f"Keycloak role {role_name} response was invalid.")
        return dict(payload)

    async def _ensure_frontend_client(self, token: str) -> str:
        client = await self._find_client(token)
        if client is None:
            response = await self.http_client.post(
                f"{self.base_url}/admin/realms/{self.realm}/clients",
                headers=self._headers(token),
                json=self._frontend_client_payload(),
            )
            self._raise_for_status(
                response,
                f"create Keycloak client {self.settings.keycloak_frontend_client_id}",
            )
            client = await self._find_client(token)
        if client is None or not isinstance(client.get("id"), str):
            raise KeycloakBootstrapError(
                f"Unable to resolve Keycloak client {self.settings.keycloak_frontend_client_id}."
            )

        client_id = str(client["id"])
        merged = {**client, **self._frontend_client_payload()}
        response = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/clients/{client_id}",
            headers=self._headers(token),
            json=merged,
        )
        self._raise_for_status(
            response,
            f"update Keycloak client {self.settings.keycloak_frontend_client_id}",
        )
        return client_id

    async def _find_client(self, token: str) -> dict[str, Any] | None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/clients",
            headers=self._headers(token),
            params={"clientId": self.settings.keycloak_frontend_client_id},
        )
        self._raise_for_status(
            response,
            f"find Keycloak client {self.settings.keycloak_frontend_client_id}",
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise KeycloakBootstrapError("Keycloak client lookup response was invalid.")
        first = next((item for item in payload if isinstance(item, dict)), None)
        return dict(first) if first is not None else None

    async def _ensure_user_attribute_mapper(
        self,
        token: str,
        client_uuid: str,
        attribute_name: str,
    ) -> None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/clients/"
            f"{client_uuid}/protocol-mappers/models",
            headers=self._headers(token),
        )
        self._raise_for_status(response, "read Keycloak protocol mappers")
        mappers = response.json()
        if isinstance(mappers, list) and any(
            isinstance(mapper, dict) and mapper.get("name") == attribute_name for mapper in mappers
        ):
            return

        create = await self.http_client.post(
            f"{self.base_url}/admin/realms/{self.realm}/clients/"
            f"{client_uuid}/protocol-mappers/models",
            headers=self._headers(token),
            json={
                "name": attribute_name,
                "protocol": "openid-connect",
                "protocolMapper": "oidc-usermodel-attribute-mapper",
                "consentRequired": False,
                "config": {
                    "user.attribute": attribute_name,
                    "claim.name": attribute_name,
                    "jsonType.label": "String",
                    "id.token.claim": "true",
                    "access.token.claim": "true",
                    "userinfo.token.claim": "true",
                },
            },
        )
        self._raise_for_status(create, f"create Keycloak mapper {attribute_name}")

    async def _ensure_admin_user(
        self,
        token: str,
        *,
        tenant_id: UUID,
        tenant_slug: str,
        admin_email: str,
        admin_password: str,
    ) -> str:
        user = await self._find_user(token, admin_email)
        user_payload = {
            "username": admin_email,
            "email": admin_email,
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
            "attributes": {
                "tenant": [tenant_slug],
                "tenant_id": [str(tenant_id)],
            },
        }
        if user is None:
            response = await self.http_client.post(
                f"{self.base_url}/admin/realms/{self.realm}/users",
                headers=self._headers(token),
                json=user_payload,
            )
            self._raise_for_status(response, f"create Keycloak user {admin_email}")
            user_id = _user_id_from_location(response.headers.get("Location"))
            if user_id is None:
                user = await self._find_user(token, admin_email)
                user_id = str(user["id"]) if user is not None and "id" in user else None
        else:
            user_id = str(user["id"])
            merged = {**user, **user_payload}
            response = await self.http_client.put(
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                headers=self._headers(token),
                json=merged,
            )
            self._raise_for_status(response, f"update Keycloak user {admin_email}")

        if not user_id:
            raise KeycloakBootstrapError(f"Unable to resolve Keycloak user {admin_email}.")

        reset = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/reset-password",
            headers=self._headers(token),
            json={
                "type": "password",
                "value": admin_password,
                "temporary": False,
            },
        )
        self._raise_for_status(reset, f"set Keycloak password for {admin_email}")
        return user_id

    async def _find_user(self, token: str, admin_email: str) -> dict[str, Any] | None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/users",
            headers=self._headers(token),
            params={"username": admin_email, "exact": "true"},
        )
        self._raise_for_status(response, f"find Keycloak user {admin_email}")
        payload = response.json()
        if not isinstance(payload, list):
            raise KeycloakBootstrapError("Keycloak user lookup response was invalid.")
        first = next((item for item in payload if isinstance(item, dict)), None)
        return dict(first) if first is not None else None

    async def _ensure_realm_role_assignment(
        self,
        token: str,
        user_id: str,
        role_name: str,
    ) -> None:
        role = await self._ensure_realm_role(token, role_name)
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
        )
        self._raise_for_status(response, "read Keycloak user role mappings")
        mapped_roles = response.json()
        if isinstance(mapped_roles, list) and any(
            isinstance(mapped, dict) and mapped.get("name") == role_name for mapped in mapped_roles
        ):
            return

        assign = await self.http_client.post(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
            json=[role],
        )
        self._raise_for_status(assign, f"assign Keycloak role {role_name}")

    def _frontend_client_payload(self) -> dict[str, Any]:
        origins = _dedupe(
            (
                self.settings.keycloak_frontend_url.rstrip("/"),
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            )
        )
        return {
            "clientId": self.settings.keycloak_frontend_client_id,
            "name": "Vezor Frontend",
            "enabled": True,
            "publicClient": True,
            "protocol": "openid-connect",
            "standardFlowEnabled": True,
            "directAccessGrantsEnabled": False,
            "redirectUris": [f"{origin}/*" for origin in origins],
            "webOrigins": origins,
            "attributes": {"pkce.code.challenge.method": "S256"},
        }

    def _headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def _raise_for_status(self, response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        raise KeycloakBootstrapError(
            f"Unable to {action}: Keycloak returned HTTP {response.status_code}."
        )


def keycloak_bootstrap_provisioner_from_settings(
    settings: Settings,
) -> KeycloakBootstrapProvisioner | None:
    if settings.keycloak_admin_username is None or settings.keycloak_admin_password is None:
        return None
    return KeycloakBootstrapProvisioner(settings)


def _user_id_from_location(location: str | None) -> str | None:
    if not location:
        return None
    user_id = location.rstrip("/").rsplit("/", 1)[-1]
    return user_id or None


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))
