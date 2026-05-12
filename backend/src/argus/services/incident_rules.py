from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterable
from typing import Any, Protocol
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.api.contracts import (
    CameraCommandPayload,
    IncidentRuleCreate,
    IncidentRulePredicate,
    IncidentRuleResponse,
    IncidentRuleUpdate,
    IncidentRuleValidationRequest,
    IncidentRuleValidationResponse,
    TenantContext,
    WorkerIncidentRule,
    WorkerIncidentRulePredicate,
)
from argus.models.tables import Camera, DetectionRule, Site

HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)

_NON_SLUG_CHARS = re.compile(r"[^a-z0-9]+")
_KNOWN_SAFE_ATTRIBUTES = {
    "direction",
    "hardhat",
    "helmet",
    "hi_vis",
    "ppe",
    "vest",
    "vehicle_color",
}
_BLOCKED_ATTRIBUTE_KEYS = {
    "biometric_id",
    "face_embedding",
    "face_id",
    "license_plate_plaintext",
    "person_id",
}
logger = logging.getLogger(__name__)


class AuditLogger(Protocol):
    async def record(
        self,
        *,
        tenant_context: TenantContext,
        action: str,
        target: str,
        meta: dict[str, Any] | None = None,
    ) -> None: ...


class CameraCommandPublisher(Protocol):
    async def publish(self, subject: str, payload: CameraCommandPayload) -> object: ...


def normalize_incident_type(value: str) -> str:
    normalized = _NON_SLUG_CHARS.sub("_", value.strip().lower()).strip("_")
    if normalized == "":
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="incident_type must contain at least one letter or number.",
        )
    return normalized


def build_rule_hash(rule: IncidentRuleCreate) -> str:
    predicate_payload = rule.predicate.model_dump(mode="json")
    predicate_payload["class_names"] = sorted(predicate_payload.get("class_names", []))
    predicate_payload["zone_ids"] = sorted(predicate_payload.get("zone_ids", []))
    payload = {
        "enabled": rule.enabled,
        "incident_type": normalize_incident_type(rule.incident_type or rule.name),
        "severity": rule.severity.value,
        "predicate": predicate_payload,
        "action": rule.action.value,
        "cooldown_seconds": rule.cooldown_seconds,
        "webhook_url_present": rule.webhook_url is not None,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_incident_rule_payload(
    rule: IncidentRuleCreate,
    *,
    available_classes: set[str],
    available_zone_ids: set[str],
    supported_attributes: set[str],
) -> None:
    errors = _incident_rule_validation_errors(
        rule,
        available_classes=available_classes,
        available_zone_ids=available_zone_ids,
        supported_attributes=supported_attributes,
    )
    if errors:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE,
            detail="; ".join(errors),
        )


def validate_rule_against_sample(
    rule: IncidentRuleCreate,
    *,
    sample_detection: dict[str, Any],
    available_classes: set[str],
    available_zone_ids: set[str],
    supported_attributes: set[str],
) -> IncidentRuleValidationResponse:
    errors = _incident_rule_validation_errors(
        rule,
        available_classes=available_classes,
        available_zone_ids=available_zone_ids,
        supported_attributes=supported_attributes,
    )
    if errors:
        return IncidentRuleValidationResponse(
            valid=False,
            matches=False,
            errors=errors,
            normalized_incident_type=None,
            rule_hash=None,
        )

    return IncidentRuleValidationResponse(
        valid=True,
        matches=_sample_matches_rule(rule.predicate, sample_detection),
        errors=[],
        normalized_incident_type=normalize_incident_type(rule.incident_type or rule.name),
        rule_hash=build_rule_hash(rule),
    )


class IncidentRuleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger: AuditLogger,
        events: CameraCommandPublisher | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.audit_logger = audit_logger
        self.events = events

    async def list_rules(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
    ) -> list[IncidentRuleResponse]:
        async with self.session_factory() as session:
            await self._load_camera(session, tenant_context, camera_id)
            statement = (
                select(DetectionRule)
                .where(DetectionRule.camera_id == camera_id)
                .order_by(DetectionRule.name)
            )
            rules = (await session.execute(statement)).scalars().all()
            return [_rule_to_response(rule) for rule in rules]

    async def get_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> IncidentRuleResponse:
        async with self.session_factory() as session:
            rule = await self._load_rule(session, tenant_context, camera_id, rule_id)
            return _rule_to_response(rule)

    async def create_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: IncidentRuleCreate,
    ) -> IncidentRuleResponse:
        async with self.session_factory() as session:
            camera = await self._load_camera(session, tenant_context, camera_id)
            normalized = _normalized_create_payload(payload)
            _validate_against_camera(camera, normalized)
            await self._ensure_unique(
                session,
                camera_id=camera_id,
                name=normalized.name,
                incident_type=normalized.incident_type or normalized.name,
                exclude_rule_id=None,
            )
            rule = DetectionRule(
                camera_id=camera_id,
                enabled=normalized.enabled,
                name=normalized.name,
                incident_type=normalize_incident_type(
                    normalized.incident_type or normalized.name
                ),
                severity=normalized.severity,
                description=normalized.description,
                zone_id=_single_zone_id(normalized.predicate),
                predicate=normalized.predicate.model_dump(mode="python"),
                action=normalized.action,
                webhook_url=normalized.webhook_url,
                cooldown_seconds=normalized.cooldown_seconds,
                rule_hash=build_rule_hash(normalized),
            )
            session.add(rule)
            await session.commit()
            await session.refresh(rule)

        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="incident_rule.create",
            target=f"incident_rule:{rule.id}",
            meta=_audit_meta(_rule_to_response(rule)),
        )
        await self._publish_camera_rule_command(camera_id)
        return _rule_to_response(rule)

    async def update_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
        payload: IncidentRuleUpdate,
    ) -> IncidentRuleResponse:
        async with self.session_factory() as session:
            rule = await self._load_rule(session, tenant_context, camera_id, rule_id)
            camera = await self._load_camera(session, tenant_context, camera_id)
            merged = _merge_update(rule, payload)
            _validate_against_camera(camera, merged)
            await self._ensure_unique(
                session,
                camera_id=camera_id,
                name=merged.name,
                incident_type=merged.incident_type or merged.name,
                exclude_rule_id=rule_id,
            )
            rule.enabled = merged.enabled
            rule.name = merged.name
            rule.incident_type = normalize_incident_type(merged.incident_type or merged.name)
            rule.severity = merged.severity
            rule.description = merged.description
            rule.zone_id = _single_zone_id(merged.predicate)
            rule.predicate = merged.predicate.model_dump(mode="python")
            rule.action = merged.action
            rule.webhook_url = merged.webhook_url
            rule.cooldown_seconds = merged.cooldown_seconds
            rule.rule_hash = build_rule_hash(merged)
            await session.commit()
            await session.refresh(rule)

        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="incident_rule.update",
            target=f"incident_rule:{rule.id}",
            meta=_audit_meta(_rule_to_response(rule)),
        )
        await self._publish_camera_rule_command(camera_id)
        return _rule_to_response(rule)

    async def delete_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> None:
        async with self.session_factory() as session:
            rule = await self._load_rule(session, tenant_context, camera_id, rule_id)
            response = _rule_to_response(rule)
            await session.delete(rule)
            await session.commit()

        await self.audit_logger.record(
            tenant_context=tenant_context,
            action="incident_rule.delete",
            target=f"incident_rule:{rule_id}",
            meta=_audit_meta(response),
        )
        await self._publish_camera_rule_command(camera_id)

    async def validate_rule(
        self,
        tenant_context: TenantContext,
        camera_id: UUID,
        payload: IncidentRuleValidationRequest,
    ) -> IncidentRuleValidationResponse:
        async with self.session_factory() as session:
            camera = await self._load_camera(session, tenant_context, camera_id)
        return validate_rule_against_sample(
            _normalized_create_payload(payload.rule),
            sample_detection=payload.sample_detection,
            available_classes=_available_classes(camera),
            available_zone_ids=_available_zone_ids(camera),
            supported_attributes=_supported_attributes(camera),
        )

    async def _load_camera(
        self,
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

    async def _load_rule(
        self,
        session: AsyncSession,
        tenant_context: TenantContext,
        camera_id: UUID,
        rule_id: UUID,
    ) -> DetectionRule:
        await self._load_camera(session, tenant_context, camera_id)
        statement = select(DetectionRule).where(
            DetectionRule.id == rule_id,
            DetectionRule.camera_id == camera_id,
        )
        rule = (await session.execute(statement)).scalar_one_or_none()
        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Incident rule not found.",
            )
        return rule

    async def _ensure_unique(
        self,
        session: AsyncSession,
        *,
        camera_id: UUID,
        name: str,
        incident_type: str,
        exclude_rule_id: UUID | None,
    ) -> None:
        normalized_type = normalize_incident_type(incident_type)
        statement: Select[tuple[DetectionRule]] = select(DetectionRule).where(
            DetectionRule.camera_id == camera_id,
            (
                (DetectionRule.name == name)
                | (DetectionRule.incident_type == normalized_type)
            ),
        )
        if exclude_rule_id is not None:
            statement = statement.where(DetectionRule.id != exclude_rule_id)
        existing = (await session.execute(statement)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE,
                detail="Incident rule name or incident type already exists for this camera.",
            )

    async def _publish_camera_rule_command(self, camera_id: UUID) -> None:
        if self.events is None:
            return
        async with self.session_factory() as session:
            statement = (
                select(DetectionRule)
                .where(
                    DetectionRule.camera_id == camera_id,
                    DetectionRule.enabled.is_(True),
                )
                .order_by(DetectionRule.incident_type, DetectionRule.name, DetectionRule.id)
            )
            rules = (await session.execute(statement)).scalars().all()
        command = CameraCommandPayload(
            incident_rules=[
                _rule_to_worker_rule(rule)
                for rule in rules
                if rule.enabled
            ],
        )
        try:
            await self.events.publish(f"cmd.camera.{camera_id}", command)
        except Exception:
            logger.exception("Failed to publish incident rule command for camera %s", camera_id)


def _normalized_create_payload(payload: IncidentRuleCreate) -> IncidentRuleCreate:
    return payload.model_copy(
        update={
            "name": payload.name.strip(),
            "incident_type": normalize_incident_type(payload.incident_type or payload.name),
            "description": payload.description.strip() if payload.description else None,
        }
    )


def _merge_update(rule: DetectionRule, payload: IncidentRuleUpdate) -> IncidentRuleCreate:
    values = {
        "enabled": rule.enabled,
        "name": rule.name,
        "incident_type": rule.incident_type,
        "severity": rule.severity,
        "description": rule.description,
        "predicate": IncidentRulePredicate.model_validate(rule.predicate),
        "action": rule.action,
        "cooldown_seconds": rule.cooldown_seconds,
        "webhook_url": rule.webhook_url,
    }
    update_data = payload.model_dump(exclude_unset=True)
    values.update(update_data)
    return _normalized_create_payload(IncidentRuleCreate.model_validate(values))


def _validate_against_camera(camera: Camera, payload: IncidentRuleCreate) -> None:
    validate_incident_rule_payload(
        payload,
        available_classes=_available_classes(camera),
        available_zone_ids=_available_zone_ids(camera),
        supported_attributes=_supported_attributes(camera),
    )


def _incident_rule_validation_errors(
    rule: IncidentRuleCreate,
    *,
    available_classes: set[str],
    available_zone_ids: set[str],
    supported_attributes: set[str],
) -> list[str]:
    errors: list[str] = []
    unknown_classes = sorted(set(rule.predicate.class_names) - available_classes)
    if unknown_classes:
        errors.append(f"Unknown class names: {', '.join(unknown_classes)}")

    unknown_zones = sorted(set(rule.predicate.zone_ids) - available_zone_ids)
    if unknown_zones:
        errors.append(f"Unknown zone ids: {', '.join(unknown_zones)}")

    attribute_keys = set(rule.predicate.attributes)
    unsupported_attributes = sorted(
        key
        for key in attribute_keys
        if key in _BLOCKED_ATTRIBUTE_KEYS or key not in supported_attributes
    )
    if unsupported_attributes:
        errors.append(f"Unsupported attribute keys: {', '.join(unsupported_attributes)}")

    return errors


def _sample_matches_rule(
    predicate: IncidentRulePredicate,
    sample_detection: dict[str, Any],
) -> bool:
    class_name = sample_detection.get("class_name")
    if predicate.class_names and class_name not in predicate.class_names:
        return False

    zone_id = sample_detection.get("zone_id")
    if predicate.zone_ids and zone_id not in predicate.zone_ids:
        return False

    confidence = float(sample_detection.get("confidence") or 0.0)
    if confidence < predicate.min_confidence:
        return False

    attributes = sample_detection.get("attributes") or {}
    if not isinstance(attributes, dict):
        return False
    for key, expected in predicate.attributes.items():
        if attributes.get(key) != expected:
            return False

    return True


def _available_classes(camera: Camera) -> set[str]:
    classes = set(_clean_strings(camera.active_classes or []))
    classes.update(_clean_strings(camera.runtime_vocabulary or []))
    return classes


def _available_zone_ids(camera: Camera) -> set[str]:
    zone_ids: set[str] = set()
    for zone in camera.zones or []:
        if isinstance(zone, dict):
            zone_id = zone.get("id")
            if isinstance(zone_id, str) and zone_id.strip():
                zone_ids.add(zone_id.strip())
    return zone_ids


def _supported_attributes(camera: Camera) -> set[str]:
    attributes = set(_KNOWN_SAFE_ATTRIBUTES)
    for rule in camera.attribute_rules or []:
        if not isinstance(rule, dict):
            continue
        for key in ("attribute", "attribute_name", "key", "name", "id"):
            value = rule.get(key)
            if isinstance(value, str) and value.strip():
                attributes.add(value.strip())
        outputs = rule.get("outputs")
        if isinstance(outputs, list):
            attributes.update(_clean_strings(outputs))
    return attributes - _BLOCKED_ATTRIBUTE_KEYS


def _clean_strings(values: Iterable[object]) -> list[str]:
    return [value.strip() for value in values if isinstance(value, str) and value.strip()]


def _single_zone_id(predicate: IncidentRulePredicate) -> str | None:
    return predicate.zone_ids[0] if len(predicate.zone_ids) == 1 else None


def _rule_to_response(rule: DetectionRule) -> IncidentRuleResponse:
    return IncidentRuleResponse(
        id=rule.id,
        camera_id=rule.camera_id,
        enabled=rule.enabled,
        name=rule.name,
        incident_type=rule.incident_type,
        severity=rule.severity,
        description=rule.description,
        predicate=IncidentRulePredicate.model_validate(rule.predicate),
        action=rule.action,
        cooldown_seconds=rule.cooldown_seconds,
        webhook_url_present=rule.webhook_url is not None,
        rule_hash=rule.rule_hash,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def _rule_to_worker_rule(rule: DetectionRule) -> WorkerIncidentRule:
    return WorkerIncidentRule(
        id=rule.id,
        camera_id=rule.camera_id,
        enabled=rule.enabled,
        name=rule.name,
        incident_type=rule.incident_type,
        severity=rule.severity,
        predicate=WorkerIncidentRulePredicate.model_validate(rule.predicate),
        action=rule.action,
        cooldown_seconds=rule.cooldown_seconds,
        webhook_url=rule.webhook_url,
        rule_hash=rule.rule_hash,
    )


def _audit_meta(response: IncidentRuleResponse) -> dict[str, Any]:
    return {
        "camera_id": str(response.camera_id),
        "enabled": response.enabled,
        "name": response.name,
        "incident_type": response.incident_type,
        "severity": response.severity.value,
        "action": response.action.value,
        "cooldown_seconds": response.cooldown_seconds,
        "webhook_url_present": response.webhook_url_present,
        "rule_hash": response.rule_hash,
    }
