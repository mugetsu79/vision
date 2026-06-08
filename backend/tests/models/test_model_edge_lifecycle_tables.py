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


def test_deployment_model_assignment_tracks_last_sync_job() -> None:
    table = Base.metadata.tables["deployment_model_assignments"]
    foreign_key_targets = {
        foreign_key.target_fullname
        for foreign_key in table.c.last_sync_job_id.foreign_keys
    }

    assert "deployment_model_sync_jobs.id" in foreign_key_targets


def test_runtime_artifact_build_jobs_include_build_format() -> None:
    table = Base.metadata.tables["runtime_artifact_build_jobs"]

    assert "build_format" in table.c
