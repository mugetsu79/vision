from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Protocol, cast
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    CameraUpdate,
    DetectionRegion,
    EvidenceRecordingPolicy,
    IncidentRuleCreate,
    IncidentRulePredicate,
    PolicyDraftCreate,
    PolicyDraftResponse,
    RuntimeVocabularyState,
    TenantContext,
)
from argus.compat import UTC
from argus.models.enums import (
    IncidentRuleSeverity,
    PolicyDraftLedgerAction,
    PolicyDraftStatus,
    RuleAction,
    RuntimeVocabularySource,
)
from argus.models.tables import (
    Camera,
    DetectionRule,
    PolicyDraft,
    PolicyDraftLedgerEntry,
    PrivacyManifestSnapshot,
    SceneContractSnapshot,
    Site,
)
from argus.services.incident_rules import normalize_incident_type, validate_incident_rule_payload
from argus.services.llm_provider_runtime import ResolvedLLMProviderSettings

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)


class LLMProviderResolver(Protocol):
    async def resolve_for_prompt(
        self,
        *,
        tenant_context: TenantContext,
        camera_id: UUID | None = None,
    ) -> ResolvedLLMProviderSettings: ...


class AuditLogger(Protocol):
    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None: ...


class CameraUpdateService(Protocol):
    async def update_camera(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: CameraUpdate,
    ) -> object: ...


class IncidentRuleCreateService(Protocol):
    async def create_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: IncidentRuleCreate,
    ) -> object: ...


class PolicyDraftLedgerRecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def append(
        self,
        *,
        tenant_context: TenantContext,
        draft_id: UUID,
        camera_id: UUID | None,
        action: PolicyDraftLedgerAction,
        payload: dict[str, Any],
    ) -> None:
        occurred_at = datetime.now(tz=UTC)
        async with self.session_factory() as session:
            previous = (
                await session.execute(
                    select(PolicyDraftLedgerEntry)
                    .where(
                        PolicyDraftLedgerEntry.tenant_id == tenant_context.tenant_id,
                        PolicyDraftLedgerEntry.policy_draft_id == draft_id,
                    )
                    .order_by(PolicyDraftLedgerEntry.sequence.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            sequence = 1 if previous is None else previous.sequence + 1
            previous_hash = previous.entry_hash if previous is not None else None
            entry_hash = build_policy_draft_ledger_hash(
                policy_draft_id=draft_id,
                sequence=sequence,
                action=action.value,
                actor_subject=tenant_context.user.subject,
                payload=payload,
                previous_entry_hash=previous_hash,
                occurred_at=occurred_at.isoformat(),
            )
            session.add(
                PolicyDraftLedgerEntry(
                    tenant_id=tenant_context.tenant_id,
                    policy_draft_id=draft_id,
                    camera_id=camera_id,
                    sequence=sequence,
                    action=action,
                    actor_subject=tenant_context.user.subject,
                    occurred_at=occurred_at,
                    payload=payload,
                    previous_entry_hash=previous_hash,
                    entry_hash=entry_hash,
                )
            )
            await session.commit()


@dataclass(frozen=True, slots=True)
class PolicyDraftState:
    id: UUID | None
    tenant_id: UUID
    camera_id: UUID | None
    status: PolicyDraftStatus
    prompt: str
    structured_diff: dict[str, Any]
    metadata: dict[str, Any]
    site_id: UUID | None = None
    created_by_subject: str | None = None
    approved_by_subject: str | None = None
    rejected_by_subject: str | None = None
    applied_by_subject: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    decided_at: datetime | None = None
    applied_at: datetime | None = None


class PolicyDraftCompiler:
    def __init__(self, llm_provider_resolver: LLMProviderResolver | None) -> None:
        self.llm_provider_resolver = llm_provider_resolver

    async def compile(
        self,
        *,
        tenant_context: TenantContext,
        camera_id: UUID,
        prompt: str,
        camera_state: dict[str, Any],
        use_llm: bool = True,
    ) -> PolicyDraftState:
        metadata: dict[str, Any] = {
            "parser": "deterministic-policy-fallback",
            "llm_provider": "keyword-fallback",
            "llm_model": "fallback",
            "llm_assistance": "disabled" if not use_llm else "fallback",
        }
        if use_llm and self.llm_provider_resolver is not None:
            resolved = await self.llm_provider_resolver.resolve_for_prompt(
                tenant_context=tenant_context,
                camera_id=camera_id,
            )
            metadata.update(
                {
                    "llm_provider": resolved.provider,
                    "llm_model": resolved.model,
                    "llm_profile_id": str(resolved.profile_id),
                    "llm_profile_name": resolved.profile_name,
                    "llm_profile_hash": resolved.profile_hash,
                    "llm_secret_state": resolved.secret_state
                    or _redacted_secret_state(resolved),
                    "llm_assistance": "profile_resolved",
                }
            )

        structured_diff = _deterministic_policy_diff(prompt, camera_state)
        return PolicyDraftState(
            id=None,
            tenant_id=tenant_context.tenant_id,
            camera_id=camera_id,
            site_id=_maybe_uuid(camera_state.get("site_id")),
            status=PolicyDraftStatus.DRAFT,
            prompt=prompt,
            structured_diff=structured_diff,
            metadata=metadata,
            created_by_subject=tenant_context.user.subject,
        )


class PolicyDraftService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: AuditLogger,
        *,
        llm_provider_resolver: LLMProviderResolver | None = None,
        camera_service: CameraUpdateService | None = None,
        incident_rule_service: IncidentRuleCreateService | None = None,
        ledger: PolicyDraftLedgerRecorder | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger
        self.compiler = PolicyDraftCompiler(llm_provider_resolver)
        self.camera_service = camera_service
        self.incident_rule_service = incident_rule_service
        self.ledger = ledger or PolicyDraftLedgerRecorder(session_factory)

    async def create_draft(
        self,
        tenant_context: TenantContext,
        payload: PolicyDraftCreate,
    ) -> PolicyDraftResponse:
        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context, payload.camera_id)
            camera_state = await _camera_state(session, tenant_context, camera)
            compiled = await self.compiler.compile(
                tenant_context=tenant_context,
                camera_id=payload.camera_id,
                prompt=payload.prompt,
                camera_state=camera_state,
                use_llm=payload.use_llm,
            )
            draft = PolicyDraft(
                tenant_id=tenant_context.tenant_id,
                camera_id=payload.camera_id,
                site_id=camera.site_id,
                status=PolicyDraftStatus.DRAFT,
                prompt=payload.prompt,
                structured_diff=compiled.structured_diff,
                draft_metadata=compiled.metadata,
                created_by_subject=tenant_context.user.subject,
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)

        await self._record_transition(
            tenant_context,
            PolicyDraftLedgerAction.PROPOSED,
            draft,
        )
        return _policy_draft_response(draft)

    async def get_draft(
        self,
        tenant_context: TenantContext,
        draft_id: UUID,
    ) -> PolicyDraftResponse:
        async with self.session_factory() as session:
            draft = await _load_draft(session, tenant_context, draft_id)
            return _policy_draft_response(draft)

    async def approve_draft(
        self,
        tenant_context: TenantContext,
        draft_id: UUID,
    ) -> PolicyDraftResponse:
        async with self.session_factory() as session:
            draft = await _load_draft(session, tenant_context, draft_id)
            _ensure_status(
                draft,
                PolicyDraftStatus.DRAFT,
                "Only draft policy drafts can be approved.",
            )
            draft.status = PolicyDraftStatus.APPROVED
            draft.approved_by_subject = tenant_context.user.subject
            draft.decided_at = datetime.now(tz=UTC)
            await session.commit()
            await session.refresh(draft)

        await self._record_transition(
            tenant_context,
            PolicyDraftLedgerAction.APPROVED,
            draft,
        )
        return _policy_draft_response(draft)

    async def reject_draft(
        self,
        tenant_context: TenantContext,
        draft_id: UUID,
    ) -> PolicyDraftResponse:
        async with self.session_factory() as session:
            draft = await _load_draft(session, tenant_context, draft_id)
            _ensure_status(
                draft,
                PolicyDraftStatus.DRAFT,
                "Only draft policy drafts can be rejected.",
            )
            draft.status = PolicyDraftStatus.REJECTED
            draft.rejected_by_subject = tenant_context.user.subject
            draft.decided_at = datetime.now(tz=UTC)
            await session.commit()
            await session.refresh(draft)

        await self._record_transition(
            tenant_context,
            PolicyDraftLedgerAction.REJECTED,
            draft,
        )
        return _policy_draft_response(draft)

    async def apply_draft(
        self,
        tenant_context: TenantContext,
        draft_id: UUID,
    ) -> PolicyDraftResponse:
        async with self.session_factory() as session:
            draft = await _load_draft(session, tenant_context, draft_id)
            _ensure_status(
                draft,
                PolicyDraftStatus.APPROVED,
                "Only approved policy drafts can be applied.",
            )
            camera_id = draft.camera_id
            structured_diff = dict(draft.structured_diff or {})
            if camera_id is not None:
                camera = await _load_camera(session, tenant_context, camera_id)
                current_state = await _camera_state(session, tenant_context, camera)
                try:
                    assert_policy_draft_baseline_current(structured_diff, current_state)
                    await _preflight_policy_rule_changes(
                        session,
                        tenant_context,
                        camera,
                        structured_diff,
                    )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=HTTP_422_UNPROCESSABLE,
                        detail=str(exc),
                    ) from exc

        if camera_id is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="Policy draft does not target a camera.",
            )
        await self._apply_camera_policy_diff(tenant_context, camera_id, structured_diff)

        async with self.session_factory() as session:
            draft = await _load_draft(session, tenant_context, draft_id)
            draft.status = PolicyDraftStatus.APPLIED
            draft.applied_by_subject = tenant_context.user.subject
            now = datetime.now(tz=UTC)
            draft.applied_at = now
            if draft.decided_at is None:
                draft.decided_at = now
            await session.commit()
            await session.refresh(draft)

        await self._record_transition(
            tenant_context,
            PolicyDraftLedgerAction.APPLIED,
            draft,
        )
        return _policy_draft_response(draft)

    async def _apply_camera_policy_diff(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        structured_diff: dict[str, Any],
    ) -> None:
        if self.camera_service is not None:
            update_payload = _camera_update_from_diff(structured_diff)
            if update_payload.model_fields_set:
                await self.camera_service.update_camera(tenant_context, camera_id, update_payload)
            if self.incident_rule_service is not None:
                for rule_payload in _incident_rules_from_diff(structured_diff):
                    await self.incident_rule_service.create_rule(
                        tenant_context,
                        camera_id,
                        rule_payload,
                    )
            return

        async with self.session_factory() as session:
            camera = await _load_camera(session, tenant_context, camera_id)
            camera_state = {
                "runtime_vocabulary": list(camera.runtime_vocabulary or []),
                "recording_policy": camera.evidence_recording_policy or {},
                "detection_regions": list(camera.detection_regions or []),
                "incident_rules": [],
            }
            applied = apply_policy_draft(
                PolicyDraftState(
                    id=None,
                    tenant_id=tenant_context.tenant_id,
                    camera_id=camera_id,
                    status=PolicyDraftStatus.APPROVED,
                    prompt="",
                    structured_diff=structured_diff,
                    metadata={},
                ),
                camera_state=camera_state,
            )
            if applied.status is PolicyDraftStatus.APPLIED:
                camera.runtime_vocabulary = cast(
                    list[str],
                    camera_state["runtime_vocabulary"],
                )
                camera.evidence_recording_policy = cast(
                    dict[str, Any] | None,
                    camera_state.get("recording_policy"),
                )
                camera.detection_regions = cast(
                    list[dict[str, Any]],
                    camera_state.get("detection_regions") or [],
                )
            await session.commit()

    async def _record_transition(
        self,
        tenant_context: TenantContext,
        action: PolicyDraftLedgerAction,
        draft: PolicyDraft,
    ) -> None:
        payload = _transition_payload(draft)
        await self._record_audit(tenant_context, action.value, draft, payload)
        await self.ledger.append(
            tenant_context=tenant_context,
            draft_id=draft.id,
            camera_id=draft.camera_id,
            action=action,
            payload=payload,
        )

    async def _record_audit(
        self,
        tenant_context: TenantContext,
        action: str,
        draft: PolicyDraft,
        payload: dict[str, Any],
    ) -> None:
        await self.audit_logger.record(
            tenant_context=tenant_context,
            action=action,
            target=f"policy_draft:{draft.id}",
            meta=payload,
        )


def approve_policy_draft(
    draft: PolicyDraftState,
    *,
    actor_subject: str,
) -> PolicyDraftState:
    if draft.status is not PolicyDraftStatus.DRAFT:
        raise ValueError("Only draft policy drafts can be approved.")
    return replace(
        draft,
        status=PolicyDraftStatus.APPROVED,
        approved_by_subject=actor_subject,
        decided_at=datetime.now(tz=UTC),
    )


def reject_policy_draft(
    draft: PolicyDraftState,
    *,
    actor_subject: str,
) -> PolicyDraftState:
    if draft.status is not PolicyDraftStatus.DRAFT:
        raise ValueError("Only draft policy drafts can be rejected.")
    return replace(
        draft,
        status=PolicyDraftStatus.REJECTED,
        rejected_by_subject=actor_subject,
        decided_at=datetime.now(tz=UTC),
    )


def apply_policy_draft(
    draft: PolicyDraftState,
    *,
    camera_state: dict[str, Any],
    actor_subject: str | None = None,
) -> PolicyDraftState:
    if draft.status is not PolicyDraftStatus.APPROVED:
        raise ValueError("Policy draft must be approved before it can be applied.")
    diff = dict(draft.structured_diff or {})
    vocabulary_diff = dict(diff.get("runtime_vocabulary") or {})
    vocabulary_terms = _extract_runtime_vocabulary(camera_state)
    for term in vocabulary_diff.get("add") or []:
        normalized = _normalize_term(str(term))
        if normalized and normalized not in vocabulary_terms:
            vocabulary_terms.append(normalized)
    if "after" in vocabulary_diff:
        vocabulary_terms = _normalize_terms(vocabulary_diff["after"])
    camera_state["runtime_vocabulary"] = vocabulary_terms

    recording_diff = dict(diff.get("recording_policy") or {})
    if "after" in recording_diff:
        camera_state["recording_policy"] = recording_diff["after"]

    detection_diff = dict(diff.get("detection_regions") or {})
    detection_regions = list(camera_state.get("detection_regions") or [])
    for region in detection_diff.get("add") or []:
        if isinstance(region, dict) and region.get("id") not in {
            existing.get("id") for existing in detection_regions if isinstance(existing, dict)
        }:
            detection_regions.append(region)
    if "after" in detection_diff:
        detection_regions = list(detection_diff["after"] or [])
    camera_state["detection_regions"] = detection_regions

    rule_changes = list(diff.get("rule_changes") or [])
    if rule_changes:
        camera_state["incident_rules"] = [
            *(camera_state.get("incident_rules") or []),
            *rule_changes,
        ]

    return replace(
        draft,
        status=PolicyDraftStatus.APPLIED,
        applied_by_subject=actor_subject,
        applied_at=datetime.now(tz=UTC),
    )


def assert_policy_draft_baseline_current(
    structured_diff: dict[str, Any],
    camera_state: dict[str, Any],
) -> None:
    diff_scene_hash = structured_diff.get("scene_contract_hash")
    current_scene_hash = camera_state.get("scene_contract_hash")
    if diff_scene_hash and current_scene_hash and diff_scene_hash != current_scene_hash:
        raise ValueError("Policy draft is stale because the scene contract changed.")

    diff_privacy_hash = structured_diff.get("privacy_manifest_hash")
    current_privacy_hash = camera_state.get("privacy_manifest_hash")
    if diff_privacy_hash and current_privacy_hash and diff_privacy_hash != current_privacy_hash:
        raise ValueError("Policy draft is stale because the privacy manifest changed.")

    vocabulary_diff = dict(structured_diff.get("runtime_vocabulary") or {})
    if "before" in vocabulary_diff and _normalize_terms(vocabulary_diff["before"]) != (
        _extract_runtime_vocabulary(camera_state)
    ):
        raise ValueError("Policy draft is stale because runtime vocabulary changed.")

    recording_diff = dict(structured_diff.get("recording_policy") or {})
    if "before" in recording_diff and _canonical_json(recording_diff["before"]) != (
        _canonical_json(camera_state.get("recording_policy") or {})
    ):
        raise ValueError("Policy draft is stale because recording policy changed.")

    region_diff = dict(structured_diff.get("detection_regions") or {})
    if "before" in region_diff and _canonical_json(region_diff["before"]) != (
        _canonical_json(camera_state.get("detection_regions") or [])
    ):
        raise ValueError("Policy draft is stale because detection regions changed.")


def build_policy_draft_ledger_hash(
    *,
    policy_draft_id: UUID,
    sequence: int,
    action: str,
    actor_subject: str | None,
    payload: dict[str, Any],
    previous_entry_hash: str | None,
    occurred_at: str,
) -> str:
    canonical = json.dumps(
        {
            "policy_draft_id": str(policy_draft_id),
            "sequence": sequence,
            "action": action,
            "actor_subject": actor_subject,
            "payload": payload,
            "previous_entry_hash": previous_entry_hash,
            "occurred_at": occurred_at,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _load_camera(
    session: AsyncSession,
    tenant_context: TenantContext,
    camera_id: UUID,
) -> Camera:
    statement = (
        select(Camera)
        .join(Site, Site.id == Camera.site_id)
        .where(Camera.id == camera_id, Site.tenant_id == tenant_context.tenant_id)
    )
    camera = (await session.execute(statement)).scalar_one_or_none()
    if camera is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camera not found.")
    return camera


async def _load_draft(
    session: AsyncSession,
    tenant_context: TenantContext,
    draft_id: UUID,
) -> PolicyDraft:
    statement = select(PolicyDraft).where(
        PolicyDraft.id == draft_id,
        PolicyDraft.tenant_id == tenant_context.tenant_id,
    )
    draft = (await session.execute(statement)).scalar_one_or_none()
    if draft is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy draft not found.",
        )
    return draft


async def _camera_state(
    session: AsyncSession,
    tenant_context: TenantContext,
    camera: Camera,
) -> dict[str, Any]:
    scene_hash = (
        await session.execute(
            select(SceneContractSnapshot.contract_hash)
            .where(
                SceneContractSnapshot.tenant_id == tenant_context.tenant_id,
                SceneContractSnapshot.camera_id == camera.id,
            )
            .order_by(SceneContractSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    privacy_hash = (
        await session.execute(
            select(PrivacyManifestSnapshot.manifest_hash)
            .where(
                PrivacyManifestSnapshot.tenant_id == tenant_context.tenant_id,
                PrivacyManifestSnapshot.camera_id == camera.id,
            )
            .order_by(PrivacyManifestSnapshot.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "site_id": camera.site_id,
        "scene_contract_hash": scene_hash,
        "privacy_manifest_hash": privacy_hash,
        "runtime_vocabulary": list(camera.runtime_vocabulary or []),
        "active_classes": list(camera.active_classes or []),
        "recording_policy": camera.evidence_recording_policy or {},
        "detection_regions": list(camera.detection_regions or []),
        "privacy": dict(camera.privacy or {}),
        "incident_rules": [],
    }


async def _preflight_policy_rule_changes(
    session: AsyncSession,
    tenant_context: TenantContext,
    camera: Camera,
    structured_diff: dict[str, Any],
) -> None:
    rules = _incident_rules_from_diff(structured_diff)
    if not rules:
        return

    available_classes = set(_clean_strings(camera.active_classes or []))
    vocabulary_diff = dict(structured_diff.get("runtime_vocabulary") or {})
    available_classes.update(_clean_strings(camera.runtime_vocabulary or []))
    available_classes.update(_normalize_terms(vocabulary_diff.get("after") or []))
    available_classes.update(_normalize_terms(vocabulary_diff.get("add") or []))

    available_zone_ids = _camera_zone_ids(camera)
    detection_diff = dict(structured_diff.get("detection_regions") or {})
    for region in detection_diff.get("add") or []:
        if isinstance(region, dict) and isinstance(region.get("id"), str):
            available_zone_ids.add(str(region["id"]).strip())
    for region in detection_diff.get("after") or []:
        if isinstance(region, dict) and isinstance(region.get("id"), str):
            available_zone_ids.add(str(region["id"]).strip())

    supported_attributes = _camera_supported_attributes(camera)
    for rule in rules:
        validate_incident_rule_payload(
            rule,
            available_classes=available_classes,
            available_zone_ids=available_zone_ids,
            supported_attributes=supported_attributes,
        )
        normalized_type = normalize_incident_type(rule.incident_type or rule.name)
        existing = (
            await session.execute(
                select(DetectionRule).where(
                    DetectionRule.camera_id == camera.id,
                    (DetectionRule.name == rule.name)
                    | (DetectionRule.incident_type == normalized_type),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise ValueError(
                "Policy draft is stale because an incident rule with the same "
                "name or incident type already exists."
            )


def _policy_draft_response(draft: PolicyDraft) -> PolicyDraftResponse:
    return PolicyDraftResponse(
        id=draft.id,
        tenant_id=draft.tenant_id,
        camera_id=draft.camera_id,
        site_id=draft.site_id,
        status=draft.status,
        prompt=draft.prompt,
        structured_diff=dict(draft.structured_diff or {}),
        metadata=dict(draft.draft_metadata or {}),
        created_by_subject=draft.created_by_subject,
        approved_by_subject=draft.approved_by_subject,
        rejected_by_subject=draft.rejected_by_subject,
        applied_by_subject=draft.applied_by_subject,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        decided_at=draft.decided_at,
        applied_at=draft.applied_at,
    )


def _deterministic_policy_diff(prompt: str, camera_state: dict[str, Any]) -> dict[str, Any]:
    prompt_text = prompt.lower()
    current_terms = _extract_runtime_vocabulary(camera_state)
    detected_terms = _prompt_terms(prompt_text)
    added_terms = [term for term in detected_terms if term not in current_terms]
    proposed_terms = [*current_terms, *added_terms]

    current_recording = dict(camera_state.get("recording_policy") or {})
    recording_after = dict(current_recording)
    if _mentions_recording(prompt_text):
        recording_after.update({"enabled": True, "mode": "event_clip"})

    current_regions = list(camera_state.get("detection_regions") or [])
    zone_ids = _prompt_zone_ids(prompt_text)
    region_additions = [
        _region_for_zone(zone_id, class_names=proposed_terms or detected_terms)
        for zone_id in zone_ids
        if zone_id not in {
            str(region.get("id"))
            for region in current_regions
            if isinstance(region, dict) and region.get("id") is not None
        }
    ]
    proposed_regions = [*current_regions, *region_additions]
    rule_changes = _rule_changes(prompt_text, detected_terms, zone_ids)

    return {
        "scene_contract_hash": camera_state.get("scene_contract_hash"),
        "privacy_manifest_hash": camera_state.get("privacy_manifest_hash"),
        "scene_contract": {
            "current_hash": camera_state.get("scene_contract_hash"),
            "after": {
                "runtime_vocabulary": proposed_terms,
                "detection_regions": proposed_regions,
                "incident_rules": rule_changes,
            },
        },
        "privacy_manifest": {
            "current_hash": camera_state.get("privacy_manifest_hash"),
            "after": dict(camera_state.get("privacy") or {}),
        },
        "recording_policy": {
            "before": current_recording,
            "after": recording_after,
        },
        "runtime_vocabulary": {
            "before": current_terms,
            "add": added_terms,
            "after": proposed_terms,
        },
        "detection_regions": {
            "before": current_regions,
            "add": region_additions,
            "after": proposed_regions,
        },
        "incident_rules": {"add": rule_changes},
        "rule_changes": rule_changes,
    }


def _camera_update_from_diff(diff: dict[str, Any]) -> CameraUpdate:
    payload: dict[str, Any] = {}
    vocabulary_diff = dict(diff.get("runtime_vocabulary") or {})
    if "after" in vocabulary_diff:
        payload["runtime_vocabulary"] = RuntimeVocabularyState(
            terms=_normalize_terms(vocabulary_diff["after"]),
            source=RuntimeVocabularySource.MANUAL,
        )

    recording_diff = dict(diff.get("recording_policy") or {})
    if "after" in recording_diff:
        payload["recording_policy"] = EvidenceRecordingPolicy.model_validate(
            recording_diff["after"]
        )

    detection_diff = dict(diff.get("detection_regions") or {})
    if "after" in detection_diff:
        payload["detection_regions"] = [
            DetectionRegion.model_validate(region) for region in detection_diff["after"] or []
        ]

    return CameraUpdate(**payload)


def _incident_rules_from_diff(diff: dict[str, Any]) -> list[IncidentRuleCreate]:
    incident_rules_diff = dict(diff.get("incident_rules") or {})
    raw_rules = list(diff.get("rule_changes") or incident_rules_diff.get("add") or [])
    rules: list[IncidentRuleCreate] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            continue
        predicate = dict(raw_rule.get("predicate") or {})
        name = raw_rule.get("name") or raw_rule.get("incident_type") or "Policy draft rule"
        incident_type = (
            raw_rule.get("incident_type")
            or raw_rule.get("name")
            or "policy_draft_rule"
        )
        severity = raw_rule.get("severity") or IncidentRuleSeverity.WARNING.value
        rules.append(
            IncidentRuleCreate(
                name=str(name),
                incident_type=str(incident_type),
                severity=IncidentRuleSeverity(str(severity)),
                predicate=IncidentRulePredicate.model_validate(predicate),
                action=RuleAction(str(raw_rule.get("action") or RuleAction.RECORD_CLIP.value)),
                cooldown_seconds=int(raw_rule.get("cooldown_seconds") or 60),
            )
        )
    return rules


def _rule_changes(
    prompt_text: str,
    terms: list[str],
    zone_ids: list[str],
) -> list[dict[str, Any]]:
    if not terms and not any(
        token in prompt_text for token in ("rule", "incident", "alert", "record")
    ):
        return []
    class_names = terms or ["person"]
    primary_term = class_names[0]
    if primary_term == "hardhat":
        incident_type = "hardhat_required"
        class_names = ["person"]
        attributes: dict[str, object] = {"hardhat": False}
    else:
        incident_type = f"{primary_term}_activity"
        attributes = {}
    return [
        {
            "name": incident_type.replace("_", " ").title(),
            "incident_type": incident_type,
            "severity": IncidentRuleSeverity.WARNING.value,
            "predicate": {
                "class_names": class_names,
                "zone_ids": zone_ids,
                "min_confidence": 0.5,
                "attributes": attributes,
            },
            "action": RuleAction.RECORD_CLIP.value
            if _mentions_recording(prompt_text)
            else RuleAction.ALERT.value,
            "cooldown_seconds": 60,
        }
    ]


def _prompt_terms(prompt_text: str) -> list[str]:
    terms_by_keyword = {
        "forklift": "forklift",
        "forklifts": "forklift",
        "hardhat": "hardhat",
        "hardhats": "hardhat",
        "helmet": "hardhat",
        "helmets": "hardhat",
        "person": "person",
        "people": "person",
        "truck": "truck",
        "trucks": "truck",
        "pallet jack": "pallet_jack",
        "pallet jacks": "pallet_jack",
    }
    found: list[str] = []
    for keyword, term in terms_by_keyword.items():
        if _has_keyword(prompt_text, keyword) and term not in found:
            found.append(term)
    return found


def _prompt_zone_ids(prompt_text: str) -> list[str]:
    zones_by_keyword = {
        "dock": "dock",
        "loading bay": "loading-bay",
        "restricted": "restricted",
        "server room": "server-room",
        "warehouse": "warehouse",
    }
    zones: list[str] = []
    for keyword, zone_id in zones_by_keyword.items():
        if _has_keyword(prompt_text, keyword) and zone_id not in zones:
            zones.append(zone_id)
    return zones


def _region_for_zone(zone_id: str, *, class_names: list[str]) -> dict[str, Any]:
    return {
        "id": zone_id,
        "mode": "include",
        "polygon": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        "class_names": class_names,
        "points_normalized": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    }


def _mentions_recording(prompt_text: str) -> bool:
    return any(token in prompt_text for token in ("record", "clip", "capture evidence"))


def _extract_runtime_vocabulary(camera_state: dict[str, Any]) -> list[str]:
    raw = camera_state.get("runtime_vocabulary") or []
    if isinstance(raw, RuntimeVocabularyState):
        return _normalize_terms(raw.terms)
    if isinstance(raw, dict):
        return _normalize_terms(raw.get("terms") or [])
    return _normalize_terms(raw)


def _normalize_terms(raw_terms: object) -> list[str]:
    if not isinstance(raw_terms, list | tuple | set):
        return []
    terms: list[str] = []
    for raw_term in raw_terms:
        normalized = _normalize_term(str(raw_term))
        if normalized and normalized not in terms:
            terms.append(normalized)
    return terms


def _clean_strings(values: object) -> list[str]:
    if not isinstance(values, list | tuple | set):
        return []
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _normalize_term(term: str) -> str:
    return re.sub(r"[^a-z0-9_ -]+", "", term.strip().lower()).replace(" ", "_")


def _has_keyword(prompt_text: str, keyword: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", prompt_text) is not None


def _camera_zone_ids(camera: Camera) -> set[str]:
    zone_ids: set[str] = set()
    for source in (camera.zones or [], camera.detection_regions or []):
        for zone in source:
            if isinstance(zone, dict) and isinstance(zone.get("id"), str):
                zone_id = str(zone["id"]).strip()
                if zone_id:
                    zone_ids.add(zone_id)
    return zone_ids


def _camera_supported_attributes(camera: Camera) -> set[str]:
    attributes = {
        "direction",
        "hardhat",
        "helmet",
        "hi_vis",
        "ppe",
        "vest",
        "vehicle_color",
    }
    for rule in camera.attribute_rules or []:
        if not isinstance(rule, dict):
            continue
        for key in ("attribute", "attribute_name", "key", "name", "id"):
            value = rule.get(key)
            if isinstance(value, str) and value.strip():
                attributes.add(value.strip())
    return attributes - {
        "biometric_id",
        "face_embedding",
        "face_id",
        "license_plate_plaintext",
        "person_id",
    }


def _redacted_secret_state(resolved: ResolvedLLMProviderSettings) -> dict[str, object]:
    return {
        "api_key": "present"
        if resolved.api_key
        else ("missing" if resolved.api_key_required else "not_required"),
        "api_key_required": resolved.api_key_required,
    }


def _transition_payload(draft: PolicyDraft) -> dict[str, Any]:
    return {
        "draft_id": str(draft.id),
        "camera_id": str(draft.camera_id) if draft.camera_id is not None else None,
        "site_id": str(draft.site_id) if draft.site_id is not None else None,
        "status": draft.status.value,
        "metadata": dict(draft.draft_metadata or {}),
    }


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _ensure_status(draft: PolicyDraft, expected: PolicyDraftStatus, detail: str) -> None:
    if draft.status is not expected:
        raise HTTPException(status_code=HTTP_422_UNPROCESSABLE, detail=detail)


def _maybe_uuid(value: object) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None
