from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.llm.adapter import ClassFilterResponse, LLMClient
from argus.llm.providers.anthropic import AnthropicClient
from argus.llm.providers.gemini import GeminiClient
from argus.llm.providers.ollama import OllamaClient
from argus.llm.providers.openai import OpenAIClient
from argus.llm.providers.vllm import VLLMClient
from argus.services.llm_provider_runtime import ResolvedLLMProviderSettings


@dataclass(slots=True, frozen=True)
class ParserResult:
    classes: list[str]
    provider: str
    model: str
    latency_ms: int


class LLMProviderResolver(Protocol):
    async def resolve_for_prompt(
        self,
        *,
        tenant_context: TenantContext,
        camera_id: UUID | None = None,
    ) -> ResolvedLLMProviderSettings: ...


LLMClientFactory = Callable[
    [Settings, ResolvedLLMProviderSettings | None],
    LLMClient,
]


class ClassFilterParser:
    def __init__(
        self,
        settings: Settings,
        *,
        client: LLMClient | None = None,
        llm_provider_resolver: LLMProviderResolver | None = None,
        client_factory: LLMClientFactory | None = None,
    ) -> None:
        self.settings = settings
        self.llm_provider_resolver = llm_provider_resolver
        self.client_factory = client_factory or _build_client
        self.client = client or (
            None
            if llm_provider_resolver is not None
            else self.client_factory(settings, None)
        )

    async def resolve_classes(
        self,
        *,
        prompt: str,
        allowed_classes: list[str],
        tenant_context: TenantContext | None = None,
        camera_ids: list[UUID] | None = None,
    ) -> ParserResult:
        started_at = time.perf_counter()
        provider_settings = await self._resolve_provider_settings(
            tenant_context=tenant_context,
            camera_ids=camera_ids,
        )
        client = self.client or self.client_factory(self.settings, provider_settings)
        try:
            response = await client.extract_classes(
                prompt=_compose_prompt(prompt, allowed_classes),
                allowed=allowed_classes,
            )
            validated = _normalize_classes(response, allowed_classes)
            provider = (
                provider_settings.provider
                if provider_settings is not None
                else self.settings.llm_provider
            )
            model = (
                provider_settings.model
                if provider_settings is not None
                else self.settings.llm_model
            )
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

    async def _resolve_provider_settings(
        self,
        *,
        tenant_context: TenantContext | None,
        camera_ids: list[UUID] | None,
    ) -> ResolvedLLMProviderSettings | None:
        if self.llm_provider_resolver is None or tenant_context is None:
            return None
        camera_id = camera_ids[0] if camera_ids else None
        return await self.llm_provider_resolver.resolve_for_prompt(
            tenant_context=tenant_context,
            camera_id=camera_id,
        )


def _build_client(
    settings: Settings,
    provider_settings: ResolvedLLMProviderSettings | None = None,
) -> LLMClient:
    provider = (
        provider_settings.provider
        if provider_settings is not None
        else settings.llm_provider
    ).lower()
    model = provider_settings.model if provider_settings is not None else settings.llm_model
    base_url = provider_settings.base_url if provider_settings is not None else None
    api_key = provider_settings.api_key if provider_settings is not None else None
    if provider == "openai":
        return OpenAIClient(model=model, api_key=api_key, base_url=base_url)
    if provider == "anthropic":
        return AnthropicClient(model=model, api_key=api_key, base_url=base_url)
    if provider == "gemini":
        return GeminiClient(model=model, api_key=api_key, base_url=base_url)
    if provider == "ollama":
        return OllamaClient(
            base_url=base_url or settings.llm_ollama_base_url,
            model=model,
        )
    if provider == "vllm":
        return VLLMClient(
            base_url=base_url or settings.llm_vllm_base_url,
            model=model,
        )
    raise ValueError(f"Unsupported LLM provider: {provider}")


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
