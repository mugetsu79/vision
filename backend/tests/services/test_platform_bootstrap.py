from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import pytest

from argus.api.contracts import PlatformBootstrapComplete
from argus.models.tables import PlatformBootstrapSession
from argus.services.platform_bootstrap import PlatformBootstrapService


NOW = datetime(2026, 6, 9, 12, 0, tzinfo=UTC)


class _Result:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[object]:
        return self._rows

    def first(self) -> object | None:
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> object | None:
        return self._rows[0] if self._rows else None


class _MemorySession:
    def __init__(self) -> None:
        self.rows: list[object] = []

    async def __aenter__(self) -> _MemorySession:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement) -> _Result:  # noqa: ANN001
        params = statement.compile().params
        entities = {description.get("entity") for description in statement.column_descriptions}
        rows = self.rows
        if PlatformBootstrapSession in entities:
            rows = [row for row in rows if isinstance(row, PlatformBootstrapSession)]
            token_hash = params.get("token_hash_1")
            if token_hash is not None:
                rows = [row for row in rows if row.token_hash == token_hash]
            rows = sorted(
                rows,
                key=lambda row: row.created_at,
                reverse="DESC" in str(statement),
            )
        return _Result(rows)

    def add(self, row: object) -> None:
        self.rows.append(row)

    async def commit(self) -> None:
        return None

    async def refresh(self, row: object) -> None:
        return None


class _MemorySessionFactory:
    def __init__(self) -> None:
        self.session = _MemorySession()

    def __call__(self) -> _MemorySession:
        return self.session


class _RecordingPlatformProvisioner:
    def __init__(self, *, existing_superadmin: bool = False) -> None:
        self.existing_superadmin = existing_superadmin
        self.calls: list[dict[str, Any]] = []

    async def has_platform_superadmin(self, *, platform_realm: str) -> bool:
        del platform_realm
        return self.existing_superadmin

    async def provision_platform_superadmin(self, **kwargs) -> str:  # noqa: ANN003
        self.calls.append(dict(kwargs))
        self.existing_superadmin = True
        return "platform-user-1"


def _service(
    session_factory: _MemorySessionFactory,
    provisioner: _RecordingPlatformProvisioner | None = None,
) -> PlatformBootstrapService:
    return PlatformBootstrapService(
        session_factory=session_factory,
        identity_provisioner=provisioner,
        token_hasher=lambda token: f"hash:{hashlib.sha256(token.encode()).hexdigest()}",
        now_factory=lambda: NOW,
    )


@pytest.mark.asyncio
async def test_status_reports_available_before_consumption_and_stores_only_hash() -> None:
    session_factory = _MemorySessionFactory()
    service = _service(session_factory)

    await service.ensure_session(raw_token="vzplat_local_once")
    status = await service.status()

    assert status.available is True
    assert status.consumed_at is None
    serialized_rows = str([row.__dict__ for row in session_factory.session.rows])
    assert "vzplat_local_once" not in serialized_rows
    assert "hash:" in serialized_rows


@pytest.mark.asyncio
async def test_complete_consumes_token_and_provisions_platform_superadmin() -> None:
    session_factory = _MemorySessionFactory()
    provisioner = _RecordingPlatformProvisioner()
    service = _service(session_factory, provisioner)
    await service.ensure_session(raw_token="vzplat_local_once")

    completed = await service.complete(
        PlatformBootstrapComplete(
            bootstrap_token="vzplat_local_once",
            email="owner@example.com",
            first_name="Owner",
            last_name="One",
            password="change-me-123456",
        )
    )

    sessions = [
        row
        for row in session_factory.session.rows
        if isinstance(row, PlatformBootstrapSession)
    ]
    serialized_rows = str([row.__dict__ for row in session_factory.session.rows])
    assert completed.email == "owner@example.com"
    assert completed.realm == "platform-admin"
    assert completed.role == "superadmin"
    assert sessions[0].consumed_at == NOW
    assert sessions[0].consumed_by_subject == "platform-user-1"
    assert provisioner.calls == [
        {
            "email": "owner@example.com",
            "temporary_password": "change-me-123456",
            "first_name": "Owner",
            "last_name": "One",
            "platform_realm": "platform-admin",
        }
    ]
    assert "change-me-123456" not in serialized_rows
    assert "vzplat_local_once" not in serialized_rows


@pytest.mark.asyncio
async def test_complete_rejects_when_platform_superadmin_already_exists() -> None:
    session_factory = _MemorySessionFactory()
    provisioner = _RecordingPlatformProvisioner(existing_superadmin=True)
    service = _service(session_factory, provisioner)
    await service.ensure_session(raw_token="vzplat_local_once")

    with pytest.raises(ValueError, match="already exists"):
        await service.complete(
            PlatformBootstrapComplete(
                bootstrap_token="vzplat_local_once",
                email="owner@example.com",
                first_name="Owner",
                last_name="One",
                password="change-me-123456",
            )
        )

    sessions = [
        row
        for row in session_factory.session.rows
        if isinstance(row, PlatformBootstrapSession)
    ]
    assert sessions[0].consumed_at is None
    assert provisioner.calls == []


@pytest.mark.asyncio
async def test_complete_rejects_replay_after_token_is_consumed() -> None:
    session_factory = _MemorySessionFactory()
    service = _service(session_factory, _RecordingPlatformProvisioner())
    payload = PlatformBootstrapComplete(
        bootstrap_token="vzplat_local_once",
        email="owner@example.com",
        first_name="Owner",
        last_name="One",
        password="change-me-123456",
    )
    await service.ensure_session(raw_token="vzplat_local_once")
    await service.complete(payload)

    with pytest.raises(ValueError, match="already consumed"):
        await service.complete(payload)
