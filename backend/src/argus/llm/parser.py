from __future__ import annotations

import re
import time
from dataclasses import dataclass

from argus.core.config import Settings
from argus.llm.adapter import ClassFilterResponse, LLMClient
from argus.llm.providers.anthropic import AnthropicClient
from argus.llm.providers.gemini import GeminiClient
from argus.llm.providers.ollama import OllamaClient
from argus.llm.providers.openai import OpenAIClient
from argus.llm.providers.vllm import VLLMClient


@dataclass(slots=True, frozen=True)
class ParserResult:
    classes: list[str]
    provider: str
    model: str
    latency_ms: int


class ClassFilterParser:
    def __init__(
        self,
        settings: Settings,
        *,
        client: LLMClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or _build_client(settings)

    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
    ) -> ParserResult:
        started_at = time.perf_counter()
        try:
            response = await self.client.extract_classes(
                prompt=_compose_prompt(prompt, allowed_classes),
                allowed=allowed_classes,
            )
            validated = _normalize_classes(response, allowed_classes)
            provider = self.settings.llm_provider
            model = self.settings.llm_model
        except Exception:
            validated = _keyword_fallback(prompt, allowed_classes)
            provider = "keyword-fallback"
            model = "fallback"

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return ParserResult(
            classes=validated,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
        )


def _build_client(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "openai":
        return OpenAIClient(model=settings.llm_model)
    if provider == "anthropic":
        return AnthropicClient(model=settings.llm_model)
    if provider == "gemini":
        return GeminiClient(model=settings.llm_model)
    if provider == "ollama":
        return OllamaClient(
            base_url=settings.llm_ollama_base_url,
            model=settings.llm_model,
        )
    if provider == "vllm":
        return VLLMClient(
            base_url=settings.llm_vllm_base_url,
            model=settings.llm_model,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def _compose_prompt(prompt: str, allowed_classes: list[str]) -> str:
    return (
        "You map natural-language operator instructions to detection classes.\n"
        f"Allowed classes: {', '.join(sorted(allowed_classes))}\n"
        f"User request: {prompt}\n"
        "Return JSON only."
    )


def _normalize_classes(response: ClassFilterResponse, allowed_classes: list[str]) -> list[str]:
    allowed = {class_name.lower(): class_name for class_name in allowed_classes}
    resolved: list[str] = []
    for class_name in response.classes:
        normalized = class_name.lower().strip()
        if normalized in allowed and allowed[normalized] not in resolved:
            resolved.append(allowed[normalized])
    return resolved


def _keyword_fallback(prompt: str, allowed_classes: list[str]) -> list[str]:
    normalized_prompt = re.sub(r"[^a-z0-9\s]", " ", prompt.lower())
    tokens = {token for token in normalized_prompt.split() if token}
    resolved: list[str] = []
    for class_name in allowed_classes:
        forms = _plural_forms(class_name)
        if tokens.intersection(forms):
            resolved.append(class_name)
    return resolved


def _plural_forms(word: str) -> set[str]:
    lowered = word.lower()
    forms = {lowered}
    if lowered.endswith("y") and len(lowered) > 1:
        forms.add(f"{lowered[:-1]}ies")
    elif lowered.endswith(("s", "x", "z", "ch", "sh")):
        forms.add(f"{lowered}es")
    else:
        forms.add(f"{lowered}s")
    if lowered == "bus":
        forms.add("buses")
    return forms
