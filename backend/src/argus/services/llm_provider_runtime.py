from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

import httpx
from fastapi import HTTPException

from argus.api.contracts import LLMProviderProfileConfig, TenantContext
from argus.models.enums import OperatorConfigProfileKind
from argus.services.runtime_configuration import RuntimeOperatorConfig


@dataclass(frozen=True, slots=True)
class ResolvedLLMProviderSettings:
    profile_id: UUID | None
    profile_name: str | None
    profile_hash: str | None
    provider: str
    model: str
    base_url: str | None
    api_key: str | None
    api_key_required: bool
    secret_state: dict[str, object] | None = None


class RuntimeConfigurationResolver(Protocol):
    async def resolve_profile_for_runtime(
        self,
        tenant_context: TenantContext,
        kind: OperatorConfigProfileKind,
        *,
        camera_id: UUID | None = None,
        site_id: UUID | None = None,
        edge_node_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> RuntimeOperatorConfig: ...


class LLMProviderClient(Protocol):
    async def create_policy_draft(
        self,
        *,
        resolved: ResolvedLLMProviderSettings,
        prompt: str,
        camera_state: Mapping[str, object],
    ) -> Mapping[str, object]: ...


class OpenAICompatibleLLMProviderClient:
    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.http_client = http_client
        self.timeout = timeout

    async def create_policy_draft(
        self,
        *,
        resolved: ResolvedLLMProviderSettings,
        prompt: str,
        camera_state: Mapping[str, object],
    ) -> Mapping[str, object]:
        base_url = _openai_compatible_base_url(resolved)
        headers = {"Content-Type": "application/json"}
        if resolved.api_key:
            headers["Authorization"] = f"Bearer {resolved.api_key}"
        payload = {
            "model": resolved.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You draft camera policy changes. Return only JSON with either "
                        "a rules array or a structured_diff object. Do not include prose."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": prompt,
                            "camera_state": camera_state,
                        },
                        sort_keys=True,
                        default=str,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        client = self.http_client or httpx.AsyncClient(timeout=self.timeout)
        should_close = self.http_client is None
        try:
            response = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            return _extract_openai_compatible_mapping(response.json())
        finally:
            if should_close:
                await client.aclose()


def resolved_llm_provider_from_runtime_config(
    runtime_config: RuntimeOperatorConfig,
) -> ResolvedLLMProviderSettings:
    if runtime_config.kind is not OperatorConfigProfileKind.LLM_PROVIDER:
        raise ValueError("Runtime configuration is not an LLM provider profile.")
    config = LLMProviderProfileConfig.model_validate(runtime_config.config)
    api_key = runtime_config.secrets.get("api_key")
    if config.api_key_required and not api_key:
        raise HTTPException(
            status_code=422,
            detail=(
                "Selected LLM provider profile requires an api_key secret before "
                "prompt requests can be sent."
            ),
        )
    return ResolvedLLMProviderSettings(
        profile_id=runtime_config.profile_id,
        profile_name=runtime_config.profile_name,
        profile_hash=runtime_config.profile_hash,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        api_key=api_key,
        api_key_required=config.api_key_required,
        secret_state={
            "api_key": "present"
            if api_key
            else ("missing" if config.api_key_required else "not_required"),
            "api_key_required": config.api_key_required,
        },
    )


class LLMProviderRuntimeService:
    def __init__(self, runtime_configuration: RuntimeConfigurationResolver) -> None:
        self.runtime_configuration = runtime_configuration

    async def resolve_for_prompt(
        self,
        *,
        tenant_context: TenantContext,
        camera_id: UUID | None = None,
    ) -> ResolvedLLMProviderSettings:
        runtime_config = await self.runtime_configuration.resolve_profile_for_runtime(
            tenant_context,
            OperatorConfigProfileKind.LLM_PROVIDER,
            camera_id=camera_id,
        )
        return resolved_llm_provider_from_runtime_config(runtime_config)


LLMProviderRuntimeResolver = LLMProviderRuntimeService


def _openai_compatible_base_url(resolved: ResolvedLLMProviderSettings) -> str:
    if resolved.base_url:
        return resolved.base_url
    if resolved.provider.lower() == "openai":
        return "https://api.openai.com/v1"
    raise ValueError(
        "LLM provider profile requires base_url for OpenAI-compatible policy draft calls."
    )


def _extract_openai_compatible_mapping(body: object) -> Mapping[str, object]:
    if not isinstance(body, Mapping):
        return {"provider_response": body}
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                content = message.get("content")
                if isinstance(content, Mapping):
                    return content
                if isinstance(content, str):
                    try:
                        parsed = json.loads(content)
                    except json.JSONDecodeError:
                        return {"provider_response": content}
                    if isinstance(parsed, Mapping):
                        return parsed
                    return {"provider_response": parsed}
    return body
