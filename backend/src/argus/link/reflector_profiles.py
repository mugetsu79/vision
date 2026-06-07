from __future__ import annotations

import secrets
from datetime import datetime

from argus.core.config import Settings
from argus.core.security import decrypt_config_secret, encrypt_config_secret


def generate_reflector_secret() -> str:
    return f"vzref_{secrets.token_urlsafe(32)}"


def generate_reflector_key_id(*, now: datetime) -> str:
    return f"master-reflector-{now:%Y%m%d%H%M%S}-{secrets.token_hex(4)}"


def encrypt_reflector_secret(secret: str, *, settings: Settings) -> str:
    return encrypt_config_secret(secret, settings)


def decrypt_reflector_secret(encrypted_secret: str, *, settings: Settings) -> str:
    return decrypt_config_secret(encrypted_secret, settings)
