from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class ClassFilterResponse(BaseModel):
    classes: list[str] = Field(default_factory=list)


class LLMClient(Protocol):
    async def extract_classes(
        self,
        *,
        prompt: str,
        allowed: list[str],
    ) -> ClassFilterResponse: ...
