from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import EvidenceRecordingPolicy, EvidenceStorageProfile
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
) -> dict[str, object]:
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
            "plaintext_storage": "allowed" if allow_plaintext_plates else "blocked",
            "plaintext_justification": plaintext_justification,
        },
        "recording": recording_policy.model_dump(mode="json"),
        "storage": {
            "residency": _residency_for_storage_profile(recording_policy.storage_profile),
            "profile": recording_policy.storage_profile,
        },
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
                schema_version=int(manifest.get("schema_version", SCHEMA_VERSION)),
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


def _json_safe_manifest(manifest: Mapping[str, object]) -> dict[str, Any]:
    return json.loads(canonical_json(manifest))
