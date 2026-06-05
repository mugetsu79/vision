from __future__ import annotations

from typing import Any

__all__ = ["AppServices", "build_app_services"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from argus.services import app

        value = getattr(app, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
