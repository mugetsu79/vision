"""Core backend utilities."""

from argus.core.config import Settings, settings
from argus.core.db import DatabaseManager, get_session
from argus.core.events import EventMessage, NatsJetStreamClient
from argus.core.security import (
    AuthenticatedUser,
    EdgeKeyMiddleware,
    SecurityService,
    decrypt_config_secret,
    decrypt_rtsp_url,
    encrypt_config_secret,
    encrypt_rtsp_url,
    get_current_user,
    require,
)

__all__ = [
    "AuthenticatedUser",
    "DatabaseManager",
    "EdgeKeyMiddleware",
    "EventMessage",
    "NatsJetStreamClient",
    "SecurityService",
    "Settings",
    "decrypt_config_secret",
    "decrypt_rtsp_url",
    "encrypt_config_secret",
    "encrypt_rtsp_url",
    "get_current_user",
    "get_session",
    "require",
    "settings",
]
