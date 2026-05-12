from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from argus.models.enums import RuleAction
from argus.vision.types import Detection


class RulePublisher(Protocol):
    async def publish(self, subject: str, payload: BaseModel) -> None: ...


class RuleStore(Protocol):
    async def record(self, event: BaseModel) -> None: ...


@dataclass(slots=True)
class RuleDefinition:
    id: UUID
    camera_id: UUID
    name: str
    predicate: dict[str, Any]
    action: RuleAction
    enabled: bool = True
    incident_type: str | None = None
    severity: str = "warning"
    cooldown_seconds: int = 0
    zone_id: str | None = None
    webhook_url: str | None = None
    rule_hash: str | None = None


class RuleEventRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: UUID
    camera_id: UUID
    action: RuleAction
    name: str
    incident_type: str | None = None
    severity: str | None = None
    cooldown_seconds: int = 0
    predicate: dict[str, Any] = Field(default_factory=dict)
    rule_hash: str | None = None
    ts: datetime
    detection: dict[str, Any]


class RuleEngine:
    def __init__(
        self,
        *,
        rules: list[RuleDefinition],
        publisher: RulePublisher,
        store: RuleStore,
    ) -> None:
        self.publisher = publisher
        self.store = store
        self._rules_by_camera: dict[UUID, list[RuleDefinition]] = defaultdict(list)
        self._last_triggered: dict[UUID, datetime] = {}
        self.replace_rules(rules)

    def replace_rules(self, rules: list[RuleDefinition]) -> None:
        self._rules_by_camera.clear()
        self._last_triggered.clear()
        for rule in rules:
            if rule.enabled:
                self._rules_by_camera[rule.camera_id].append(rule)

    async def evaluate(
        self,
        *,
        camera_id: UUID,
        detections: list[Detection],
        ts: datetime,
    ) -> list[RuleEventRecord]:
        events: list[RuleEventRecord] = []
        for rule in self._rules_by_camera.get(camera_id, []):
            if not rule.enabled:
                continue
            if self._is_on_cooldown(rule, ts):
                continue

            for detection in detections:
                if not _matches_rule(rule, detection):
                    continue

                event = RuleEventRecord(
                    rule_id=rule.id,
                    camera_id=camera_id,
                    action=rule.action,
                    name=rule.name,
                    incident_type=rule.incident_type,
                    severity=rule.severity,
                    cooldown_seconds=rule.cooldown_seconds,
                    predicate=dict(rule.predicate),
                    rule_hash=rule.rule_hash,
                    ts=ts,
                    detection={
                        "class_name": detection.class_name,
                        "confidence": detection.confidence,
                        "bbox": detection.bbox,
                        "track_id": detection.track_id,
                        "zone_id": detection.zone_id,
                        "attributes": detection.attributes,
                    },
                )
                await self.publisher.publish(f"evt.rule.{camera_id}", event)
                await self.store.record(event)
                self._last_triggered[rule.id] = ts
                events.append(event)
        return events

    def _is_on_cooldown(self, rule: RuleDefinition, ts: datetime) -> bool:
        if rule.cooldown_seconds <= 0:
            return False

        last_triggered = self._last_triggered.get(rule.id)
        if last_triggered is None:
            return False

        return ts < last_triggered + timedelta(seconds=rule.cooldown_seconds)


def _matches_rule(rule: RuleDefinition, detection: Detection) -> bool:
    class_names = rule.predicate.get("class_names")
    if class_names and detection.class_name not in class_names:
        return False

    zone_ids = rule.predicate.get("zone_ids")
    if zone_ids and detection.zone_id not in zone_ids:
        return False

    if rule.zone_id is not None and detection.zone_id != rule.zone_id:
        return False

    min_confidence = rule.predicate.get("min_confidence")
    if min_confidence is not None and detection.confidence < float(min_confidence):
        return False

    required_attributes = rule.predicate.get("attributes", {})
    for attribute_name, expected_value in required_attributes.items():
        if detection.attributes.get(attribute_name) != expected_value:
            return False

    return True
