from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from math import nan
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from argus.api.contracts import EvidenceRecordingPolicy
from argus.models import Base
from argus.models.enums import ModelFormat, ModelTask, ProcessingMode, TrackerType
from argus.models.tables import Camera, Model, PrivacyManifestSnapshot, Site, Tenant
from argus.services.privacy_manifests import (
    PrivacyManifestService,
    build_privacy_manifest,
    canonical_json,
    hash_manifest,
)


def test_privacy_manifest_is_deterministic_and_disables_biometrics_by_default() -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    policy = EvidenceRecordingPolicy(storage_profile="edge_local")

    first = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=policy,
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )
    second = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=policy,
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )

    assert first == second
    assert first["identity"]["face_identification"] == "disabled"
    assert first["identity"]["biometric_identification"] == "disabled"
    assert first["plates"]["plaintext_storage"] == "blocked"
    assert first["storage"]["residency"] == "edge"
    assert hash_manifest(first) == hash_manifest(second)


class _Result:
    def __init__(self, values: list[PrivacyManifestSnapshot]) -> None:
        self.values = values

    def scalar_one_or_none(self) -> PrivacyManifestSnapshot | None:
        return self.values[0] if self.values else None


class _Session:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    async def execute(self, statement):  # noqa: ANN001
        snapshots = self.state["snapshots"]
        assert isinstance(snapshots, list)
        manifest_hash = _manifest_hash_from_statement(statement)
        if manifest_hash is None:
            return _Result(snapshots)
        return _Result(
            [
                snapshot
                for snapshot in snapshots
                if snapshot.manifest_hash == manifest_hash
            ]
        )

    def add(self, snapshot: PrivacyManifestSnapshot) -> None:
        snapshot.id = snapshot.id or uuid4()
        self.state["pending"] = snapshot

    async def commit(self) -> None:
        if self.state.get("raise_integrity_once") and not self.state.get("integrity_raised"):
            self.state["integrity_raised"] = True
            pending = self.state.pop("pending")
            assert isinstance(pending, PrivacyManifestSnapshot)
            snapshots = self.state["snapshots"]
            assert isinstance(snapshots, list)
            snapshots.append(
                PrivacyManifestSnapshot(
                    id=uuid4(),
                    tenant_id=pending.tenant_id,
                    camera_id=pending.camera_id,
                    schema_version=pending.schema_version,
                    manifest_hash=pending.manifest_hash,
                    manifest=dict(pending.manifest),
                )
            )
            raise IntegrityError("INSERT", {}, Exception("duplicate manifest hash"))

        pending = self.state.pop("pending", None)
        if pending is not None:
            snapshots = self.state["snapshots"]
            assert isinstance(snapshots, list)
            assert isinstance(pending, PrivacyManifestSnapshot)
            snapshots.append(pending)
        self.state["commits"] = int(self.state.get("commits", 0)) + 1

    async def rollback(self) -> None:
        self.state["rollbacks"] = int(self.state.get("rollbacks", 0)) + 1

    async def refresh(self, snapshot: PrivacyManifestSnapshot) -> None:
        snapshot.created_at = snapshot.created_at or datetime.now(tz=UTC)


class _SessionFactory:
    def __init__(self, *, raise_integrity_once: bool = False) -> None:
        self.state: dict[str, object] = {
            "snapshots": [],
            "raise_integrity_once": raise_integrity_once,
        }

    def __call__(self) -> _Session:
        return _Session(self.state)


@pytest.mark.asyncio
async def test_privacy_manifest_service_reuses_identical_manifest_snapshot() -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    manifest = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=EvidenceRecordingPolicy(storage_profile="edge_local"),
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )
    session_factory = _SessionFactory()
    service = PrivacyManifestService(session_factory=session_factory)

    first = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        manifest=manifest,
    )
    second = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        manifest=manifest,
    )

    snapshots = session_factory.state["snapshots"]
    assert isinstance(snapshots, list)
    assert first.id == second.id
    assert first.manifest_hash == hash_manifest(manifest)
    assert len(snapshots) == 1
    assert session_factory.state["commits"] == 1


@pytest.mark.asyncio
async def test_privacy_manifest_service_reuses_snapshot_in_postgres() -> None:
    _skip_without_docker()
    try:
        from testcontainers.postgres import PostgresContainer
    except ModuleNotFoundError as exc:
        pytest.skip(f"Postgres testcontainer unavailable: {exc}")

    try:
        postgres = PostgresContainer("postgres:16-alpine")
        postgres.start()
    except Exception as exc:
        pytest.skip(f"Postgres testcontainer unavailable: {exc}")

    postgres_url = postgres.get_connection_url()
    async_url = postgres_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        tenant_id = uuid4()
        camera_id = uuid4()
        await _seed_manifest_foreign_keys(
            session_factory=session_factory,
            tenant_id=tenant_id,
            camera_id=camera_id,
        )
        service = PrivacyManifestService(session_factory=session_factory)
        manifest = build_privacy_manifest(
            tenant_id=tenant_id,
            camera_id=camera_id,
            deployment_mode="edge",
            recording_policy=EvidenceRecordingPolicy(storage_profile="edge_local"),
            allow_plaintext_plates=False,
            plaintext_justification=None,
        )

        first = await service.get_or_create_snapshot(
            tenant_id=tenant_id,
            camera_id=camera_id,
            manifest=manifest,
        )
        second = await service.get_or_create_snapshot(
            tenant_id=tenant_id,
            camera_id=camera_id,
            manifest=manifest,
        )

        async with session_factory() as session:
            snapshot_count = await session.scalar(
                select(func.count()).select_from(PrivacyManifestSnapshot)
            )
        assert first.id == second.id
        assert first.manifest_hash == hash_manifest(manifest)
        assert snapshot_count == 1
    finally:
        await engine.dispose()
        postgres.stop()


@pytest.mark.asyncio
async def test_privacy_manifest_service_reselects_snapshot_after_unique_conflict() -> None:
    camera_id = uuid4()
    tenant_id = uuid4()
    manifest = build_privacy_manifest(
        tenant_id=tenant_id,
        camera_id=camera_id,
        deployment_mode="edge",
        recording_policy=EvidenceRecordingPolicy(storage_profile="edge_local"),
        allow_plaintext_plates=False,
        plaintext_justification=None,
    )
    session_factory = _SessionFactory(raise_integrity_once=True)
    service = PrivacyManifestService(session_factory=session_factory)

    snapshot = await service.get_or_create_snapshot(
        tenant_id=tenant_id,
        camera_id=camera_id,
        manifest=manifest,
    )

    snapshots = session_factory.state["snapshots"]
    assert isinstance(snapshots, list)
    assert snapshot.id == snapshots[0].id
    assert snapshot.manifest_hash == hash_manifest(manifest)
    assert len(snapshots) == 1
    assert session_factory.state["rollbacks"] == 1


def test_canonical_json_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError):
        canonical_json({"bad": nan})


def _skip_without_docker() -> None:
    try:
        result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        pytest.skip(f"Docker unavailable for Postgres integration test: {exc}")
    if result.returncode != 0:
        pytest.skip(f"Docker unavailable for Postgres integration test: {result.stderr.strip()}")


def _manifest_hash_from_statement(statement) -> str | None:  # noqa: ANN001
    compiled = statement.compile()
    for key, value in compiled.params.items():
        if "manifest_hash" in key and isinstance(value, str):
            return value
    return None


async def _seed_manifest_foreign_keys(
    *,
    session_factory: async_sessionmaker,
    tenant_id,
    camera_id,
) -> None:
    model_id = uuid4()
    site_id = uuid4()
    async with session_factory() as session:
        session.add(
            Tenant(
                id=tenant_id,
                name="Test Tenant",
                slug="test-tenant",
            )
        )
        await session.flush()

        session.add_all(
            [
                Site(
                    id=site_id,
                    tenant_id=tenant_id,
                    name="Test Site",
                    tz="UTC",
                ),
                Model(
                    id=model_id,
                    name="YOLO Test",
                    version="test",
                    task=ModelTask.DETECT,
                    path="/models/test.onnx",
                    format=ModelFormat.ONNX,
                    classes=["person"],
                    capability_config={},
                    input_shape={"width": 640, "height": 640},
                    sha256="a" * 64,
                    size_bytes=1,
                ),
            ]
        )
        await session.flush()

        session.add(
            Camera(
                id=camera_id,
                site_id=site_id,
                name="Dock Camera",
                rtsp_url_encrypted="encrypted",
                processing_mode=ProcessingMode.EDGE,
                primary_model_id=model_id,
                secondary_model_id=None,
                tracker_type=TrackerType.BOTSORT,
                active_classes=[],
                runtime_vocabulary=[],
                runtime_vocabulary_version=0,
                attribute_rules=[],
                zones=[],
                vision_profile={},
                detection_regions=[],
                privacy={},
                browser_delivery={},
                frame_skip=1,
                fps_cap=25,
            )
        )
        await session.commit()
