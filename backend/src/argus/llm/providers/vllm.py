from __future__ import annotations

from typing import Any

import httpx

from argus.llm.adapter import ClassFilterResponse


class VLLMClient:
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._owned_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient()

    async def extract_classes(
        self,
        *,
        prompt: str,
        allowed: list[str],
    ) -> ClassFilterResponse:
        response = await self._http_client.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return JSON with key 'classes'. Only include values from the "
                            f"allowed list: {allowed}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        content = payload["choices"][0]["message"]["content"]
        return ClassFilterResponse.model_validate_json(content)

    async def close(self) -> None:
        if self._owned_client:
            await self._http_client.aclose()
