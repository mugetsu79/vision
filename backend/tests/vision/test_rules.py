from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from argus.models.enums import RuleAction
from argus.vision.rules import RuleDefinition, RuleEngine
from argus.vision.types import Detection


class _RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[tuple[str, object]] = []

    async def publish(self, subject: str, payload: object) -> None:
        self.messages.append((subject, payload))


class _RecordingStore:
    def __init__(self) -> None:
        self.events: list[object] = []

    async def record(self, event: object) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_rule_engine_emits_events_and_honors_cooldowns() -> None:
    camera_id = uuid4()
    rule_id = uuid4()
    publisher = _RecordingPublisher()
    store = _RecordingStore()
    engine = RuleEngine(
        rules=[
            RuleDefinition(
                id=rule_id,
                camera_id=camera_id,
                name="restricted-no-vest",
                incident_type="restricted_person",
                severity="critical",
                predicate={
                    "class_names": ["person", "hi_vis_worker"],
                    "zone_ids": ["restricted"],
                    "attributes": {"hi_vis": False},
                    "min_confidence": 0.5
                },
                action=RuleAction.ALERT,
                cooldown_seconds=5,
                rule_hash="c" * 64,
            )
        ],
        publisher=publisher,
        store=store,
    )
    detected_at = datetime(2026, 4, 18, 12, 0, tzinfo=UTC)
    detections = [
        Detection(
            class_name="person",
            confidence=0.96,
            bbox=(40.0, 12.0, 80.0, 90.0),
            zone_id="restricted",
            attributes={"hi_vis": False},
            track_id=7,
        )
    ]

    first_events = await engine.evaluate(camera_id=camera_id, detections=detections, ts=detected_at)
    suppressed_events = await engine.evaluate(
        camera_id=camera_id,
        detections=detections,
        ts=detected_at + timedelta(seconds=2),
    )
    cooled_down_events = await engine.evaluate(
        camera_id=camera_id,
        detections=detections,
        ts=detected_at + timedelta(seconds=6),
    )

    assert len(first_events) == 1
    assert suppressed_events == []
    assert len(cooled_down_events) == 1
    assert first_events[0].incident_type == "restricted_person"
    assert first_events[0].severity == "critical"
    assert first_events[0].rule_hash == "c" * 64
    assert len(publisher.messages) == 2
    assert len(store.events) == 2
    assert publisher.messages[0][0] == f"evt.rule.{camera_id}"


@pytest.mark.asyncio
async def test_rule_engine_replaces_rules_for_hot_reload() -> None:
    camera_id = uuid4()
    publisher = _RecordingPublisher()
    store = _RecordingStore()
    engine = RuleEngine(rules=[], publisher=publisher, store=store)
    engine.replace_rules(
        [
            RuleDefinition(
                id=uuid4(),
                camera_id=camera_id,
                name="restricted-person",
                incident_type="restricted_person",
                severity="warning",
                predicate={"class_names": ["person"]},
                action=RuleAction.RECORD_CLIP,
                rule_hash="d" * 64,
            )
        ]
    )

    events = await engine.evaluate(
        camera_id=camera_id,
        detections=[
            Detection(
                class_name="person",
                confidence=0.91,
                bbox=(0.0, 0.0, 10.0, 10.0),
            )
        ],
        ts=datetime(2026, 5, 12, 12, 0, tzinfo=UTC),
    )

    assert len(events) == 1
    assert events[0].action is RuleAction.RECORD_CLIP
