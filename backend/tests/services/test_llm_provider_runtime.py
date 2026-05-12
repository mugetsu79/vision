from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from argus.api.contracts import TenantContext
from argus.core.config import Settings
from argus.core.security import AuthenticatedUser
from argus.llm.adapter import ClassFilterResponse
from argus.llm.parser import ClassFilterParser
from argus.models.enums import OperatorConfigProfileKind, RoleEnum
from argus.services.llm_provider_runtime import (
    LLMProviderRuntimeService,
    ResolvedLLMProviderSettings,
    resolved_llm_provider_from_runtime_config,
)
from argus.services.runtime_configuration import RuntimeOperatorConfig


def test_resolved_llm_provider_includes_decrypted_runtime_secret() -> None:
    profile_id = uuid4()

    resolved = resolved_llm_provider_from_runtime_config(
        RuntimeOperatorConfig(
            kind=OperatorConfigProfileKind.LLM_PROVIDER,
            profile_id=profile_id,
            profile_name="Production OpenAI",
            profile_slug="production-openai",
            profile_hash="a" * 64,
            config={
                "provider": "openai",
                "model": "gpt-4.1-mini",
                "base_url": "https://api.openai.com/v1",
                "api_key_required": True,
            },
            secrets={"api_key": "sk-runtime"},
        )
    )

    assert resolved.profile_id == profile_id
    assert resolved.profile_name == "Production OpenAI"
    assert resolved.profile_hash == "a" * 64
    assert resolved.provider == "openai"
    assert resolved.model == "gpt-4.1-mini"
    assert resolved.base_url == "https://api.openai.com/v1"
    assert resolved.api_key == "sk-runtime"
    assert resolved.api_key_required is True


def test_resolved_llm_provider_fails_closed_when_required_secret_is_missing() -> None:
    with pytest.raises(HTTPException) as exc_info:
        resolved_llm_provider_from_runtime_config(
            RuntimeOperatorConfig(
                kind=OperatorConfigProfileKind.LLM_PROVIDER,
                profile_id=uuid4(),
                profile_name="Missing OpenAI Key",
                profile_slug="missing-openai-key",
                profile_hash="b" * 64,
                config={
                    "provider": "openai",
                    "model": "gpt-4.1-mini",
                    "api_key_required": True,
                },
                secrets={},
            )
        )

    assert exc_info.value.status_code == 422
    assert "api_key" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_runtime_service_resolves_selected_profile_for_camera() -> None:
    tenant_context = _tenant_context()
    camera_id = uuid4()
    runtime_config = RuntimeOperatorConfig(
        kind=OperatorConfigProfileKind.LLM_PROVIDER,
        profile_id=uuid4(),
        profile_name="Camera OpenAI",
        profile_slug="camera-openai",
        profile_hash="c" * 64,
        config={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "api_key_required": False,
        },
        secrets={},
    )
    runtime_configuration = _FakeRuntimeConfiguration(runtime_config)
    service = LLMProviderRuntimeService(runtime_configuration)

    resolved = await service.resolve_for_prompt(
        tenant_context=tenant_context,
        camera_id=camera_id,
    )

    assert runtime_configuration.calls == [
        (tenant_context, OperatorConfigProfileKind.LLM_PROVIDER, camera_id)
    ]
    assert resolved.profile_id == runtime_config.profile_id
    assert resolved.model == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_class_filter_parser_uses_selected_llm_provider_profile() -> None:
    tenant_context = _tenant_context()
    camera_id = uuid4()
    resolver = _FakeLLMProviderResolver(
        ResolvedLLMProviderSettings(
            profile_id=uuid4(),
            profile_name="Camera vLLM",
            profile_hash="d" * 64,
            provider="vllm",
            model="qwen2.5",
            base_url="http://vllm.internal:8001",
            api_key=None,
            api_key_required=False,
        )
    )
    factory = _ClientFactory()
    parser = ClassFilterParser(
        Settings(_env_file=None),
        llm_provider_resolver=resolver,
        client_factory=factory,
    )

    result = await parser.resolve_classes(
        prompt="show cars",
        allowed_classes=["car", "person"],
        tenant_context=tenant_context,
        camera_ids=[camera_id],
    )

    assert resolver.calls == [(tenant_context, camera_id)]
    assert factory.provider_settings is resolver.resolved
    assert "User request: show cars" in factory.client.prompts[0]
    assert result.classes == ["car"]
    assert result.provider == "vllm"
    assert result.model == "qwen2.5"


class _FakeRuntimeConfiguration:
    def __init__(self, runtime_config: RuntimeOperatorConfig) -> None:
        self.runtime_config = runtime_config
        self.calls: list[tuple[TenantContext, OperatorConfigProfileKind, object]] = []

    async def resolve_profile_for_runtime(
        self,
        tenant_context: TenantContext,
        kind: OperatorConfigProfileKind,
        *,
        camera_id=None,  # noqa: ANN001
        site_id=None,  # noqa: ANN001
        edge_node_id=None,  # noqa: ANN001
        profile_id=None,  # noqa: ANN001
    ) -> RuntimeOperatorConfig:
        del site_id, edge_node_id, profile_id
        self.calls.append((tenant_context, kind, camera_id))
        return self.runtime_config


class _FakeLLMProviderResolver:
    def __init__(self, resolved: ResolvedLLMProviderSettings) -> None:
        self.resolved = resolved
        self.calls: list[tuple[TenantContext, object]] = []

    async def resolve_for_prompt(
        self,
        *,
        tenant_context: TenantContext,
        camera_id=None,  # noqa: ANN001
    ) -> ResolvedLLMProviderSettings:
        self.calls.append((tenant_context, camera_id))
        return self.resolved


class _FakeLLMClient:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def extract_classes(
        self,
        *,
        prompt: str,
        allowed: list[str],
    ) -> ClassFilterResponse:
        del allowed
        self.prompts.append(prompt)
        return ClassFilterResponse(classes=["car"])


class _ClientFactory:
    def __init__(self) -> None:
        self.client = _FakeLLMClient()
        self.provider_settings: ResolvedLLMProviderSettings | None = None

    def __call__(
        self,
        settings: Settings,
        provider_settings: ResolvedLLMProviderSettings | None,
    ) -> _FakeLLMClient:
        del settings
        self.provider_settings = provider_settings
        return self.client


def _tenant_context() -> TenantContext:
    tenant_id = uuid4()
    return TenantContext(
        tenant_id=tenant_id,
        tenant_slug="argus-dev",
        user=AuthenticatedUser(
            subject="operator-1",
            email="operator@argus.local",
            role=RoleEnum.OPERATOR,
            issuer="http://issuer",
            realm="argus-dev",
            is_superadmin=False,
            tenant_context=str(tenant_id),
            claims={},
        ),
    )
