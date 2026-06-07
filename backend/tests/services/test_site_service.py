from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from argus.api.contracts import TenantContext
from argus.core.security import AuthenticatedUser
from argus.models.enums import RoleEnum
from argus.models.tables import Site
from argus.services import app as app_services
from argus.services.app import SiteService


class _IntegrityErrorOnCommitSession:
    async def __aenter__(self) -> _IntegrityErrorOnCommitSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def commit(self) -> None:
        raise IntegrityError("DELETE", {}, Exception("site still referenced"))

    async def rollback(self) -> None:
        return None

    async def delete(self, item: object) -> None:
        del item


class _IntegrityErrorSessionFactory:
    def __call__(self) -> _IntegrityErrorOnCommitSession:
        return _IntegrityErrorOnCommitSession()


class _AuditLogger:
    async def record(self, **kwargs: object) -> None:
        del kwargs


def _tenant_context(tenant_id) -> TenantContext:  # noqa: ANN001
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="admin-1",
            email="admin@argus.local",
            role=RoleEnum.ADMIN,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=None,
            claims={},
        ),
    )


@pytest.mark.asyncio
async def test_site_response_exposes_site_kind() -> None:
    site = Site(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Vezor Master",
        description=None,
        tz="UTC",
        geo_point=None,
        site_kind="control_plane",
        created_at=datetime(2026, 6, 7, tzinfo=UTC),
    )

    response = app_services._site_to_response(site)

    assert response.site_kind == "control_plane"


@pytest.mark.asyncio
async def test_delete_site_returns_conflict_when_site_is_still_referenced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = uuid4()
    site_id = uuid4()
    site = Site(
        id=site_id,
        tenant_id=tenant_id,
        name="FleetOps Site",
        description=None,
        tz="UTC",
        geo_point=None,
        created_at=datetime(2026, 6, 6, tzinfo=UTC),
    )

    async def fake_load_site(session, tenant_id_arg, site_id_arg):  # noqa: ANN001
        del session, tenant_id_arg, site_id_arg
        return site

    monkeypatch.setattr(app_services, "_load_site", fake_load_site)
    service = SiteService(
        session_factory=_IntegrityErrorSessionFactory(),
        audit_logger=_AuditLogger(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.delete_site(_tenant_context(tenant_id), site_id)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "Delete scenes and dependent records before deleting this site." in str(
        exc_info.value.detail
    )
