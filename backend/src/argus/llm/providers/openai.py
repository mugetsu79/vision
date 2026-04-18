from __future__ import annotations

from argus.llm.providers.shared import LiteLLMProvider


class OpenAIClient(LiteLLMProvider):
    provider_name = "openai"
