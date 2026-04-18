from __future__ import annotations

from argus.llm.providers.shared import LiteLLMProvider


class GeminiClient(LiteLLMProvider):
    provider_name = "gemini"
