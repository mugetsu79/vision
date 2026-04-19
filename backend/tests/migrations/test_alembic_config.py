from __future__ import annotations

from alembic.config import Config

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


def test_configure_database_url_keeps_existing_value(monkeypatch) -> None:
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+asyncpg://argus:argus@localhost:5432/argus")
    monkeypatch.delenv("ARGUS_DB_URL", raising=False)

    database_url = configure_database_url(config)

    assert database_url == "postgresql+asyncpg://argus:argus@localhost:5432/argus"
    assert config.get_main_option("sqlalchemy.url") == database_url
