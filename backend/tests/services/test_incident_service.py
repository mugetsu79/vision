from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import TenantContext
from argus.core.security import AuthenticatedUser
from argus.models.enums import IncidentReviewStatus, RoleEnum
from argus.models.tables import Incident
from argus.services.app import IncidentService


def _compiled_sql(statement: object) -> str:
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


class _ScalarResult:
    def __init__(self, row: tuple[Incident, str] | None) -> None:
        self.row = row

    def all(self) -> list[tuple[Incident, str]]:
        return [self.row] if self.row is not None else []

    def one_or_none(self) -> tuple[Incident, str] | None:
        return self.row


class _FakeSession:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state
        self.commits = 0
        self.refreshes = 0

    async def __aenter__(self) -> _FakeSession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        self.state["last_statement"] = statement
        return _ScalarResult(self.state.get("row"))  # type: ignore[arg-type]

    async def commit(self) -> None:
        self.commits += 1
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def refresh(self, obj: object) -> None:
        self.refreshes += 1
        self.state["refreshes"] = int(self.state.get("refreshes", 0)) + 1


class _FakeSessionFactory:
    def __init__(self, row: tuple[Incident, str] | None) -> None:
        self.state: dict[str, object] = {"row": row}

    def __call__(self) -> _FakeSession:
        return _FakeSession(self.state)


class _FakeAuditLogger:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def record(self, **kwargs: object) -> None:
        self.calls.append(kwargs)


def _tenant_context(tenant_id=None) -> TenantContext:  # noqa: ANN001
    tenant_uuid = tenant_id or uuid4()
    return TenantContext(
        tenant_id=tenant_uuid,
        tenant_slug="test-tenant",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://localhost:8080/realms/argus-dev",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_uuid),
            claims={},
        ),
    )


def _incident() -> Incident:
    return Incident(
        id=uuid4(),
        camera_id=uuid4(),
        ts=datetime(2026, 4, 28, 10, 0, tzinfo=UTC),
        type="ppe-missing",
        payload={"severity": "high"},
        snapshot_url=None,
        clip_url="https://minio.local/signed/incidents/1.mjpeg",
        storage_bytes=2_097_152,
        review_status=IncidentReviewStatus.PENDING,
        reviewed_at=None,
        reviewed_by_subject=None,
    )


@pytest.mark.asyncio
async def test_update_review_state_marks_incident_reviewed_and_audits() -> None:
    incident = _incident()
    audit = _FakeAuditLogger()
    service = IncidentService(
        _FakeSessionFactory((incident, "Forklift Gate")),
        audit_logger=audit,
    )
    context = _tenant_context()

    response = await service.update_review_state(
        context,
        incident_id=incident.id,
        review_status=IncidentReviewStatus.REVIEWED,
    )

    assert response.review_status == IncidentReviewStatus.REVIEWED
    assert response.reviewed_at is not None
    assert response.reviewed_by_subject == "operator-1"
    assert incident.review_status == IncidentReviewStatus.REVIEWED
    assert incident.reviewed_at is not None
    assert incident.reviewed_by_subject == "operator-1"
    assert len(audit.calls) == 1
    assert audit.calls[0]["action"] == "incident.review"
    assert audit.calls[0]["target"] == f"incident:{incident.id}"
    assert audit.calls[0]["tenant_context"] == context
    assert audit.calls[0]["meta"] == {
        "review_status": "reviewed",
        "previous_review_status": "pending",
        "camera_id": str(incident.camera_id),
        "incident_type": "ppe-missing",
        "user_subject": "operator-1",
    }


@pytest.mark.asyncio
async def test_update_review_state_reopens_incident_and_clears_reviewer() -> None:
    incident = _incident()
    incident.review_status = IncidentReviewStatus.REVIEWED
    incident.reviewed_at = datetime(2026, 4, 28, 10, 5, tzinfo=UTC)
    incident.reviewed_by_subject = "operator-1"
    service = IncidentService(_FakeSessionFactory((incident, "Forklift Gate")), audit_logger=None)

    response = await service.update_review_state(
        _tenant_context(),
        incident_id=incident.id,
        review_status=IncidentReviewStatus.PENDING,
    )

    assert response.review_status == IncidentReviewStatus.PENDING
    assert response.reviewed_at is None
    assert response.reviewed_by_subject is None
    assert incident.review_status == IncidentReviewStatus.PENDING
    assert incident.reviewed_at is None
    assert incident.reviewed_by_subject is None


@pytest.mark.asyncio
async def test_update_review_state_is_idempotent() -> None:
    incident = _incident()
    audit = _FakeAuditLogger()
    session_factory = _FakeSessionFactory((incident, "Forklift Gate"))
    service = IncidentService(session_factory, audit_logger=audit)

    response = await service.update_review_state(
        _tenant_context(),
        incident_id=incident.id,
        review_status=IncidentReviewStatus.PENDING,
    )

    assert response.review_status == IncidentReviewStatus.PENDING
    assert audit.calls == []
    assert session_factory.state.get("commits", 0) == 0


@pytest.mark.asyncio
async def test_update_review_state_raises_404_when_incident_not_in_tenant_scope() -> None:
    session_factory = _FakeSessionFactory(None)
    service = IncidentService(session_factory, audit_logger=None)

    with pytest.raises(HTTPException) as exc_info:
        await service.update_review_state(
            _tenant_context(),
            incident_id=uuid4(),
            review_status=IncidentReviewStatus.REVIEWED,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Incident not found."
    statement = session_factory.state["last_statement"]
    sql = _compiled_sql(statement)
    assert "sites.tenant_id" in sql
    assert "incidents.id" in sql
