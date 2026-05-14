from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from argus.migrations.alembic_config import configure_database_url


def test_configure_database_url_uses_argus_db_url(monkeypatch) -> None:
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://argus:argus@localhost:5432/argus")
    monkeypatch.setenv(
        "ARGUS_DB_URL",
        "postgresql+asyncpg://argus:argus@postgres:5432/argus",
    )

    database_url = configure_database_url(config)

    assert database_url == "postgresql+asyncpg://argus:argus@postgres:5432/argus"
    assert config.get_main_option("sqlalchemy.url") == database_url


def test_configure_database_url_uses_docker_secret_file(monkeypatch, tmp_path) -> None:
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://argus:argus@localhost:5432/argus")
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ARGUS_DB_URL").write_text(
        "postgresql+asyncpg://argus:secret@postgres:5432/argus\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ARGUS_DB_URL", raising=False)
    monkeypatch.setenv("ARGUS_SECRETS_DIR", str(secrets_dir))

    database_url = configure_database_url(config)

    assert database_url == "postgresql+asyncpg://argus:secret@postgres:5432/argus"
    assert config.get_main_option("sqlalchemy.url") == database_url


def test_configure_database_url_keeps_existing_value(monkeypatch) -> None:
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://argus:argus@localhost:5432/argus")
    monkeypatch.delenv("ARGUS_DB_URL", raising=False)
    monkeypatch.delenv("ARGUS_SECRETS_DIR", raising=False)

    database_url = configure_database_url(config)

    assert database_url == "postgresql+asyncpg://argus:argus@localhost:5432/argus"
    assert config.get_main_option("sqlalchemy.url") == database_url


def test_revision_ids_fit_alembic_version_column() -> None:
    config = Config()
    migrations_path = Path(__file__).resolve().parents[2] / "src" / "argus" / "migrations"
    config.set_main_option("script_location", str(migrations_path))

    script = ScriptDirectory.from_config(config)
    revision_ids = [revision.revision for revision in script.walk_revisions()]

    assert all(len(revision_id) <= 32 for revision_id in revision_ids)
