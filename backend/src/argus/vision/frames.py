from __future__ import annotations

from typing import Literal, Protocol, TypeGuard

import numpy as np
from numpy.typing import NDArray

Frame = NDArray[np.uint8]
MemoryKind = Literal["cpu_bgr", "nvmm", "cuda"]


class CapturedFrame(Protocol):
    width: int
    height: int
    memory_kind: MemoryKind
    source_profile_hash: str | None

    def as_bgr_numpy(self) -> Frame: ...


def is_captured_frame(value: object) -> TypeGuard[CapturedFrame]:
    return callable(getattr(value, "as_bgr_numpy", None)) and hasattr(value, "memory_kind")
