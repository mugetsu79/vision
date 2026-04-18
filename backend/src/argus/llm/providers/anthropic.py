from __future__ import annotations

from argus.llm.providers.shared import LiteLLMProvider


class AnthropicClient(LiteLLMProvider):
    provider_name = "anthropic"
