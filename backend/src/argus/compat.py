from __future__ import annotations

from datetime import timezone
from enum import Enum
from typing import TYPE_CHECKING

UTC = timezone.utc  # noqa: UP017

if TYPE_CHECKING:
    from enum import StrEnum as StrEnum
else:
    try:
        from enum import StrEnum as StrEnum
    except ImportError:  # pragma: no cover - exercised by the Python 3.10 edge image

        class StrEnum(str, Enum):  # noqa: UP042
            def __str__(self) -> str:
                return str(self.value)
