from __future__ import annotations

from uuid import uuid4

import pytest

from argus.api.contracts import TenantContext
from argus.core.security import AuthenticatedUser
from argus.models.enums import PolicyDraftStatus, RoleEnum
from argus.services.llm_provider_runtime import ResolvedLLMProviderSettings
from argus.services.policy_drafts import (
    PolicyDraftCompiler,
    PolicyDraftService,
    PolicyDraftState,
    apply_policy_draft,
    approve_policy_draft,
    assert_policy_draft_baseline_current,
    build_policy_draft_ledger_hash,
    reject_policy_draft,
)


@pytest.mark.asyncio
async def test_prompt_creates_draft_diff_without_applying_camera_change() -> None:
    camera_state = {
        "runtime_vocabulary": ["person"],
        "recording_policy": {"enabled": False, "mode": "event_clip"},
        "detection_regions": [],
        "incident_rules": [],
    }
    compiler = PolicyDraftCompiler(llm_provider_resolver=None)

    draft = await compiler.compile(
        tenant_context=_tenant_context(),
        camera_id=uuid4(),
        prompt="Watch forklifts in the dock zone and record clips",
        camera_state=camera_state,
        use_llm=False,
    )

    assert draft.status is PolicyDraftStatus.DRAFT
    assert draft.structured_diff["runtime_vocabulary"]["add"] == ["forklift"]
    assert draft.structured_diff["recording_policy"]["after"]["enabled"] is True
    assert draft.structured_diff["rule_changes"][0]["action"] == "record_clip"
    assert draft.structured_diff["rule_changes"][0]["predicate"]["zone_ids"] == ["dock"]
    assert camera_state["runtime_vocabulary"] == ["person"]
    assert camera_state["recording_policy"]["enabled"] is False


@pytest.mark.asyncio
async def test_policy_draft_records_selected_llm_provider_metadata() -> None:
    resolver = _FakeLLMProviderResolver(
        ResolvedLLMProviderSettings(
            profile_id=uuid4(),
            profile_name="Camera OpenAI",
            profile_hash="c" * 64,
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key=None,
            api_key_required=False,
        )
    )
    compiler = PolicyDraftCompiler(llm_provider_resolver=resolver)
    tenant_context = _tenant_context()
    camera_id = uuid4()

    draft = await compiler.compile(
        tenant_context=tenant_context,
        camera_id=camera_id,
        prompt="Create a hardhat rule but do not apply it",
        camera_state={"runtime_vocabulary": [], "recording_policy": {}},
        use_llm=True,
    )

    assert resolver.calls == [(tenant_context, camera_id)]
    assert draft.metadata["llm_provider"] == "openai"
    assert draft.metadata["llm_model"] == "gpt-4.1-mini"
    assert draft.metadata["llm_profile_hash"] == "c" * 64


@pytest.mark.asyncio
async def test_policy_draft_records_redacted_llm_secret_state() -> None:
    resolver = _FakeLLMProviderResolver(
        ResolvedLLMProviderSettings(
            profile_id=uuid4(),
            profile_name="Camera OpenAI",
            profile_hash="c" * 64,
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key="super-secret-key",
            api_key_required=True,
        )
    )
    compiler = PolicyDraftCompiler(llm_provider_resolver=resolver)

    draft = await compiler.compile(
        tenant_context=_tenant_context(),
        camera_id=uuid4(),
        prompt="Create a hardhat rule but do not apply it",
        camera_state={"runtime_vocabulary": [], "recording_policy": {}},
        use_llm=True,
    )

    assert draft.metadata["llm_secret_state"] == {
        "api_key": "present",
        "api_key_required": True,
    }
    assert "super-secret-key" not in str(draft.metadata)


@pytest.mark.asyncio
async def test_policy_draft_uses_resolved_llm_provider() -> None:
    resolver = _FakeLLMProviderResolver(
        ResolvedLLMProviderSettings(
            profile_id=uuid4(),
            profile_name="Camera OpenAI",
            profile_hash="c" * 64,
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key="sk-runtime",
            api_key_required=True,
        )
    )
    provider_client = _MockLLMProviderClient()
    provider_client.queue_response(
        {"rules": [{"name": "High visibility worker near gate"}]}
    )
    service = PolicyDraftService(
        session_factory=object(),  # type: ignore[arg-type]
        audit_logger=_FakeAuditLogger(),
        llm_provider_resolver=resolver,
        llm_provider_client=provider_client,
    )
    tenant_context = _tenant_context()
    camera_id = uuid4()
    camera_state = {"runtime_vocabulary": ["person"], "recording_policy": {}}

    draft = await service.compiler.compile(
        tenant_context=tenant_context,
        camera_id=camera_id,
        prompt="alert on workers near gate",
        camera_state=camera_state,
        use_llm=True,
    )

    assert resolver.calls == [(tenant_context, camera_id)]
    assert provider_client.calls == [
        (resolver.resolved, "alert on workers near gate", camera_state)
    ]
    assert draft.metadata["llm_assistance"] == "provider_assisted"
    assert draft.metadata["llm_provider"] == "openai"
    assert draft.metadata["llm_model"] == "gpt-4.1-mini"
    assert draft.structured_diff["rule_changes"] == [
        {
            "name": "High visibility worker near gate",
            "incident_type": "high_visibility_worker_near_gate",
            "severity": "warning",
            "predicate": {
                "class_names": ["person"],
                "zone_ids": [],
                "min_confidence": 0.5,
                "attributes": {},
            },
            "action": "alert",
            "cooldown_seconds": 60,
        }
    ]


@pytest.mark.asyncio
async def test_malformed_provider_output_returns_deterministic_fallback_warning() -> None:
    resolver = _FakeLLMProviderResolver(_resolved_provider())
    provider_client = _MockLLMProviderClient()
    provider_client.queue_response({"unexpected": "shape"})
    compiler = PolicyDraftCompiler(
        llm_provider_resolver=resolver,
        llm_provider_client=provider_client,
    )

    draft = await compiler.compile(
        tenant_context=_tenant_context(),
        camera_id=uuid4(),
        prompt="alert on forklifts in dock",
        camera_state={"runtime_vocabulary": [], "recording_policy": {}},
        use_llm=True,
    )

    assert draft.metadata["llm_assistance"] == "provider_rejected"
    assert draft.metadata["llm_fallback"] == "deterministic"
    assert draft.metadata["llm_provider"] == "openai"
    assert draft.structured_diff["runtime_vocabulary"]["add"] == ["forklift"]
    assert draft.structured_diff["rule_changes"][0]["incident_type"] == "forklift_activity"


@pytest.mark.asyncio
async def test_policy_draft_does_not_call_provider_when_llm_disabled() -> None:
    resolver = _FakeLLMProviderResolver(_resolved_provider())
    provider_client = _MockLLMProviderClient()
    compiler = PolicyDraftCompiler(
        llm_provider_resolver=resolver,
        llm_provider_client=provider_client,
    )

    draft = await compiler.compile(
        tenant_context=_tenant_context(),
        camera_id=uuid4(),
        prompt="Watch forklifts in the dock zone and record clips",
        camera_state={
            "runtime_vocabulary": [],
            "recording_policy": {"enabled": False, "mode": "event_clip"},
        },
        use_llm=False,
    )

    assert resolver.calls == []
    assert provider_client.calls == []
    assert draft.metadata["llm_assistance"] == "disabled"
    assert draft.structured_diff["runtime_vocabulary"]["add"] == ["forklift"]


@pytest.mark.asyncio
async def test_policy_draft_falls_back_when_provider_client_unavailable() -> None:
    resolver = _FakeLLMProviderResolver(_resolved_provider())
    compiler = PolicyDraftCompiler(
        llm_provider_resolver=resolver,
        llm_provider_client=None,
    )

    draft = await compiler.compile(
        tenant_context=_tenant_context(),
        camera_id=uuid4(),
        prompt="Watch forklifts in the dock zone and record clips",
        camera_state={
            "runtime_vocabulary": [],
            "recording_policy": {"enabled": False, "mode": "event_clip"},
        },
        use_llm=True,
    )

    assert draft.metadata["llm_assistance"] == "provider_unavailable"
    assert draft.metadata["llm_fallback"] == "deterministic"
    assert draft.structured_diff["runtime_vocabulary"]["add"] == ["forklift"]


def test_policy_draft_service_injects_mock_llm_provider_client() -> None:
    provider_client = _MockLLMProviderClient()

    service = PolicyDraftService(
        session_factory=object(),  # type: ignore[arg-type]
        audit_logger=_FakeAuditLogger(),
        llm_provider_resolver=_FakeLLMProviderResolver(_resolved_provider()),
        llm_provider_client=provider_client,
    )

    assert service.compiler.llm_provider_client is provider_client


def test_policy_draft_requires_approval_before_apply() -> None:
    draft = PolicyDraftState(
        id=uuid4(),
        tenant_id=uuid4(),
        camera_id=uuid4(),
        status=PolicyDraftStatus.DRAFT,
        prompt="record forklifts",
        structured_diff={
            "runtime_vocabulary": {"add": ["forklift"]},
            "recording_policy": {"after": {"enabled": True}},
        },
        metadata={},
    )

    with pytest.raises(ValueError, match="approved"):
        apply_policy_draft(draft, camera_state={"runtime_vocabulary": []})

    approved = approve_policy_draft(draft, actor_subject="operator-1")
    applied_state = {"runtime_vocabulary": []}
    applied = apply_policy_draft(approved, camera_state=applied_state)

    assert applied.status is PolicyDraftStatus.APPLIED
    assert applied_state["runtime_vocabulary"] == ["forklift"]


def test_policy_draft_rejection_does_not_apply_changes() -> None:
    camera_state = {"runtime_vocabulary": []}
    draft = PolicyDraftState(
        id=uuid4(),
        tenant_id=uuid4(),
        camera_id=uuid4(),
        status=PolicyDraftStatus.DRAFT,
        prompt="record forklifts",
        structured_diff={"runtime_vocabulary": {"add": ["forklift"]}},
        metadata={},
    )

    rejected = reject_policy_draft(draft, actor_subject="operator-1")

    assert rejected.status is PolicyDraftStatus.REJECTED
    assert camera_state["runtime_vocabulary"] == []
    with pytest.raises(ValueError, match="approved"):
        apply_policy_draft(rejected, camera_state=camera_state)


def test_policy_draft_apply_rejects_stale_camera_baseline() -> None:
    structured_diff = {
        "scene_contract_hash": "a" * 64,
        "privacy_manifest_hash": "b" * 64,
        "runtime_vocabulary": {
            "before": ["person"],
            "add": ["forklift"],
            "after": ["person", "forklift"],
        },
        "recording_policy": {
            "before": {"enabled": False, "mode": "event_clip"},
            "after": {"enabled": True, "mode": "event_clip"},
        },
    }

    with pytest.raises(ValueError, match="stale"):
        assert_policy_draft_baseline_current(
            structured_diff,
            {
                "scene_contract_hash": "a" * 64,
                "privacy_manifest_hash": "b" * 64,
                "runtime_vocabulary": ["person", "truck"],
                "recording_policy": {"enabled": False, "mode": "event_clip"},
            },
        )


def test_policy_draft_ledger_hash_chains_transition_entries() -> None:
    first = build_policy_draft_ledger_hash(
        policy_draft_id=uuid4(),
        sequence=1,
        action="policy_draft.proposed",
        actor_subject="operator-1",
        payload={"status": "draft"},
        previous_entry_hash=None,
        occurred_at="2026-05-12T10:00:00Z",
    )
    second = build_policy_draft_ledger_hash(
        policy_draft_id=uuid4(),
        sequence=2,
        action="policy_draft.approved",
        actor_subject="operator-1",
        payload={"status": "approved"},
        previous_entry_hash=first,
        occurred_at="2026-05-12T10:01:00Z",
    )

    assert len(first) == 64
    assert len(second) == 64
    assert second != first


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


class _MockLLMProviderClient:
    def __init__(self) -> None:
        self.responses: list[dict[str, object]] = []
        self.calls: list[tuple[ResolvedLLMProviderSettings, str, dict[str, object]]] = []

    def queue_response(self, response: dict[str, object]) -> None:
        self.responses.append(response)

    async def create_policy_draft(
        self,
        *,
        resolved: ResolvedLLMProviderSettings,
        prompt: str,
        camera_state: dict[str, object],
    ) -> dict[str, object]:
        self.calls.append((resolved, prompt, camera_state))
        if not self.responses:
            raise AssertionError("No mock LLM provider response queued.")
        return self.responses.pop(0)


class _FakeAuditLogger:
    async def record(self, **kwargs):  # noqa: ANN003, ANN201
        del kwargs


def _resolved_provider() -> ResolvedLLMProviderSettings:
    return ResolvedLLMProviderSettings(
        profile_id=uuid4(),
        profile_name="Camera OpenAI",
        profile_hash="c" * 64,
        provider="openai",
        model="gpt-4.1-mini",
        base_url="https://api.openai.com/v1",
        api_key=None,
        api_key_required=False,
    )


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
            tenant_context=None,
            claims={},
        ),
    )
