from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config


def _database_url_from_secret_file() -> str | None:
    secrets_dir = Path(os.getenv("ARGUS_SECRETS_DIR", "/run/secrets"))
    secret_path = secrets_dir / "ARGUS_DB_URL"
    try:
        value = secret_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def configure_database_url(config: Config) -> str:
    """Prefer the runtime database URL when Alembic runs inside containers."""
    database_url = (
        os.getenv("ARGUS_DB_URL")
        or _database_url_from_secret_file()
        or config.get_main_option("sqlalchemy.url")
    )
    if database_url is None:
        raise RuntimeError("Alembic sqlalchemy.url is not configured.")
    config.set_main_option("sqlalchemy.url", database_url)
    return database_url
