from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import EvidenceRecordingPolicy
from argus.models.tables import SceneContractSnapshot

SCHEMA_VERSION = 1


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def hash_contract(contract: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(contract).encode("utf-8")).hexdigest()


def build_scene_contract(
    *,
    tenant_id: object,
    site_id: object,
    camera_id: object,
    camera_name: str,
    camera_source: Mapping[str, object],
    deployment_mode: str,
    model: Mapping[str, object],
    runtime_vocabulary: Mapping[str, object],
    runtime_selection: Mapping[str, object],
    vision_profile: Mapping[str, object],
    detection_regions: Sequence[Mapping[str, object]],
    candidate_quality: Mapping[str, object],
    recording_policy: EvidenceRecordingPolicy,
    privacy_manifest_hash: str,
    privacy_policy: Mapping[str, object] | None = None,
    incident_rules: Sequence[Mapping[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "site_id": str(site_id),
        "camera": {
            "id": str(camera_id),
            "name": camera_name,
            "source": dict(camera_source),
            "deployment_mode": deployment_mode,
        },
        "model": dict(model),
        "runtime_vocabulary": dict(runtime_vocabulary),
        "runtime_selection": dict(runtime_selection),
        "vision_profile": dict(vision_profile),
        "detection_regions": [dict(region) for region in detection_regions],
        "candidate_quality": dict(candidate_quality),
        "recording_policy": recording_policy.model_dump(mode="json"),
        "privacy_policy": dict(privacy_policy or {}),
        "incident_rules": [dict(rule) for rule in (incident_rules or [])],
        "privacy_manifest_hash": privacy_manifest_hash,
    }


class SceneContractService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_or_create_snapshot(
        self,
        *,
        tenant_id: UUID,
        camera_id: UUID,
        contract: Mapping[str, object],
    ) -> SceneContractSnapshot:
        contract_hash = hash_contract(contract)
        async with self.session_factory() as session:
            existing = await _load_snapshot_by_hash(session, contract_hash)
            if existing is not None:
                return existing

            snapshot = SceneContractSnapshot(
                tenant_id=tenant_id,
                camera_id=camera_id,
                schema_version=_schema_version(contract),
                contract_hash=contract_hash,
                contract=_json_safe_contract(contract),
            )
            session.add(snapshot)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await _load_snapshot_by_hash(session, contract_hash)
                if existing is not None:
                    return existing
                raise
            await session.refresh(snapshot)
            return snapshot


async def _load_snapshot_by_hash(
    session: AsyncSession,
    contract_hash: str,
) -> SceneContractSnapshot | None:
    statement = select(SceneContractSnapshot).where(
        SceneContractSnapshot.contract_hash == contract_hash
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _json_safe_contract(contract: Mapping[str, object]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(canonical_json(contract)))


def _schema_version(contract: Mapping[str, object]) -> int:
    schema_version = contract.get("schema_version", SCHEMA_VERSION)
    if isinstance(schema_version, int):
        return schema_version
    if isinstance(schema_version, str):
        return int(schema_version)
    return SCHEMA_VERSION
