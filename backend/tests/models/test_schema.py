from __future__ import annotations

from argus.models import Base

EXPECTED_TABLES = {
    "api_keys",
    "audit_log",
    "cameras",
    "detection_rules",
    "edge_nodes",
    "incidents",
    "models",
    "rule_events",
    "sites",
    "tenants",
    "tracking_events",
    "users",
}


def test_declares_all_prompt_one_tables() -> None:
    assert EXPECTED_TABLES.issubset(Base.metadata.tables.keys())


def test_cameras_table_has_prompt_one_columns() -> None:
    camera_columns = Base.metadata.tables["cameras"].columns.keys()
    assert "processing_mode" in camera_columns
    assert "primary_model_id" in camera_columns
    assert "secondary_model_id" in camera_columns
    assert "tracker_type" in camera_columns
    assert "active_classes" in camera_columns
    assert "attribute_rules" in camera_columns
    assert "zones" in camera_columns
    assert "homography" in camera_columns
    assert "privacy" in camera_columns


def test_tracking_events_support_class_aggregations() -> None:
    tracking_columns = Base.metadata.tables["tracking_events"].columns.keys()
    rule_event_columns = Base.metadata.tables["rule_events"].columns.keys()

    assert "class_name" in tracking_columns
    assert "class_name" not in rule_event_columns


def test_event_hypertables_include_ts_in_primary_key() -> None:
    tracking_primary_key = {
        column.name for column in Base.metadata.tables["tracking_events"].primary_key
    }
    rule_primary_key = {column.name for column in Base.metadata.tables["rule_events"].primary_key}

    assert tracking_primary_key == {"id", "ts"}
    assert rule_primary_key == {"id", "ts"}


def test_sqlalchemy_enums_use_database_values_not_member_names() -> None:
    camera_columns = Base.metadata.tables["cameras"].columns
    model_columns = Base.metadata.tables["models"].columns
    incident_columns = Base.metadata.tables["incidents"].columns

    assert list(camera_columns["processing_mode"].type.enums) == ["central", "edge", "hybrid"]
    assert list(camera_columns["tracker_type"].type.enums) == ["botsort", "bytetrack", "ocsort"]
    assert list(model_columns["task"].type.enums) == ["detect", "classify", "attribute"]
    assert list(incident_columns["review_status"].type.enums) == ["pending", "reviewed"]


def test_incidents_table_tracks_review_state() -> None:
    incident_columns = Base.metadata.tables["incidents"].columns.keys()

    assert "review_status" in incident_columns
    assert "reviewed_at" in incident_columns
    assert "reviewed_by_subject" in incident_columns


def test_schema_exposes_open_vocab_tables_and_columns() -> None:
    from argus.models.tables import Camera, CountEvent, Model, TrackingEvent

    assert "capability" in Model.__table__.c
    assert "capability_config" in Model.__table__.c
    assert "runtime_vocabulary" in Camera.__table__.c
    assert "runtime_vocabulary_source" in Camera.__table__.c
    assert "runtime_vocabulary_version" in Camera.__table__.c
    assert "runtime_vocabulary_updated_at" in Camera.__table__.c
    assert "vocabulary_version" in TrackingEvent.__table__.c
    assert "vocabulary_hash" in TrackingEvent.__table__.c
    assert "vocabulary_version" in CountEvent.__table__.c
    assert "vocabulary_hash" in CountEvent.__table__.c


def test_schema_registers_camera_vocabulary_snapshots_table() -> None:
    from argus.models.tables import CameraVocabularySnapshot

    assert CameraVocabularySnapshot.__tablename__ == "camera_vocabulary_snapshots"
    assert "camera_id" in CameraVocabularySnapshot.__table__.c
    assert "version" in CameraVocabularySnapshot.__table__.c
    assert "vocabulary_hash" in CameraVocabularySnapshot.__table__.c
    assert "terms" in CameraVocabularySnapshot.__table__.c
