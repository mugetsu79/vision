"""Core backend utilities."""

from traffic_monitor.core.config import Settings, settings
from traffic_monitor.core.db import DatabaseManager, get_session
from traffic_monitor.core.events import EventMessage, NatsJetStreamClient
from traffic_monitor.core.security import (
    AuthenticatedUser,
    EdgeKeyMiddleware,
    SecurityService,
    decrypt_rtsp_url,
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
    "decrypt_rtsp_url",
    "encrypt_rtsp_url",
    "get_current_user",
    "get_session",
    "require",
    "settings",
]
