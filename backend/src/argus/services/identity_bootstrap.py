from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx

from argus.core.config import Settings
from argus.models.enums import RoleEnum


class KeycloakBootstrapError(RuntimeError):
    """Raised when first-run identity provisioning cannot complete."""


_TENANT_USER_ROLES = {RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN}


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
        admin_first_name: str,
        admin_last_name: str,
    ) -> str:
        token = await self._admin_token()
        await self._ensure_realm(token, tenant_name=tenant_name)
        for role in (RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN):
            await self._ensure_realm_role(token, role.value)
        client_id = await self._ensure_frontend_client(token)
        await self._ensure_tenant_user_profile_attributes(token)
        await self._ensure_user_attribute_mapper(token, client_id, "tenant_id")
        await self._ensure_user_attribute_mapper(token, client_id, "tenant")
        cli_client_id = await self._ensure_cli_client(token)
        await self._ensure_user_attribute_mapper(token, cli_client_id, "tenant_id")
        await self._ensure_user_attribute_mapper(token, cli_client_id, "tenant")
        user_id = await self._ensure_tenant_user(
            token,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            email=admin_email,
            password=admin_password,
            first_name=admin_first_name,
            last_name=admin_last_name,
            password_temporary=False,
        )
        await self._ensure_realm_role_assignment(token, user_id, RoleEnum.ADMIN.value)
        return user_id

    async def provision_tenant_user(
        self,
        *,
        tenant_id: UUID,
        tenant_slug: str,
        email: str,
        temporary_password: str,
        first_name: str,
        last_name: str,
        role: RoleEnum,
    ) -> str:
        if role is RoleEnum.SUPERADMIN:
            raise KeycloakBootstrapError("Tenant users cannot be assigned superadmin.")

        token = await self._admin_token()
        for required_role in (RoleEnum.VIEWER, RoleEnum.OPERATOR, RoleEnum.ADMIN):
            await self._ensure_realm_role(token, required_role.value)
        user_id = await self._ensure_tenant_user(
            token,
            tenant_id=tenant_id,
            tenant_slug=tenant_slug,
            email=email,
            password=temporary_password,
            first_name=first_name,
            last_name=last_name,
            password_temporary=True,
        )
        await self._ensure_realm_role_assignment(token, user_id, role.value)
        return user_id

    async def has_platform_superadmin(self, *, platform_realm: str) -> bool:
        token = await self._admin_token()
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{platform_realm}/roles/{RoleEnum.SUPERADMIN.value}/users",
            headers=self._headers(token),
        )
        if response.status_code == 404:
            return False
        self._raise_for_status(response, "list platform superadmin users")
        payload = response.json()
        return isinstance(payload, list) and bool(payload)

    async def provision_platform_superadmin(
        self,
        *,
        email: str,
        temporary_password: str,
        first_name: str,
        last_name: str,
        platform_realm: str,
    ) -> str:
        token = await self._admin_token()
        await self._ensure_platform_realm(token, platform_realm=platform_realm)
        await self._ensure_realm_role_in_realm(
            token,
            platform_realm,
            RoleEnum.SUPERADMIN.value,
        )
        await self._ensure_client_in_realm(
            token,
            platform_realm,
            self.settings.keycloak_frontend_client_id,
            self._frontend_client_payload(),
        )
        await self._ensure_client_in_realm(
            token,
            platform_realm,
            self.settings.keycloak_cli_client_id,
            self._cli_client_payload(),
        )
        user_id = await self._ensure_platform_user(
            token,
            platform_realm=platform_realm,
            email=email,
            password=temporary_password,
            first_name=first_name,
            last_name=last_name,
        )
        await self._ensure_realm_role_assignment_in_realm(
            token,
            platform_realm,
            user_id,
            RoleEnum.SUPERADMIN.value,
        )
        return user_id

    async def update_tenant_user(
        self,
        *,
        user_id: str,
        first_name: str,
        last_name: str,
        enabled: bool,
    ) -> None:
        token = await self._admin_token()
        user = await self._read_user(token, user_id)
        payload = {
            **user,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": enabled,
        }
        response = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
            headers=self._headers(token),
            json=payload,
        )
        self._raise_for_status(response, f"update Keycloak user {user_id}")

    async def set_tenant_user_role(self, *, user_id: str, role: RoleEnum) -> None:
        if role not in _TENANT_USER_ROLES:
            raise KeycloakBootstrapError("Tenant users cannot be assigned superadmin.")

        token = await self._admin_token()
        desired_role = await self._ensure_realm_role(token, role.value)
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
        )
        self._raise_for_status(response, "read Keycloak user role mappings")
        mapped_roles = response.json()
        if not isinstance(mapped_roles, list):
            raise KeycloakBootstrapError("Keycloak user role mappings response was invalid.")

        tenant_role_names = {tenant_role.value for tenant_role in _TENANT_USER_ROLES}
        stale_roles = [
            mapped
            for mapped in mapped_roles
            if isinstance(mapped, dict)
            and mapped.get("name") in tenant_role_names
            and mapped.get("name") != role.value
        ]
        if stale_roles:
            remove = await self.http_client.request(
                "DELETE",
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
                headers=self._headers(token),
                json=stale_roles,
            )
            self._raise_for_status(remove, f"remove Keycloak tenant roles for {user_id}")

        if any(
            isinstance(mapped, dict) and mapped.get("name") == role.value
            for mapped in mapped_roles
        ):
            return

        assign = await self.http_client.post(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
            json=[desired_role],
        )
        self._raise_for_status(assign, f"assign Keycloak role {role.value}")

    async def reset_tenant_user_password(
        self,
        *,
        user_id: str,
        temporary_password: str,
    ) -> None:
        token = await self._admin_token()
        response = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/reset-password",
            headers=self._headers(token),
            json={
                "type": "password",
                "value": temporary_password,
                "temporary": True,
            },
        )
        self._raise_for_status(response, f"set Keycloak password for {user_id}")

    async def reconcile_frontend_client(self) -> bool:
        token = await self._admin_token()
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}",
            headers=self._headers(token),
        )
        if response.status_code == 404:
            return False
        self._raise_for_status(response, f"read Keycloak realm {self.realm}")
        await self._ensure_frontend_client(token)
        return True

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
        client = await self._find_client(token, self.settings.keycloak_frontend_client_id)
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
            client = await self._find_client(token, self.settings.keycloak_frontend_client_id)
        if client is None or not isinstance(client.get("id"), str):
            raise KeycloakBootstrapError(
                f"Unable to resolve Keycloak client {self.settings.keycloak_frontend_client_id}."
            )

        client_id = str(client["id"])
        merged = {
            **client,
            **self._frontend_client_payload(existing_attributes=client.get("attributes")),
        }
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

    async def _ensure_cli_client(self, token: str) -> str:
        client = await self._find_client(token, self.settings.keycloak_cli_client_id)
        if client is None:
            response = await self.http_client.post(
                f"{self.base_url}/admin/realms/{self.realm}/clients",
                headers=self._headers(token),
                json=self._cli_client_payload(),
            )
            self._raise_for_status(
                response,
                f"create Keycloak client {self.settings.keycloak_cli_client_id}",
            )
            client = await self._find_client(token, self.settings.keycloak_cli_client_id)
        if client is None or not isinstance(client.get("id"), str):
            raise KeycloakBootstrapError(
                f"Unable to resolve Keycloak client {self.settings.keycloak_cli_client_id}."
            )

        client_id = str(client["id"])
        merged = {**client, **self._cli_client_payload()}
        response = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/clients/{client_id}",
            headers=self._headers(token),
            json=merged,
        )
        self._raise_for_status(
            response,
            f"update Keycloak client {self.settings.keycloak_cli_client_id}",
        )
        return client_id

    async def _ensure_tenant_user_profile_attributes(self, token: str) -> None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/users/profile",
            headers=self._headers(token),
        )
        if response.status_code == 404:
            return
        self._raise_for_status(response, "read Keycloak user profile")
        profile = response.json()
        if not isinstance(profile, dict):
            raise KeycloakBootstrapError("Keycloak user profile response was invalid.")

        attributes = profile.get("attributes")
        if not isinstance(attributes, list):
            raise KeycloakBootstrapError("Keycloak user profile attributes were invalid.")

        desired_attributes = [
            {
                "name": "tenant",
                "displayName": "Tenant",
                "multivalued": False,
                "permissions": {"view": ["admin"], "edit": ["admin"]},
                "validations": {"length": {"max": 255}},
            },
            {
                "name": "tenant_id",
                "displayName": "Tenant ID",
                "multivalued": False,
                "permissions": {"view": ["admin"], "edit": ["admin"]},
                "validations": {"length": {"max": 64}},
            },
        ]

        changed = False
        updated_attributes: list[object] = []
        desired_by_name = {str(attribute["name"]): attribute for attribute in desired_attributes}
        seen_names: set[str] = set()
        for attribute in attributes:
            if not isinstance(attribute, dict):
                updated_attributes.append(attribute)
                continue
            name = attribute.get("name")
            if not isinstance(name, str) or name not in desired_by_name:
                updated_attributes.append(attribute)
                continue
            seen_names.add(name)
            desired = desired_by_name[name]
            merged = {**attribute, **desired}
            if merged != attribute:
                changed = True
            updated_attributes.append(merged)

        for desired in desired_attributes:
            if desired["name"] not in seen_names:
                updated_attributes.append(desired)
                changed = True

        if not changed:
            return

        update_payload = {**profile, "attributes": updated_attributes}
        update = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/users/profile",
            headers=self._headers(token),
            json=update_payload,
        )
        self._raise_for_status(update, "update Keycloak user profile")

    async def _find_client(self, token: str, client_id: str) -> dict[str, Any] | None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/clients",
            headers=self._headers(token),
            params={"clientId": client_id},
        )
        self._raise_for_status(
            response,
            f"find Keycloak client {client_id}",
        )
        payload = response.json()
        if not isinstance(payload, list):
            raise KeycloakBootstrapError("Keycloak client lookup response was invalid.")
        first = next((item for item in payload if isinstance(item, dict)), None)
        return dict(first) if first is not None else None

    async def _ensure_platform_realm(self, token: str, *, platform_realm: str) -> None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{platform_realm}",
            headers=self._headers(token),
        )
        if response.status_code == 200:
            return
        if response.status_code != 404:
            self._raise_for_status(response, f"read Keycloak realm {platform_realm}")
        create = await self.http_client.post(
            f"{self.base_url}/admin/realms",
            headers=self._headers(token),
            json={
                "realm": platform_realm,
                "enabled": True,
                "displayName": "Vezor Platform Administration",
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "roles": {"realm": [{"name": RoleEnum.SUPERADMIN.value}]},
            },
        )
        self._raise_for_status(create, f"create Keycloak realm {platform_realm}")

    async def _ensure_realm_role_in_realm(
        self,
        token: str,
        realm: str,
        role_name: str,
    ) -> dict[str, Any]:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{realm}/roles/{role_name}",
            headers=self._headers(token),
        )
        if response.status_code == 404:
            create = await self.http_client.post(
                f"{self.base_url}/admin/realms/{realm}/roles",
                headers=self._headers(token),
                json={"name": role_name},
            )
            self._raise_for_status(create, f"create Keycloak role {role_name}")
            response = await self.http_client.get(
                f"{self.base_url}/admin/realms/{realm}/roles/{role_name}",
                headers=self._headers(token),
            )
        self._raise_for_status(response, f"read Keycloak role {role_name}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise KeycloakBootstrapError(f"Keycloak role {role_name} response was invalid.")
        return dict(payload)

    async def _ensure_client_in_realm(
        self,
        token: str,
        realm: str,
        client_id: str,
        client_payload: dict[str, Any],
    ) -> str:
        client = await self._find_client_in_realm(token, realm, client_id)
        if client is None:
            response = await self.http_client.post(
                f"{self.base_url}/admin/realms/{realm}/clients",
                headers=self._headers(token),
                json=client_payload,
            )
            self._raise_for_status(response, f"create Keycloak client {client_id}")
            client = await self._find_client_in_realm(token, realm, client_id)
        if client is None or not isinstance(client.get("id"), str):
            raise KeycloakBootstrapError(f"Unable to resolve Keycloak client {client_id}.")
        client_uuid = str(client["id"])
        response = await self.http_client.put(
            f"{self.base_url}/admin/realms/{realm}/clients/{client_uuid}",
            headers=self._headers(token),
            json={**client, **client_payload},
        )
        self._raise_for_status(response, f"update Keycloak client {client_id}")
        return client_uuid

    async def _find_client_in_realm(
        self,
        token: str,
        realm: str,
        client_id: str,
    ) -> dict[str, Any] | None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{realm}/clients",
            headers=self._headers(token),
            params={"clientId": client_id},
        )
        self._raise_for_status(response, f"find Keycloak client {client_id}")
        payload = response.json()
        if not isinstance(payload, list):
            raise KeycloakBootstrapError("Keycloak client lookup response was invalid.")
        first = next((item for item in payload if isinstance(item, dict)), None)
        return dict(first) if first is not None else None

    async def _ensure_platform_user(
        self,
        token: str,
        *,
        platform_realm: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
    ) -> str:
        user = await self._find_user_in_realm(token, platform_realm, email)
        user_payload = {
            "username": email,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
            "enabled": True,
            "emailVerified": True,
            "requiredActions": [],
        }
        if user is None:
            response = await self.http_client.post(
                f"{self.base_url}/admin/realms/{platform_realm}/users",
                headers=self._headers(token),
                json=user_payload,
            )
            self._raise_for_status(response, f"create Keycloak user {email}")
            user_id = _user_id_from_location(response.headers.get("Location"))
            if user_id is None:
                user = await self._find_user_in_realm(token, platform_realm, email)
                user_id = str(user["id"]) if user is not None and "id" in user else None
        else:
            user_id = str(user["id"])
            response = await self.http_client.put(
                f"{self.base_url}/admin/realms/{platform_realm}/users/{user_id}",
                headers=self._headers(token),
                json={**user, **user_payload},
            )
            self._raise_for_status(response, f"update Keycloak user {email}")
        if not user_id:
            raise KeycloakBootstrapError(f"Unable to resolve Keycloak user {email}.")
        reset = await self.http_client.put(
            f"{self.base_url}/admin/realms/{platform_realm}/users/{user_id}/reset-password",
            headers=self._headers(token),
            json={"type": "password", "value": password, "temporary": False},
        )
        self._raise_for_status(reset, f"set Keycloak password for {email}")
        return user_id

    async def _find_user_in_realm(
        self,
        token: str,
        realm: str,
        email: str,
    ) -> dict[str, Any] | None:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{realm}/users",
            headers=self._headers(token),
            params={"username": email, "exact": "true"},
        )
        self._raise_for_status(response, f"find Keycloak user {email}")
        payload = response.json()
        if not isinstance(payload, list):
            raise KeycloakBootstrapError("Keycloak user lookup response was invalid.")
        first = next((item for item in payload if isinstance(item, dict)), None)
        return dict(first) if first is not None else None

    async def _ensure_realm_role_assignment_in_realm(
        self,
        token: str,
        realm: str,
        user_id: str,
        role_name: str,
    ) -> None:
        role = await self._ensure_realm_role_in_realm(token, realm, role_name)
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
        )
        self._raise_for_status(response, "read Keycloak user role mappings")
        mapped_roles = response.json()
        if isinstance(mapped_roles, list) and any(
            isinstance(mapped, dict) and mapped.get("name") == role_name for mapped in mapped_roles
        ):
            return
        assign = await self.http_client.post(
            f"{self.base_url}/admin/realms/{realm}/users/{user_id}/role-mappings/realm",
            headers=self._headers(token),
            json=[role],
        )
        self._raise_for_status(assign, f"assign Keycloak role {role_name}")

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

    async def _ensure_tenant_user(
        self,
        token: str,
        *,
        tenant_id: UUID,
        tenant_slug: str,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        password_temporary: bool,
    ) -> str:
        user = await self._find_user(token, email)
        user_payload = {
            "username": email,
            "email": email,
            "firstName": first_name,
            "lastName": last_name,
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
            self._raise_for_status(response, f"create Keycloak user {email}")
            user_id = _user_id_from_location(response.headers.get("Location"))
            if user_id is None:
                user = await self._find_user(token, email)
                user_id = str(user["id"]) if user is not None and "id" in user else None
        else:
            user_id = str(user["id"])
            merged = {**user, **user_payload}
            response = await self.http_client.put(
                f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
                headers=self._headers(token),
                json=merged,
            )
            self._raise_for_status(response, f"update Keycloak user {email}")

        if not user_id:
            raise KeycloakBootstrapError(f"Unable to resolve Keycloak user {email}.")

        reset = await self.http_client.put(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}/reset-password",
            headers=self._headers(token),
            json={
                "type": "password",
                "value": password,
                "temporary": password_temporary,
            },
        )
        self._raise_for_status(reset, f"set Keycloak password for {email}")
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

    async def _read_user(self, token: str, user_id: str) -> dict[str, Any]:
        response = await self.http_client.get(
            f"{self.base_url}/admin/realms/{self.realm}/users/{user_id}",
            headers=self._headers(token),
        )
        self._raise_for_status(response, f"read Keycloak user {user_id}")
        payload = response.json()
        if not isinstance(payload, dict):
            raise KeycloakBootstrapError(f"Keycloak user {user_id} response was invalid.")
        return dict(payload)

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

    def _frontend_client_payload(
        self,
        existing_attributes: object | None = None,
    ) -> dict[str, Any]:
        origins = _dedupe(
            (
                self.settings.keycloak_frontend_url.rstrip("/"),
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            )
        )
        attributes = dict(existing_attributes) if isinstance(existing_attributes, dict) else {}
        attributes.pop("pkce.code.challenge.method", None)
        if self.settings.keycloak_frontend_disable_pkce:
            # Keycloak preserves client attributes on update unless they are explicitly blanked.
            attributes["pkce.code.challenge.method"] = ""
        else:
            attributes["pkce.code.challenge.method"] = "S256"

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
            "attributes": attributes,
        }

    def _cli_client_payload(self) -> dict[str, Any]:
        return {
            "clientId": self.settings.keycloak_cli_client_id,
            "name": "Vezor CLI",
            "enabled": True,
            "publicClient": True,
            "protocol": "openid-connect",
            "standardFlowEnabled": False,
            "directAccessGrantsEnabled": True,
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
