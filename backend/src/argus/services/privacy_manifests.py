from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    EvidenceRecordingPolicy,
    EvidenceStorageProfile,
    WorkerPrivacyPolicySettings,
)
from argus.models.tables import PrivacyManifestSnapshot

SCHEMA_VERSION = 1


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def hash_manifest(manifest: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(manifest).encode("utf-8")).hexdigest()


def build_privacy_manifest(
    *,
    tenant_id: UUID,
    camera_id: UUID,
    deployment_mode: str,
    recording_policy: EvidenceRecordingPolicy,
    allow_plaintext_plates: bool,
    plaintext_justification: str | None,
    privacy_policy: WorkerPrivacyPolicySettings | None = None,
) -> dict[str, object]:
    plaintext_allowed = (
        privacy_policy.plaintext_plate_storage == "allowed"
        if privacy_policy is not None
        else allow_plaintext_plates
    )
    resolved_plaintext_justification = _plaintext_justification(
        plaintext_allowed=plaintext_allowed,
        plaintext_justification=plaintext_justification,
        privacy_policy=privacy_policy,
    )
    residency = (
        privacy_policy.residency
        if privacy_policy is not None
        else _residency_for_storage_profile(recording_policy.storage_profile)
    )
    storage_payload: dict[str, object] = {
        "residency": residency,
        "profile": recording_policy.storage_profile,
    }
    if privacy_policy is not None:
        storage_payload["quota_bytes"] = privacy_policy.storage_quota_bytes
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "camera_id": str(camera_id),
        "deployment_mode": deployment_mode,
        "identity": {
            "face_identification": "disabled",
            "biometric_identification": "disabled",
        },
        "plates": {
            "plaintext_storage": "allowed" if plaintext_allowed else "blocked",
            "plaintext_justification": resolved_plaintext_justification,
        },
        "recording": recording_policy.model_dump(mode="json"),
        "storage": storage_payload,
        "retention": (
            {"days": privacy_policy.retention_days}
            if privacy_policy is not None
            else {"days": None}
        ),
        "privacy_policy": _privacy_policy_manifest_payload(privacy_policy),
        "review": {
            "human_review_required": True,
        },
    }


class PrivacyManifestService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_or_create_snapshot(
        self,
        *,
        tenant_id: UUID,
        camera_id: UUID,
        manifest: Mapping[str, object],
    ) -> PrivacyManifestSnapshot:
        manifest_hash = hash_manifest(manifest)
        async with self.session_factory() as session:
            existing = await _load_snapshot_by_hash(session, manifest_hash)
            if existing is not None:
                return existing

            snapshot = PrivacyManifestSnapshot(
                tenant_id=tenant_id,
                camera_id=camera_id,
                schema_version=_schema_version(manifest),
                manifest_hash=manifest_hash,
                manifest=_json_safe_manifest(manifest),
            )
            session.add(snapshot)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await _load_snapshot_by_hash(session, manifest_hash)
                if existing is not None:
                    return existing
                raise
            await session.refresh(snapshot)
            return snapshot


async def _load_snapshot_by_hash(
    session: AsyncSession,
    manifest_hash: str,
) -> PrivacyManifestSnapshot | None:
    statement = select(PrivacyManifestSnapshot).where(
        PrivacyManifestSnapshot.manifest_hash == manifest_hash
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _residency_for_storage_profile(profile: EvidenceStorageProfile) -> str:
    if profile == "cloud":
        return "cloud"
    if profile == "central":
        return "central"
    return "edge"


def _privacy_policy_manifest_payload(
    privacy_policy: WorkerPrivacyPolicySettings | None,
) -> dict[str, object | None]:
    if privacy_policy is None:
        return {
            "profile_id": None,
            "profile_name": None,
            "profile_hash": None,
        }
    return {
        "profile_id": str(privacy_policy.profile_id)
        if privacy_policy.profile_id is not None
        else None,
        "profile_name": privacy_policy.profile_name,
        "profile_hash": privacy_policy.profile_hash,
    }


def _plaintext_justification(
    *,
    plaintext_allowed: bool,
    plaintext_justification: str | None,
    privacy_policy: WorkerPrivacyPolicySettings | None,
) -> str | None:
    if not plaintext_allowed:
        return None
    if plaintext_justification:
        return plaintext_justification
    if privacy_policy is not None:
        return "Privacy policy profile allows plaintext plate storage."
    return None


def _json_safe_manifest(manifest: Mapping[str, object]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(canonical_json(manifest)))


def _schema_version(manifest: Mapping[str, object]) -> int:
    schema_version = manifest.get("schema_version", SCHEMA_VERSION)
    if isinstance(schema_version, int):
        return schema_version
    if isinstance(schema_version, str):
        return int(schema_version)
    return SCHEMA_VERSION
