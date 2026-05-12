from __future__ import annotations

import importlib

from argus.llm.adapter import ClassFilterResponse


class LiteLLMProvider:
    provider_name = "unknown"

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    async def extract_classes(
        self,
        *,
        prompt: str,
        allowed: list[str],
    ) -> ClassFilterResponse:
        try:
            litellm = importlib.import_module("litellm")
        except ImportError as exc:  # pragma: no cover - optional runtime dependency
            raise RuntimeError("LiteLLM is not installed.") from exc
        acompletion = litellm.acompletion

        kwargs: dict[str, object] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Return JSON with a single key named 'classes'. "
                        "Only include classes from the allowed list."
                    ),
                },
                {
                    "role": "user",
                    "content": {
                        "prompt": prompt,
                        "allowed": allowed,
                    },
                },
            ],
            "response_format": {"type": "json_object"},
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.base_url:
            kwargs["api_base"] = self.base_url
        response = await acompletion(**kwargs)
        choice = response["choices"][0]["message"]["content"]
        return ClassFilterResponse.model_validate_json(choice)
