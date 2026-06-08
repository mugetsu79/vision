from argus.models.base import Base


def test_model_edge_lifecycle_tables_are_registered() -> None:
    table_names = set(Base.metadata.tables)
    assert "model_import_jobs" in table_names
    assert "deployment_model_assignments" in table_names
    assert "deployment_model_sync_jobs" in table_names
    assert "deployment_model_inventory" in table_names
    assert "runtime_artifact_build_jobs" in table_names
    assert "supervisor_model_job_events" in table_names
    assert "edge_configuration_assignments" in table_names
