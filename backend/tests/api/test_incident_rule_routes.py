from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    IncidentRuleResponse,
    IncidentRuleValidationResponse,
    TenantContext,
)
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import IncidentRuleSeverity, RoleEnum, RuleAction


def _user(role: RoleEnum = RoleEnum.ADMIN) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="admin-1",
        email="admin@argus.local",
        role=role,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=None,
        claims={},
    )


def _tenant_context(role: RoleEnum = RoleEnum.ADMIN) -> TenantContext:
    return TenantContext(
        tenant_id=uuid4(),
        tenant_slug="argus-dev",
        user=_user(role),
    )


class _FakeTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id=None,
    ) -> TenantContext:
        return TenantContext(
            tenant_id=self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request) -> AuthenticatedUser:  # noqa: ANN001
        return self.user


class _FakeIncidentRuleService:
    def __init__(self) -> None:
        self.camera_id = UUID("00000000-0000-0000-0000-000000000123")
        self.rule_id = UUID("00000000-0000-0000-0000-000000000456")
        self.created_payload = None
        self.updated_payload = None
        self.deleted_rule_id: UUID | None = None
        self.validation_payload = None

    def _response(self, *, enabled: bool = True) -> IncidentRuleResponse:
        return IncidentRuleResponse(
            id=self.rule_id,
            camera_id=self.camera_id,
            enabled=enabled,
            name="Restricted person",
            incident_type="restricted_person",
            severity=IncidentRuleSeverity.CRITICAL,
            description="Person inside restricted area.",
            predicate={
                "class_names": ["person"],
                "zone_ids": ["restricted"],
                "min_confidence": 0.7,
                "attributes": {"hi_vis": False},
            },
            action=RuleAction.RECORD_CLIP,
            cooldown_seconds=60,
            webhook_url_present=False,
            rule_hash="a" * 64,
            created_at=datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
        )

    async def list_rules(self, tenant_context: TenantContext, camera_id: UUID):
        assert tenant_context.tenant_id
        assert camera_id == self.camera_id
        return [self._response()]

    async def create_rule(self, tenant_context: TenantContext, camera_id: UUID, payload):
        assert tenant_context.tenant_id
        assert camera_id == self.camera_id
        self.created_payload = payload
        return self._response()

    async def update_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
        payload,
    ):
        assert tenant_context.tenant_id
        assert camera_id == self.camera_id
        assert rule_id == self.rule_id
        self.updated_payload = payload
        return self._response(enabled=False)

    async def delete_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> None:
        assert tenant_context.tenant_id
        assert camera_id == self.camera_id
        self.deleted_rule_id = rule_id

    async def validate_rule(self, tenant_context: TenantContext, camera_id: UUID, payload):
        assert tenant_context.tenant_id
        assert camera_id == self.camera_id
        self.validation_payload = payload
        return IncidentRuleValidationResponse(
            valid=True,
            matches=True,
            errors=[],
            normalized_incident_type="restricted_person",
            rule_hash="a" * 64,
        )


def _create_app(
    context: TenantContext,
    rules: _FakeIncidentRuleService,
    *,
    user: AuthenticatedUser | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        incident_rules=rules,
    )
    app.state.security = _FakeSecurity(user or context.user)
    return app


@pytest.mark.asyncio
async def test_camera_incident_rule_routes_crud_and_validate() -> None:
    context = _tenant_context()
    rules = _FakeIncidentRuleService()
    app = _create_app(context, rules)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        list_response = await client.get(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules",
            headers={"Authorization": "Bearer token"},
        )
        create_response = await client.post(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules",
            headers={"Authorization": "Bearer token"},
            json={
                "name": "Restricted person",
                "incident_type": "Restricted Person",
                "severity": "critical",
                "predicate": {
                    "class_names": ["person"],
                    "zone_ids": ["restricted"],
                    "min_confidence": 0.7,
                    "attributes": {"hi_vis": False},
                },
                "action": "record_clip",
                "cooldown_seconds": 60,
            },
        )
        update_response = await client.patch(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules/{rules.rule_id}",
            headers={"Authorization": "Bearer token"},
            json={"enabled": False},
        )
        validate_response = await client.post(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules/validate",
            headers={"Authorization": "Bearer token"},
            json={
                "rule": {
                    "name": "Restricted person",
                    "incident_type": "restricted_person",
                    "predicate": {"class_names": ["person"]},
                    "action": "record_clip",
                },
                "sample_detection": {
                    "class_name": "person",
                    "confidence": 0.9,
                    "zone_id": "restricted",
                    "attributes": {},
                },
            },
        )
        delete_response = await client.delete(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules/{rules.rule_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert list_response.status_code == 200
    assert list_response.json()[0]["rule_hash"] == "a" * 64
    assert create_response.status_code == 201
    assert create_response.json()["webhook_url_present"] is False
    assert rules.created_payload.incident_type == "Restricted Person"
    assert update_response.status_code == 200
    assert update_response.json()["enabled"] is False
    assert rules.updated_payload.enabled is False
    assert validate_response.status_code == 200
    assert validate_response.json()["matches"] is True
    assert rules.validation_payload.sample_detection["class_name"] == "person"
    assert delete_response.status_code == 204
    assert rules.deleted_rule_id == rules.rule_id


@pytest.mark.asyncio
async def test_viewer_cannot_mutate_incident_rules() -> None:
    context = _tenant_context(role=RoleEnum.VIEWER)
    rules = _FakeIncidentRuleService()
    app = _create_app(context, rules, user=context.user)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            f"/api/v1/cameras/{rules.camera_id}/incident-rules",
            headers={"Authorization": "Bearer token"},
            json={
                "name": "Restricted person",
                "incident_type": "restricted_person",
                "predicate": {"class_names": ["person"]},
                "action": "record_clip",
            },
        )

    assert response.status_code == 403
    assert rules.created_payload is None
