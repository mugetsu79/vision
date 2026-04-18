from __future__ import annotations

import importlib

from argus.llm.adapter import ClassFilterResponse


class LiteLLMProvider:
    provider_name = "unknown"

    def __init__(self, *, model: str) -> None:
        self.model = model

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

        response = await acompletion(
            model=self.model,
            messages=[
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
            response_format={"type": "json_object"},
        )
        choice = response["choices"][0]["message"]["content"]
        return ClassFilterResponse.model_validate_json(choice)
