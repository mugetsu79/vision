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

    assert list(camera_columns["processing_mode"].type.enums) == ["central", "edge", "hybrid"]
    assert list(camera_columns["tracker_type"].type.enums) == ["botsort", "bytetrack", "ocsort"]
    assert list(model_columns["task"].type.enums) == ["detect", "classify", "attribute"]
