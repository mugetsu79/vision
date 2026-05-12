from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

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
