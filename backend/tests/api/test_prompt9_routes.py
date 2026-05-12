from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.contracts import (
    EvidenceArtifactResponse,
    EvidenceLedgerEntryResponse,
    EvidenceLedgerSummary,
    EvidenceRecordingPolicy,
    ExportArtifact,
    HistoryPoint,
    IncidentResponse,
    PrivacyManifestSnapshotResponse,
    RuntimePassportSnapshotResponse,
    RuntimePassportSummary,
    SceneContractSnapshotResponse,
    TenantContext,
    TriggerRuleSummary,
)
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser, get_current_user
from argus.main import create_app
from argus.models.enums import (
    EvidenceArtifactKind,
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    EvidenceStorageProvider,
    EvidenceStorageScope,
    IncidentReviewStatus,
    RoleEnum,
)


def _sample_user(role: RoleEnum = RoleEnum.VIEWER) -> AuthenticatedUser:
    return AuthenticatedUser(
        subject="user-1",
        email="analyst@argus.local",
        role=role,
        issuer="http://localhost:8080/realms/argus-dev",
        realm="argus-dev",
        is_superadmin=False,
        tenant_context=str(uuid4()),
        claims={},
    )


def _tenant_context(user: AuthenticatedUser) -> TenantContext:
    return TenantContext(
        tenant_id=UUID(str(user.tenant_context)),
        tenant_slug=user.realm,
        user=user,
    )


class RecordingTenancyService:
    def __init__(self, context: TenantContext) -> None:
        self.context = context

    async def resolve_context(
        self,
        *,
        user: AuthenticatedUser,
        explicit_tenant_id: UUID | None = None,
    ) -> TenantContext:
        return TenantContext(
            tenant_id=explicit_tenant_id or self.context.tenant_id,
            tenant_slug=self.context.tenant_slug,
            user=user,
        )


class RecordingHistoryService:
    def __init__(self) -> None:
        self.last_query: dict[str, object] | None = None
        self.last_series_query: dict[str, object] | None = None
        self.last_export: dict[str, object] | None = None

    async def query_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: object,
    ) -> list[HistoryPoint]:
        self.last_query = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        return [
            HistoryPoint(
                bucket=starts_at,
                camera_id=camera_ids[0] if camera_ids else None,
                class_name="car",
                event_count=18,
                granularity=granularity,
            )
        ]

    async def query_series(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        metric: object,
        include_speed: bool = False,
        speed_threshold: float | None = None,
    ) -> dict[str, object]:
        self.last_series_query = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "include_speed": include_speed,
            "speed_threshold": speed_threshold,
        }
        return {
            "granularity": granularity,
            "class_names": class_names or ["car", "bus"],
            "rows": [
                {
                    "bucket": starts_at.isoformat(),
                    "values": {"car": 18, "bus": 4},
                    "total_count": 22,
                }
            ],
        }

    async def export_history(
        self,
        context: TenantContext,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
        format_name: str,
        metric: object,
    ) -> ExportArtifact:
        self.last_export = {
            "tenant_id": context.tenant_id,
            "camera_ids": camera_ids,
            "class_names": class_names,
            "granularity": granularity,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "format_name": format_name,
        }
        return ExportArtifact(
            filename=f"history.{format_name}",
            media_type="text/csv; charset=utf-8",
            content=b"bucket,class_name,event_count\n2026-04-12T00:00:00Z,car,18\n",
        )


class RecordingIncidentService:
    def __init__(self) -> None:
        self.last_query: dict[str, object] | None = None
        self.review_calls: list[dict[str, object]] = []
        self.scene_contract_calls: list[dict[str, object]] = []
        self.privacy_manifest_calls: list[dict[str, object]] = []
        self.runtime_passport_calls: list[dict[str, object]] = []
        self.ledger_calls: list[dict[str, object]] = []
        self.artifact_content_calls: list[dict[str, object]] = []
        self.scene_contract_id = uuid4()
        self.privacy_manifest_id = uuid4()
        self.runtime_passport_id = uuid4()
        self.artifact_id = uuid4()
        self.incident_id = uuid4()

    async def list_incidents(
        self,
        context: TenantContext,
        *,
        camera_id: UUID | None,
        incident_type: str | None,
        review_status: IncidentReviewStatus | None,
        limit: int,
    ) -> list[IncidentResponse]:
        self.last_query = {
            "tenant_id": context.tenant_id,
            "camera_id": camera_id,
            "incident_type": incident_type,
            "review_status": review_status,
            "limit": limit,
        }
        return [
            IncidentResponse(
                id=self.incident_id,
                camera_id=camera_id or uuid4(),
                ts=datetime.now(tz=UTC),
                type=incident_type or "rule.restricted_person",
                payload={
                    "severity": "high",
                    "trigger_rule": _trigger_rule_summary().model_dump(mode="json"),
                },
                trigger_rule=_trigger_rule_summary(),
                snapshot_url="https://minio.local/signed/incidents/1.jpg",
                clip_url="https://minio.local/signed/incidents/1.mjpeg",
                storage_bytes=2_097_152,
                review_status=review_status or IncidentReviewStatus.PENDING,
                scene_contract_hash="a" * 64,
                scene_contract_id=self.scene_contract_id,
                privacy_manifest_hash="b" * 64,
                privacy_manifest_id=self.privacy_manifest_id,
                runtime_passport_hash="e" * 64,
                runtime_passport_id=self.runtime_passport_id,
                runtime_passport=_runtime_passport_summary(self.runtime_passport_id),
                recording_policy=EvidenceRecordingPolicy(storage_profile="edge_local"),
                evidence_artifacts=[
                    EvidenceArtifactResponse(
                        id=self.artifact_id,
                        incident_id=self.incident_id,
                        camera_id=camera_id or uuid4(),
                        kind=EvidenceArtifactKind.EVENT_CLIP,
                        status=EvidenceArtifactStatus.REMOTE_AVAILABLE,
                        storage_provider=EvidenceStorageProvider.S3_COMPATIBLE,
                        storage_scope=EvidenceStorageScope.CLOUD,
                        bucket="incidents",
                        object_key="tenant/camera/clip.mjpeg",
                        content_type="video/x-motion-jpeg",
                        sha256="c" * 64,
                        size_bytes=2_097_152,
                        review_url="https://minio.local/signed/incidents/1.mjpeg",
                    )
                ],
                ledger_summary=EvidenceLedgerSummary(
                    entry_count=2,
                    latest_action=EvidenceLedgerAction.CLIP_AVAILABLE,
                    latest_at=datetime(2026, 5, 11, 10, 1, tzinfo=UTC),
                ),
            )
        ]

    async def update_review_state(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
        review_status: IncidentReviewStatus,
    ) -> IncidentResponse:
        self.review_calls.append(
            {
                "tenant_id": context.tenant_id,
                "incident_id": incident_id,
                "review_status": review_status,
                "subject": context.user.subject,
            }
        )
        reviewed_at = (
            datetime.now(tz=UTC) if review_status == IncidentReviewStatus.REVIEWED else None
        )
        reviewed_by_subject = (
            context.user.subject if review_status == IncidentReviewStatus.REVIEWED else None
        )
        return IncidentResponse(
            id=incident_id,
            camera_id=uuid4(),
            ts=datetime.now(tz=UTC),
            type="ppe-missing",
            payload={"severity": "high"},
            snapshot_url=None,
            clip_url="https://minio.local/signed/incidents/1.mjpeg",
            storage_bytes=2_097_152,
            review_status=review_status,
            reviewed_at=reviewed_at,
            reviewed_by_subject=reviewed_by_subject,
        )

    async def get_scene_contract(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
    ) -> SceneContractSnapshotResponse:
        self.scene_contract_calls.append(
            {"tenant_id": context.tenant_id, "incident_id": incident_id}
        )
        return SceneContractSnapshotResponse(
            id=self.scene_contract_id,
            camera_id=uuid4(),
            schema_version=1,
            contract_hash="a" * 64,
            contract={"camera": {"name": "Dock Camera"}},
            created_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        )

    async def get_privacy_manifest(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
    ) -> PrivacyManifestSnapshotResponse:
        self.privacy_manifest_calls.append(
            {"tenant_id": context.tenant_id, "incident_id": incident_id}
        )
        return PrivacyManifestSnapshotResponse(
            id=self.privacy_manifest_id,
            camera_id=uuid4(),
            schema_version=1,
            manifest_hash="b" * 64,
            manifest={"identity": {"face_identification": "disabled"}},
            created_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        )

    async def get_runtime_passport(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
    ) -> RuntimePassportSnapshotResponse:
        self.runtime_passport_calls.append(
            {"tenant_id": context.tenant_id, "incident_id": incident_id}
        )
        return RuntimePassportSnapshotResponse(
            id=self.runtime_passport_id,
            camera_id=uuid4(),
            incident_id=incident_id,
            schema_version=1,
            passport_hash="e" * 64,
            passport=_runtime_passport_payload(),
            summary=_runtime_passport_summary(self.runtime_passport_id),
            created_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        )

    async def list_ledger_entries(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
    ) -> list[EvidenceLedgerEntryResponse]:
        self.ledger_calls.append({"tenant_id": context.tenant_id, "incident_id": incident_id})
        return [
            EvidenceLedgerEntryResponse(
                id=uuid4(),
                incident_id=incident_id,
                camera_id=uuid4(),
                sequence=1,
                action=EvidenceLedgerAction.INCIDENT_TRIGGERED,
                actor_type="system",
                actor_subject=None,
                occurred_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
                payload={"type": "ppe-missing"},
                previous_entry_hash=None,
                entry_hash="d" * 64,
            )
        ]

    async def get_artifact_content(
        self,
        context: TenantContext,
        *,
        incident_id: UUID,
        artifact_id: UUID,
    ) -> SimpleNamespace:
        self.artifact_content_calls.append(
            {
                "tenant_id": context.tenant_id,
                "incident_id": incident_id,
                "artifact_id": artifact_id,
            }
        )
        return SimpleNamespace(
            content_type="video/x-motion-jpeg",
            file_path=None,
            redirect_url="https://minio.local/signed/incidents/1.mjpeg",
        )


def _runtime_passport_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "model": {"sha256": "f" * 64},
        "runtime_selection_profile": {
            "profile_id": "11111111-1111-1111-1111-111111111111",
            "profile_name": "Jetson runtime",
            "profile_hash": "g" * 64,
        },
        "selected_runtime": {
            "backend": "tensorrt_engine",
            "runtime_artifact_id": "22222222-2222-2222-2222-222222222222",
            "runtime_artifact_hash": "d" * 64,
            "target_profile": "linux-aarch64-nvidia-jetson",
            "precision": "fp16",
            "validated_at": "2026-05-11T10:00:00+00:00",
            "fallback_reason": None,
        },
        "provider_versions": {"tensorrt": "10.0.0", "cuda": "12.6"},
    }


def _runtime_passport_summary(passport_id: UUID) -> RuntimePassportSummary:
    return RuntimePassportSummary(
        id=passport_id,
        passport_hash="e" * 64,
        selected_backend="tensorrt_engine",
        model_hash="f" * 64,
        runtime_artifact_id="22222222-2222-2222-2222-222222222222",
        runtime_artifact_hash="d" * 64,
        target_profile="linux-aarch64-nvidia-jetson",
        precision="fp16",
        validated_at=datetime(2026, 5, 11, 10, 0, tzinfo=UTC),
        fallback_reason=None,
        runtime_selection_profile_id=UUID("11111111-1111-1111-1111-111111111111"),
        runtime_selection_profile_name="Jetson runtime",
        runtime_selection_profile_hash="g" * 64,
    )


def _trigger_rule_summary() -> TriggerRuleSummary:
    return TriggerRuleSummary(
        id=UUID("99999999-9999-9999-9999-999999999111"),
        name="Restricted person in server room",
        incident_type="restricted_person",
        severity="critical",
        action="record_clip",
        cooldown_seconds=45,
        predicate={
            "class_names": ["person"],
            "zone_ids": ["server-room"],
            "min_confidence": 0.82,
            "attributes": {"vest": "red"},
        },
        rule_hash="f" * 64,
    )


def _create_test_app(
    *,
    user: AuthenticatedUser,
    history: RecordingHistoryService,
    incidents: RecordingIncidentService,
) -> object:
    context = _tenant_context(user)
    app = create_app(
        Settings(
            _env_file=None,
            enable_startup_services=False,
            enable_nats=False,
            enable_tracing=False,
            rtsp_encryption_key="argus-dev-rtsp-key",
        )
    )
    app.state.services = SimpleNamespace(
        tenancy=RecordingTenancyService(context),
        history=history,
        incidents=incidents,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_history_route_accepts_multi_filters_and_extended_granularity() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    camera_a = uuid4()
    camera_b = uuid4()
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=1)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/history",
            params=[
                ("camera_ids", str(camera_a)),
                ("camera_ids", str(camera_b)),
                ("class_names", "car"),
                ("class_names", "bus"),
                ("granularity", "5m"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
            ],
        )

    assert response.status_code == 200
    assert response.json()[0]["granularity"] == "5m"
    assert history.last_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": [camera_a, camera_b],
        "class_names": ["car", "bus"],
        "granularity": "5m",
        "starts_at": starts_at,
        "ends_at": ends_at,
    }


@pytest.mark.asyncio
async def test_history_series_route_returns_chart_ready_rows() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=7)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/history/series",
            params=[
                ("class_names", "car"),
                ("class_names", "bus"),
                ("granularity", "1d"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
            ],
        )

    assert response.status_code == 200
    assert response.json() == {
        "granularity": "1d",
        "metric": None,
        "class_names": ["car", "bus"],
        "rows": [
            {
                "bucket": "2026-04-12T00:00:00Z",
                "values": {"car": 18, "bus": 4},
                "total_count": 22,
                "speed_p50": None,
                "speed_p95": None,
                "speed_sample_count": None,
                "over_threshold_count": None,
            }
        ],
        "granularity_adjusted": False,
        "speed_classes_capped": False,
        "speed_classes_used": None,
        "effective_from": None,
        "effective_to": None,
        "bucket_count": 0,
        "bucket_span": None,
        "coverage_status": "populated",
        "coverage_by_bucket": [],
    }
    assert history.last_series_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": None,
        "class_names": ["car", "bus"],
        "granularity": "1d",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "include_speed": False,
        "speed_threshold": None,
    }


@pytest.mark.asyncio
async def test_export_route_accepts_multi_filters_and_extended_granularity() -> None:
    user = _sample_user()
    history = RecordingHistoryService()
    app = _create_test_app(user=user, history=history, incidents=RecordingIncidentService())
    camera_id = uuid4()
    starts_at = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(days=1)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/export",
            params=[
                ("camera_ids", str(camera_id)),
                ("class_names", "car"),
                ("granularity", "1d"),
                ("from", starts_at.isoformat()),
                ("to", ends_at.isoformat()),
                ("format", "csv"),
            ],
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert history.last_export == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_ids": [camera_id],
        "class_names": ["car"],
        "granularity": "1d",
        "starts_at": starts_at,
        "ends_at": ends_at,
        "format_name": "csv",
    }


@pytest.mark.asyncio
async def test_incidents_route_passes_camera_type_limit_and_review_status_filters() -> None:
    user = _sample_user()
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)
    camera_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.get(
            "/api/v1/incidents",
            params={
                "camera_id": str(camera_id),
                "type": "ppe-missing",
                "review_status": "pending",
                "limit": "25",
            },
        )

    assert response.status_code == 200
    assert response.json()[0]["type"] == "ppe-missing"
    assert response.json()[0]["clip_url"] == "https://minio.local/signed/incidents/1.mjpeg"
    assert response.json()[0]["storage_bytes"] == 2_097_152
    assert response.json()[0]["review_status"] == "pending"
    assert response.json()[0]["scene_contract_hash"] == "a" * 64
    assert response.json()[0]["privacy_manifest_hash"] == "b" * 64
    assert response.json()[0]["runtime_passport_hash"] == "e" * 64
    assert response.json()[0]["runtime_passport"]["selected_backend"] == "tensorrt_engine"
    assert response.json()[0]["runtime_passport"]["model_hash"] == "f" * 64
    assert response.json()[0]["trigger_rule"] == {
        "id": "99999999-9999-9999-9999-999999999111",
        "name": "Restricted person in server room",
        "incident_type": "restricted_person",
        "severity": "critical",
        "action": "record_clip",
        "cooldown_seconds": 45,
        "predicate": {
            "class_names": ["person"],
            "zone_ids": ["server-room"],
            "min_confidence": 0.82,
            "attributes": {"vest": "red"},
        },
        "rule_hash": "f" * 64,
    }
    assert response.json()[0]["recording_policy"]["storage_profile"] == "edge_local"
    assert response.json()[0]["evidence_artifacts"][0] == {
        "id": str(incidents.artifact_id),
        "incident_id": str(incidents.incident_id),
        "camera_id": response.json()[0]["evidence_artifacts"][0]["camera_id"],
        "kind": "event_clip",
        "status": "remote_available",
        "storage_provider": "s3_compatible",
        "storage_scope": "cloud",
        "bucket": "incidents",
        "object_key": "tenant/camera/clip.mjpeg",
        "content_type": "video/x-motion-jpeg",
        "sha256": "c" * 64,
        "size_bytes": 2_097_152,
        "clip_started_at": None,
        "triggered_at": None,
        "clip_ended_at": None,
        "duration_seconds": None,
        "fps": None,
        "scene_contract_hash": None,
        "privacy_manifest_hash": None,
        "review_url": "https://minio.local/signed/incidents/1.mjpeg",
        "sync_status": None,
        "sync_error": None,
    }
    assert response.json()[0]["ledger_summary"] == {
        "entry_count": 2,
        "latest_action": "evidence.clip.available",
        "latest_at": "2026-05-11T10:01:00Z",
    }
    assert incidents.last_query == {
        "tenant_id": UUID(str(user.tenant_context)),
        "camera_id": camera_id,
        "incident_type": "ppe-missing",
        "review_status": IncidentReviewStatus.PENDING,
        "limit": 25,
    }


@pytest.mark.asyncio
async def test_incident_accountability_detail_routes_call_service() -> None:
    user = _sample_user()
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)
    incident_id = uuid4()
    artifact_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        scene_response = await client.get(f"/api/v1/incidents/{incident_id}/scene-contract")
        privacy_response = await client.get(f"/api/v1/incidents/{incident_id}/privacy-manifest")
        runtime_response = await client.get(f"/api/v1/incidents/{incident_id}/runtime-passport")
        ledger_response = await client.get(f"/api/v1/incidents/{incident_id}/ledger")
        content_response = await client.get(
            f"/api/v1/incidents/{incident_id}/artifacts/{artifact_id}/content"
        )

    assert scene_response.status_code == 200
    assert scene_response.json()["contract_hash"] == "a" * 64
    assert privacy_response.status_code == 200
    assert privacy_response.json()["manifest_hash"] == "b" * 64
    assert runtime_response.status_code == 200
    assert runtime_response.json()["passport_hash"] == "e" * 64
    assert runtime_response.json()["summary"]["runtime_artifact_hash"] == "d" * 64
    assert runtime_response.json()["summary"]["runtime_selection_profile_hash"] == "g" * 64
    assert ledger_response.status_code == 200
    assert ledger_response.json()[0]["action"] == "incident.triggered"
    assert content_response.status_code == 307
    assert content_response.headers["location"] == ("https://minio.local/signed/incidents/1.mjpeg")
    assert incidents.scene_contract_calls == [
        {"tenant_id": UUID(str(user.tenant_context)), "incident_id": incident_id}
    ]
    assert incidents.privacy_manifest_calls == [
        {"tenant_id": UUID(str(user.tenant_context)), "incident_id": incident_id}
    ]
    assert incidents.runtime_passport_calls == [
        {"tenant_id": UUID(str(user.tenant_context)), "incident_id": incident_id}
    ]
    assert incidents.ledger_calls == [
        {"tenant_id": UUID(str(user.tenant_context)), "incident_id": incident_id}
    ]
    assert incidents.artifact_content_calls == [
        {
            "tenant_id": UUID(str(user.tenant_context)),
            "incident_id": incident_id,
            "artifact_id": artifact_id,
        }
    ]


@pytest.mark.asyncio
async def test_incident_review_route_requires_operator_and_calls_service() -> None:
    user = _sample_user(role=RoleEnum.OPERATOR)
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)
    incident_id = uuid4()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/v1/incidents/{incident_id}/review",
            json={"review_status": "reviewed"},
        )

    assert response.status_code == 200
    assert response.json()["id"] == str(incident_id)
    assert response.json()["review_status"] == "reviewed"
    assert response.json()["reviewed_by_subject"] == "user-1"
    assert incidents.review_calls == [
        {
            "tenant_id": UUID(str(user.tenant_context)),
            "incident_id": incident_id,
            "review_status": IncidentReviewStatus.REVIEWED,
            "subject": "user-1",
        }
    ]


@pytest.mark.asyncio
async def test_incident_review_route_rejects_viewer() -> None:
    user = _sample_user(role=RoleEnum.VIEWER)
    incidents = RecordingIncidentService()
    app = _create_test_app(user=user, history=RecordingHistoryService(), incidents=incidents)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        response = await client.patch(
            f"/api/v1/incidents/{uuid4()}/review",
            json={"review_status": "reviewed"},
        )

    assert response.status_code == 403
    assert incidents.review_calls == []
