from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    EvidenceRecordingPolicy,
    PrivacyPolicyProfileConfig,
    WorkerEvidenceStorageSettings,
    WorkerPrivacyPolicySettings,
)
from argus.compat import UTC
from argus.models.enums import (
    EvidenceArtifactStatus,
    EvidenceLedgerAction,
    OperatorConfigProfileKind,
)
from argus.models.tables import Camera, EvidenceArtifact, Incident, Site
from argus.services.evidence_ledger import EvidenceLedgerService
from argus.services.runtime_configuration import RuntimeOperatorConfig


class EvidenceLedgerWriter(Protocol):
    async def append_entry(
        self,
        *,
        tenant_id: UUID,
        incident_id: UUID,
        camera_id: UUID,
        action: EvidenceLedgerAction,
        actor_type: str,
        actor_subject: str | None = None,
        occurred_at: datetime | None = None,
        payload: Mapping[str, object] | None = None,
    ) -> Any: ...


def worker_privacy_policy_from_runtime_config(
    runtime_config: RuntimeOperatorConfig,
) -> WorkerPrivacyPolicySettings:
    if runtime_config.kind is not OperatorConfigProfileKind.PRIVACY_POLICY:
        raise ValueError("Runtime configuration is not a privacy policy profile.")
    config = PrivacyPolicyProfileConfig.model_validate(runtime_config.config)
    return WorkerPrivacyPolicySettings(
        profile_id=runtime_config.profile_id,
        profile_name=runtime_config.profile_name,
        profile_hash=runtime_config.profile_hash,
        retention_days=config.retention_days,
        storage_quota_bytes=config.storage_quota_bytes,
        plaintext_plate_storage=config.plaintext_plate_storage,
        residency=config.residency,
    )


def validate_privacy_policy_residency(
    *,
    privacy_policy: WorkerPrivacyPolicySettings | None,
    evidence_storage: WorkerEvidenceStorageSettings | None,
    recording_policy: EvidenceRecordingPolicy,
) -> None:
    if privacy_policy is None:
        return
    if not recording_policy.enabled:
        return
    expected = privacy_policy.residency
    actual = _storage_residency(
        evidence_storage=evidence_storage,
        recording_policy=recording_policy,
    )
    if expected != actual:
        raise ValueError(
            "Privacy policy residency does not match evidence storage residency: "
            f"{expected!r} != {actual!r}."
        )


class PrivacyPolicyRetentionService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        ledger: EvidenceLedgerWriter | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.ledger = ledger or EvidenceLedgerService(session_factory)

    async def mark_expired_artifacts(
        self,
        *,
        tenant_id: UUID,
        privacy_policy: WorkerPrivacyPolicySettings,
        now: datetime | None = None,
    ) -> int:
        current_time = now or datetime.now(tz=UTC)
        cutoff = current_time - timedelta(days=privacy_policy.retention_days)
        expired: list[tuple[EvidenceArtifact, Incident]] = []
        async with self.session_factory() as session:
            statement = (
                select(EvidenceArtifact, Incident)
                .join(Incident, Incident.id == EvidenceArtifact.incident_id)
                .join(Camera, Camera.id == EvidenceArtifact.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(Site.tenant_id == tenant_id)
                .where(EvidenceArtifact.status != EvidenceArtifactStatus.EXPIRED)
                .where(EvidenceArtifact.created_at <= cutoff)
            )
            rows = (await session.execute(statement)).all()
            for row in rows:
                artifact, incident = row[0], row[1]
                if getattr(artifact, "status", None) is EvidenceArtifactStatus.EXPIRED:
                    continue
                created_at = getattr(artifact, "created_at", None)
                if isinstance(created_at, datetime) and created_at > cutoff:
                    continue
                artifact.status = EvidenceArtifactStatus.EXPIRED
                expired.append((artifact, incident))
            if expired:
                await session.commit()

        for artifact, incident in expired:
            await self.ledger.append_entry(
                tenant_id=tenant_id,
                incident_id=incident.id,
                camera_id=incident.camera_id,
                action=EvidenceLedgerAction.EVIDENCE_EXPIRED,
                actor_type="system",
                actor_subject="privacy_retention",
                occurred_at=current_time,
                payload={
                    "artifact_id": str(artifact.id),
                    "retention_days": privacy_policy.retention_days,
                    "size_bytes": int(getattr(artifact, "size_bytes", 0) or 0),
                    "privacy_manifest_hash": getattr(
                        artifact,
                        "privacy_manifest_hash",
                        None,
                    ),
                },
            )
        return len(expired)


def _storage_residency(
    *,
    evidence_storage: WorkerEvidenceStorageSettings | None,
    recording_policy: EvidenceRecordingPolicy,
) -> str:
    if recording_policy.storage_profile == "local_first":
        return "local_first"
    if evidence_storage is not None:
        provider = _enum_value(evidence_storage.provider)
        if provider == "local_first":
            return "local_first"
        return _enum_value(evidence_storage.storage_scope)
    if recording_policy.storage_profile == "cloud":
        return "cloud"
    if recording_policy.storage_profile == "central":
        return "central"
    return "edge"


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value))
