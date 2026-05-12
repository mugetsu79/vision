from __future__ import annotations

import pytest
from fastapi import HTTPException

from argus.api.contracts import IncidentRuleCreate, IncidentRulePredicate
from argus.models.enums import IncidentRuleSeverity, RuleAction
from argus.services.incident_rules import (
    build_rule_hash,
    normalize_incident_type,
    validate_incident_rule_payload,
    validate_rule_against_sample,
)


def test_normalizes_incident_type_to_stable_slug() -> None:
    assert normalize_incident_type("Restricted Person!") == "restricted_person"
    assert normalize_incident_type("  PPE missing: hardhat  ") == "ppe_missing_hardhat"


def test_rule_hash_is_deterministic_and_redacts_webhook_secret() -> None:
    base = IncidentRuleCreate(
        name="Restricted person",
        incident_type="restricted_person",
        severity=IncidentRuleSeverity.CRITICAL,
        predicate=IncidentRulePredicate(
            class_names=["person"],
            zone_ids=["restricted"],
            min_confidence=0.7,
            attributes={"hi_vis": False},
        ),
        action=RuleAction.WEBHOOK,
        webhook_url="https://hooks.example.local/a-secret-token",
        cooldown_seconds=60,
    )
    equivalent_secret = base.model_copy(
        update={"webhook_url": "https://hooks.example.local/rotated-secret-token"}
    )
    changed_predicate = base.model_copy(
        update={
            "predicate": base.predicate.model_copy(update={"min_confidence": 0.8})
        }
    )

    assert build_rule_hash(base) == build_rule_hash(equivalent_secret)
    assert build_rule_hash(base) != build_rule_hash(changed_predicate)


def test_validate_rule_payload_rejects_unknown_scene_terms() -> None:
    payload = IncidentRuleCreate(
        name="Forklift in lobby",
        incident_type="forklift_lobby",
        predicate=IncidentRulePredicate(
            class_names=["forklift"],
            zone_ids=["lobby"],
            min_confidence=0.6,
        ),
        action=RuleAction.RECORD_CLIP,
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_incident_rule_payload(
            payload,
            available_classes={"person"},
            available_zone_ids={"restricted"},
            supported_attributes={"hi_vis"},
        )

    assert exc_info.value.status_code == 422
    assert "Unknown class" in str(exc_info.value.detail)


def test_validate_rule_payload_rejects_unsupported_attributes() -> None:
    payload = IncidentRuleCreate(
        name="Face watch",
        incident_type="face_watch",
        predicate=IncidentRulePredicate(
            class_names=["person"],
            attributes={"face_id": "abc"},
        ),
        action=RuleAction.ALERT,
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_incident_rule_payload(
            payload,
            available_classes={"person"},
            available_zone_ids=set(),
            supported_attributes={"hi_vis"},
        )

    assert exc_info.value.status_code == 422
    assert "Unsupported attribute" in str(exc_info.value.detail)


def test_validate_rule_against_sample_reports_match() -> None:
    payload = IncidentRuleCreate(
        name="Restricted person",
        incident_type="restricted_person",
        predicate=IncidentRulePredicate(
            class_names=["person"],
            zone_ids=["restricted"],
            min_confidence=0.7,
            attributes={"hi_vis": False},
        ),
        action=RuleAction.RECORD_CLIP,
    )

    result = validate_rule_against_sample(
        payload,
        sample_detection={
            "class_name": "person",
            "zone_id": "restricted",
            "confidence": 0.91,
            "attributes": {"hi_vis": False},
        },
        available_classes={"person"},
        available_zone_ids={"restricted"},
        supported_attributes={"hi_vis"},
    )

    assert result.valid is True
    assert result.matches is True
    assert result.rule_hash == build_rule_hash(payload)
    assert result.normalized_incident_type == "restricted_person"


def test_validate_rule_against_sample_reports_non_match_without_error() -> None:
    payload = IncidentRuleCreate(
        name="Restricted person",
        incident_type="restricted_person",
        predicate=IncidentRulePredicate(
            class_names=["person"],
            zone_ids=["restricted"],
            min_confidence=0.7,
        ),
        action=RuleAction.RECORD_CLIP,
    )

    result = validate_rule_against_sample(
        payload,
        sample_detection={
            "class_name": "person",
            "zone_id": "public",
            "confidence": 0.91,
            "attributes": {},
        },
        available_classes={"person"},
        available_zone_ids={"restricted", "public"},
        supported_attributes=set(),
    )

    assert result.valid is True
    assert result.matches is False
    assert result.errors == []


def test_validate_rule_against_sample_returns_validation_errors() -> None:
    payload = IncidentRuleCreate(
        name="Unknown",
        incident_type="unknown",
        predicate=IncidentRulePredicate(class_names=["forklift"]),
        action=RuleAction.RECORD_CLIP,
    )

    result = validate_rule_against_sample(
        payload,
        sample_detection={
            "class_name": "forklift",
            "zone_id": None,
            "confidence": 0.9,
            "attributes": {},
        },
        available_classes={"person"},
        available_zone_ids=set(),
        supported_attributes=set(),
    )

    assert result.valid is False
    assert result.matches is False
    assert result.rule_hash is None
    assert result.errors == ["Unknown class names: forklift"]
