from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from enum import Enum
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.models.tables import RuntimePassportSnapshot

SCHEMA_VERSION = 1


def canonical_json(value: object) -> str:
    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def hash_runtime_passport(passport: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(passport).encode("utf-8")).hexdigest()


def build_runtime_passport(
    *,
    tenant_id: object,
    camera_id: object,
    scene_contract_hash: str,
    model_metadata: Mapping[str, object],
    runtime_selection: Mapping[str, object] | None = None,
    runtime_artifact: Mapping[str, object] | None = None,
    selection_report: Mapping[str, object] | None = None,
    provider_versions: Mapping[str, object] | None = None,
    scene_vocabulary_hash: str | None = None,
) -> dict[str, object]:
    runtime_selection_payload = _json_safe(dict(runtime_selection or {}))
    artifact_payload = (
        cast(dict[str, object], _json_safe(dict(runtime_artifact)))
        if runtime_artifact is not None
        else None
    )
    selection_report_payload = cast(
        dict[str, object],
        _json_safe(dict(selection_report or {})),
    )
    model_payload = _model_payload(model_metadata)
    selected_runtime = _selected_runtime_payload(
        model=model_payload,
        runtime_selection=cast(dict[str, object], runtime_selection_payload),
        runtime_artifact=artifact_payload,
        selection_report=selection_report_payload,
        scene_vocabulary_hash=scene_vocabulary_hash,
    )
    return cast(
        dict[str, object],
        _json_safe(
            {
                "schema_version": SCHEMA_VERSION,
                "tenant_id": tenant_id,
                "camera_id": camera_id,
                "scene_contract_hash": scene_contract_hash,
                "model": model_payload,
                "runtime_selection_profile": _runtime_selection_profile(
                    cast(dict[str, object], runtime_selection_payload)
                ),
                "selected_runtime": selected_runtime,
                "provider_versions": dict(provider_versions or {})
                or _artifact_runtime_versions(artifact_payload),
            }
        ),
    )


class RuntimePassportService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def get_or_create_snapshot(
        self,
        *,
        tenant_id: UUID,
        camera_id: UUID,
        passport: Mapping[str, object],
        incident_id: UUID | None = None,
    ) -> RuntimePassportSnapshot:
        passport_hash = hash_runtime_passport(passport)
        async with self.session_factory() as session:
            existing = await _load_snapshot_by_hash(session, passport_hash)
            if existing is not None:
                return existing

            snapshot = RuntimePassportSnapshot(
                tenant_id=tenant_id,
                camera_id=camera_id,
                incident_id=incident_id,
                schema_version=_schema_version(passport),
                passport_hash=passport_hash,
                passport=_json_safe_passport(passport),
            )
            session.add(snapshot)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await _load_snapshot_by_hash(session, passport_hash)
                if existing is not None:
                    return existing
                raise
            await session.refresh(snapshot)
            return snapshot


async def _load_snapshot_by_hash(
    session: AsyncSession,
    passport_hash: str,
) -> RuntimePassportSnapshot | None:
    statement = select(RuntimePassportSnapshot).where(
        RuntimePassportSnapshot.passport_hash == passport_hash
    )
    return (await session.execute(statement)).scalar_one_or_none()


def _selected_runtime_payload(
    *,
    model: Mapping[str, object],
    runtime_selection: Mapping[str, object],
    runtime_artifact: Mapping[str, object] | None,
    selection_report: Mapping[str, object],
    scene_vocabulary_hash: str | None,
) -> dict[str, object | None]:
    fallback_reason = _first_present(
        selection_report,
        runtime_selection,
        keys=("fallback_reason",),
    )
    selected_backend = _first_present(
        selection_report,
        runtime_selection,
        model,
        keys=("selected_backend", "backend", "preferred_backend", "runtime_backend"),
    )
    if runtime_artifact is not None:
        selected_backend = selected_backend or runtime_artifact.get("runtime_backend")
    fallback = bool(selection_report.get("fallback", runtime_artifact is None and fallback_reason))
    return {
        "backend": selected_backend,
        "fallback": fallback,
        "fallback_reason": fallback_reason,
        "runtime_artifact_id": _artifact_value(runtime_artifact, "id"),
        "runtime_artifact_kind": _artifact_value(runtime_artifact, "kind"),
        "runtime_artifact_hash": _artifact_value(runtime_artifact, "sha256"),
        "source_model_sha256": _artifact_value(runtime_artifact, "source_model_sha256"),
        "target_profile": _artifact_value(runtime_artifact, "target_profile")
        or runtime_selection.get("target_profile"),
        "precision": _artifact_value(runtime_artifact, "precision")
        or runtime_selection.get("precision"),
        "scene_vocabulary_hash": scene_vocabulary_hash
        or _artifact_value(runtime_artifact, "vocabulary_hash"),
        "vocabulary_hash": _artifact_value(runtime_artifact, "vocabulary_hash"),
        "vocabulary_version": _artifact_value(runtime_artifact, "vocabulary_version"),
        "validation_status": _artifact_value(runtime_artifact, "validation_status"),
        "validated_at": _artifact_value(runtime_artifact, "validated_at"),
    }


def _model_payload(model_metadata: Mapping[str, object]) -> dict[str, object | None]:
    model = cast(dict[str, object], _json_safe(dict(model_metadata)))
    return {
        "id": model.get("id"),
        "name": model.get("name"),
        "version": model.get("version"),
        "sha256": model.get("sha256"),
        "capability": model.get("capability"),
        "runtime_backend": model.get("runtime_backend"),
    }


def _runtime_selection_profile(
    runtime_selection: Mapping[str, object],
) -> dict[str, object | None]:
    return {
        "profile_id": runtime_selection.get("profile_id"),
        "profile_name": runtime_selection.get("profile_name"),
        "profile_hash": runtime_selection.get("profile_hash"),
        "artifact_preference": runtime_selection.get("artifact_preference"),
        "fallback_allowed": runtime_selection.get("fallback_allowed"),
        "preferred_backend": runtime_selection.get("preferred_backend")
        or runtime_selection.get("backend"),
    }


def _artifact_runtime_versions(
    runtime_artifact: Mapping[str, object] | None,
) -> dict[str, object]:
    if runtime_artifact is None:
        return {}
    versions = runtime_artifact.get("runtime_versions")
    if isinstance(versions, Mapping):
        return cast(dict[str, object], dict(versions))
    return {}


def _artifact_value(
    runtime_artifact: Mapping[str, object] | None,
    key: str,
) -> object | None:
    if runtime_artifact is None:
        return None
    return runtime_artifact.get(key)


def _first_present(*payloads: Mapping[str, object], keys: Sequence[str]) -> object | None:
    for key in keys:
        for payload in payloads:
            value = payload.get(key)
            if value is not None:
                return value
    return None


def _json_safe_passport(passport: Mapping[str, object]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(canonical_json(passport)))


def _schema_version(passport: Mapping[str, object]) -> int:
    schema_version = passport.get("schema_version", SCHEMA_VERSION)
    if isinstance(schema_version, int):
        return schema_version
    if isinstance(schema_version, str):
        return int(schema_version)
    return SCHEMA_VERSION


def _json_safe(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_json_safe(item) for item in value]
    return value
