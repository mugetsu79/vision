from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import PolicyDraftResponse, TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.models.enums import PolicyDraftStatus, RoleEnum


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
        tenant_id=UUID("00000000-0000-0000-0000-000000000111"),
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


class _FakePolicyDraftService:
    def __init__(self) -> None:
        self.draft_id = UUID("00000000-0000-0000-0000-000000000222")
        self.camera_id = UUID("00000000-0000-0000-0000-000000000333")
        self.created_payload = None
        self.approved_id: UUID | None = None
        self.rejected_id: UUID | None = None
        self.applied_id: UUID | None = None

    def _response(
        self,
        *,
        status: PolicyDraftStatus = PolicyDraftStatus.DRAFT,
    ) -> PolicyDraftResponse:
        approved_subject = (
            "admin-1"
            if status in {PolicyDraftStatus.APPROVED, PolicyDraftStatus.APPLIED}
            else None
        )
        decided_at = (
            datetime(2026, 5, 12, 12, 5, tzinfo=UTC)
            if status
            in {
                PolicyDraftStatus.APPROVED,
                PolicyDraftStatus.REJECTED,
                PolicyDraftStatus.APPLIED,
            }
            else None
        )
        return PolicyDraftResponse(
            id=self.draft_id,
            tenant_id=UUID("00000000-0000-0000-0000-000000000111"),
            camera_id=self.camera_id,
            site_id=None,
            status=status,
            prompt="Watch forklifts in the dock zone and record clips",
            structured_diff={
                "scene_contract": {"after": {"runtime_vocabulary": ["forklift"]}},
                "privacy_manifest": {"after": {"mask_faces": True}},
                "recording_policy": {"after": {"enabled": True, "mode": "event_clip"}},
                "runtime_vocabulary": {"add": ["forklift"]},
                "detection_regions": {"add": [{"id": "dock", "name": "Dock"}]},
                "rule_changes": [
                    {
                        "incident_type": "forklift_activity",
                        "action": "record_clip",
                        "predicate": {"class_names": ["forklift"], "zone_ids": ["dock"]},
                    }
                ],
            },
            metadata={
                "llm_provider": "openai",
                "llm_model": "gpt-4.1-mini",
                "llm_profile_hash": "c" * 64,
            },
            created_by_subject="admin-1",
            approved_by_subject=approved_subject,
            rejected_by_subject="admin-1" if status is PolicyDraftStatus.REJECTED else None,
            applied_by_subject="admin-1" if status is PolicyDraftStatus.APPLIED else None,
            created_at=datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
            decided_at=decided_at,
            applied_at=datetime(2026, 5, 12, 12, 10, tzinfo=UTC)
            if status is PolicyDraftStatus.APPLIED
            else None,
        )

    async def create_draft(self, tenant_context: TenantContext, payload):
        assert tenant_context.tenant_id
        self.created_payload = payload
        return self._response()

    async def get_draft(self, tenant_context: TenantContext, draft_id: UUID):
        assert tenant_context.tenant_id
        assert draft_id == self.draft_id
        return self._response()

    async def approve_draft(self, tenant_context: TenantContext, draft_id: UUID):
        assert tenant_context.tenant_id
        self.approved_id = draft_id
        return self._response(status=PolicyDraftStatus.APPROVED)

    async def reject_draft(self, tenant_context: TenantContext, draft_id: UUID):
        assert tenant_context.tenant_id
        self.rejected_id = draft_id
        return self._response(status=PolicyDraftStatus.REJECTED)

    async def apply_draft(self, tenant_context: TenantContext, draft_id: UUID):
        assert tenant_context.tenant_id
        self.applied_id = draft_id
        return self._response(status=PolicyDraftStatus.APPLIED)


def _create_app(
    context: TenantContext,
    policy_drafts: _FakePolicyDraftService,
    *,
    user: AuthenticatedUser | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(context),
        policy_drafts=policy_drafts,
    )
    app.state.security = _FakeSecurity(user or context.user)
    return app


@pytest.mark.asyncio
async def test_policy_draft_routes_create_review_and_decide() -> None:
    context = _tenant_context()
    policy_drafts = _FakePolicyDraftService()
    app = _create_app(context, policy_drafts)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/policy-drafts",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(policy_drafts.camera_id),
                "prompt": "Watch forklifts in the dock zone and record clips",
                "use_llm": True,
            },
        )
        get_response = await client.get(
            f"/api/v1/policy-drafts/{policy_drafts.draft_id}",
            headers={"Authorization": "Bearer token"},
        )
        approve_response = await client.post(
            f"/api/v1/policy-drafts/{policy_drafts.draft_id}/approve",
            headers={"Authorization": "Bearer token"},
        )
        reject_response = await client.post(
            f"/api/v1/policy-drafts/{policy_drafts.draft_id}/reject",
            headers={"Authorization": "Bearer token"},
        )
        apply_response = await client.post(
            f"/api/v1/policy-drafts/{policy_drafts.draft_id}/apply",
            headers={"Authorization": "Bearer token"},
        )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "draft"
    assert create_response.json()["structured_diff"]["runtime_vocabulary"]["add"] == ["forklift"]
    assert create_response.json()["metadata"]["llm_profile_hash"] == "c" * 64
    assert policy_drafts.created_payload.camera_id == policy_drafts.camera_id
    assert policy_drafts.created_payload.prompt.startswith("Watch forklifts")
    assert get_response.status_code == 200
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"
    assert apply_response.status_code == 200
    assert apply_response.json()["status"] == "applied"
    assert policy_drafts.approved_id == policy_drafts.draft_id
    assert policy_drafts.rejected_id == policy_drafts.draft_id
    assert policy_drafts.applied_id == policy_drafts.draft_id


@pytest.mark.asyncio
async def test_viewer_cannot_create_policy_drafts() -> None:
    context = _tenant_context(role=RoleEnum.VIEWER)
    policy_drafts = _FakePolicyDraftService()
    app = _create_app(context, policy_drafts, user=context.user)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/policy-drafts",
            headers={"Authorization": "Bearer token"},
            json={
                "camera_id": str(policy_drafts.camera_id),
                "prompt": "Watch forklifts",
            },
        )

    assert response.status_code == 403
    assert policy_drafts.created_payload is None
