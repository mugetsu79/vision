from __future__ import annotations

import os

from alembic.config import Config


def configure_database_url(config: Config) -> str:
    """Prefer the runtime database URL when Alembic runs inside containers."""
    database_url = os.getenv("ARGUS_DB_URL") or config.get_main_option("sqlalchemy.url")
    config.set_main_option("sqlalchemy.url", database_url)
    return database_url
