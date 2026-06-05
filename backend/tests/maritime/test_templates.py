from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import TenantContext
from argus.api.v1 import router
from argus.core.security import AuthenticatedUser
from argus.maritime.templates import MaritimeTemplateService
from argus.models.enums import RoleEnum
from argus.services.pack_registry import PackRegistry

TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
CAMERA_ID = UUID("00000000-0000-4000-8000-000000000010")
SCENE_CONTRACT_ID = UUID("00000000-0000-4000-8000-000000000020")
PACKS_ROOT = Path(__file__).resolve().parents[3] / "packs"


def _user(role: RoleEnum) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject=f"{role.value}-1",
        email=f"{role.value}@argus.local",
        role=role,
        issuer="http://issuer",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(TENANT_ID),
        claims={},
    )


class _FakeTenancyService:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.context = TenantContext(
            tenant_id=TENANT_ID,
            tenant_slug="argus-dev",
            user=user,
        )

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return self.context


class _FakeSecurity:
    def __init__(self, user: AuthenticatedUser) -> None:
        self.user = user

    async def authenticate_request(self, request: object) -> AuthenticatedUser:
        return self.user


class _FakeCameraService:
    def __init__(self, incident_rules: _FakeIncidentRuleService) -> None:
        self.incident_rules = incident_rules
        self.update_payloads: list[object] = []
        self.update_payload: object | None = None
        self.updated_camera_id: UUID | None = None
        self.worker_config_rule_count: int | None = None

    async def get_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> object:
        return SimpleNamespace(
            active_classes=["boat"],
            runtime_vocabulary={"terms": ["boat"], "source": "manual", "version": 1},
            detection_regions=[],
            zones=[],
            privacy={
                "blur_faces": True,
                "blur_plates": True,
                "method": "gaussian",
                "strength": 7,
            },
            recording_policy={
                "enabled": True,
                "mode": "event_clip",
                "pre_seconds": 4,
                "post_seconds": 8,
                "fps": 10,
                "max_duration_seconds": 15,
                "storage_profile": "central",
            },
        )

    async def update_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: object,
    ) -> object:
        self.updated_camera_id = camera_id
        self.update_payload = payload
        self.update_payloads.append(payload)
        return SimpleNamespace(id=camera_id)

    async def get_worker_config(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> object:
        self.worker_config_rule_count = len(self.incident_rules.existing) + len(
            self.incident_rules.created
        )
        return SimpleNamespace(scene_contract_hash="a" * 64)


class _FakeIncidentRuleService:
    def __init__(self) -> None:
        self.created: list[object] = []
        self.deleted: list[UUID] = []
        self.existing: list[object] = []

    async def list_rules(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> list[object]:
        return self.existing

    async def create_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: object,
    ) -> object:
        self.created.append(payload)
        return SimpleNamespace(id=UUID("00000000-0000-4000-8000-000000000030"))

    async def delete_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> None:
        self.deleted.append(rule_id)


class _FakeSceneContractService:
    def __init__(self) -> None:
        self.snapshot: object | None = SimpleNamespace(
            id=SCENE_CONTRACT_ID,
            contract_hash="a" * 64,
        )

    async def get_snapshot_by_hash(
        self,
        *,
        tenant_id: UUID,
        camera_id: UUID,
        contract_hash: str,
    ) -> object | None:
        return self.snapshot


def _create_app(user: AuthenticatedUser) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    incident_rules = _FakeIncidentRuleService()
    app.state.services = SimpleNamespace(
        tenancy=_FakeTenancyService(user),
        packs=PackRegistry(PACKS_ROOT),
        cameras=_FakeCameraService(incident_rules),
        incident_rules=incident_rules,
        scene_contracts=_FakeSceneContractService(),
    )
    app.state.security = _FakeSecurity(user)
    return app


@pytest.fixture
def template_service() -> MaritimeTemplateService:
    return MaritimeTemplateService(pack_registry=PackRegistry(PACKS_ROOT))


@pytest_asyncio.fixture
async def app() -> FastAPI:
    return _create_app(_user(RoleEnum.ADMIN))


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client


def test_manifest_templates_map_to_core_camera_payloads(
    template_service: MaritimeTemplateService,
) -> None:
    template = template_service.get_template("gangway-access")
    payload = template_service.to_core_camera_payload(template)

    assert set(payload) <= {
        "active_classes",
        "runtime_vocabulary",
        "detection_regions",
        "zones",
        "incident_rules",
        "evidence_recording_policy",
        "privacy_defaults",
    }
    assert "vessel" not in payload


@pytest.mark.asyncio
async def test_list_scene_templates(client: AsyncClient) -> None:
    response = await client.get("/api/v1/maritime/scene-templates")

    assert response.status_code == 200
    payload = response.json()
    assert {template["id"] for template in payload} == {
        "gangway-access",
        "deck-presence",
        "engine-room-safety",
        "cargo-work-area",
        "port-call-evidence",
    }


@pytest.mark.asyncio
async def test_apply_gangway_template_updates_core_camera_primitives(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    response = await client.post(
        f"/api/v1/maritime/cameras/{CAMERA_ID}/apply-template",
        json={"template_id": "gangway-access"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["template_id"] == "gangway-access"
    assert payload["scene_contract_snapshot_id"] == str(SCENE_CONTRACT_ID)
    assert app.state.services.cameras.updated_camera_id == CAMERA_ID
    assert app.state.services.cameras.update_payload.active_classes == ["person"]
    assert app.state.services.incident_rules.created
    assert app.state.services.cameras.worker_config_rule_count == 1


@pytest.mark.asyncio
async def test_apply_template_skips_existing_incident_rule(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    app.state.services.incident_rules.existing = [
        SimpleNamespace(
            id=UUID("00000000-0000-4000-8000-000000000031"),
            incident_type="gangway_access",
        )
    ]

    response = await client.post(
        f"/api/v1/maritime/cameras/{CAMERA_ID}/apply-template",
        json={"template_id": "gangway-access"},
    )

    assert response.status_code == 200
    assert app.state.services.incident_rules.created == []


@pytest.mark.asyncio
async def test_apply_template_restores_camera_when_scene_contract_lookup_fails(
    app: FastAPI,
    client: AsyncClient,
) -> None:
    app.state.services.scene_contracts.snapshot = None

    response = await client.post(
        f"/api/v1/maritime/cameras/{CAMERA_ID}/apply-template",
        json={"template_id": "gangway-access"},
    )

    assert response.status_code == 409
    assert len(app.state.services.cameras.update_payloads) == 2
    assert app.state.services.cameras.update_payloads[-1].active_classes == ["boat"]
    assert app.state.services.incident_rules.deleted == [
        UUID("00000000-0000-4000-8000-000000000030")
    ]


def test_templates_do_not_create_second_scene_engine(
    template_service: MaritimeTemplateService,
) -> None:
    template = template_service.get_template("deck-presence")

    assert template.execution_engine == "core_scene_contract"
    assert template.detector_override is None
