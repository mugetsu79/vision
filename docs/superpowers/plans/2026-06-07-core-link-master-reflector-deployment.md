# Core Link Master Reflector Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Vezor master an optional authenticated UDP sequence reflector for edge-to-master Link Performance monitoring, with operator-controlled enablement during control-link setup.

**Architecture:** Keep edge sites as the only measurement sources. Add a deployment-scoped master reflector profile, run an authenticated UDP reflector only when that profile is enabled, extend the edge agent to send UDP sequence probes, and expose UI controls that let operators choose HTTPS-only or reflector-backed control-link monitoring. The reflector profile stores secrets server-side and target metadata stores only non-secret references.

**Tech Stack:** Python asyncio datagrams, HMAC-SHA256, FastAPI/Pydantic, SQLAlchemy/Alembic, React/TypeScript, pytest, Vitest, Ruff, mypy.

---

## File Structure

- Create `backend/src/argus/link/udp_sequence.py`: packet codec, HMAC validation, sequence statistics.
- Create `backend/src/argus/link/reflector.py`: UDP reflector protocol, listener lifecycle, CLI entrypoint.
- Create `backend/src/argus/link/reflector_profiles.py`: profile normalization, encrypted secret helpers, status helpers.
- Create `backend/src/argus/migrations/versions/0041_core_link_master_reflector_profiles.py`: reflector profile table.
- Modify `backend/src/argus/link/tables.py`: add `LinkReflectorProfile`.
- Modify `backend/src/argus/link/contracts.py`: add reflector response/request contracts.
- Modify `backend/src/argus/link/service.py`: CRUD, enable/disable, key rotation, and status for master reflector profile.
- Modify `backend/src/argus/link/api.py`: expose reflector endpoints and edge control-target helper.
- Modify `backend/src/argus/link/edge_agent.py`: add UDP sequence sender mode.
- Modify `backend/src/argus/core/config.py`: add reflector settings defaults.
- Modify `backend/src/argus/main.py`: start/stop reflector lifecycle when enabled.
- Modify `infra/install/compose/compose.master.yml`: expose UDP reflector port and env defaults.
- Modify `infra/helm/argus/values.yaml`: add reflector values.
- Modify `infra/helm/argus/templates/deployment-central-backend.yaml`: add reflector env and UDP port when enabled.
- Modify `infra/helm/argus/templates/service-backend.yaml`: expose UDP service port when enabled.
- Modify `frontend/src/components/link/types.ts`: reflector profile and target metadata types.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`: Vezor Master target mode selector and reflector fields.
- Modify `frontend/src/components/link/LinkMasterTargetPanel.tsx`: reflector availability/status.
- Modify `frontend/src/components/link/LinkProbePanel.tsx`: UDP sequence metadata display.
- Modify `frontend/src/pages/Links.test.tsx`: UI coverage.
- Update generated OpenAPI files if API schemas change.

## Task 1: UDP Sequence Codec And Statistics

**Files:**
- Create: `backend/src/argus/link/udp_sequence.py`
- Test: `backend/tests/link/test_udp_sequence.py`

- [ ] **Step 1: Write failing codec/statistics tests**

Add tests that prove:

- request and reply packets round trip with HMAC.
- bad magic/version/auth is rejected.
- sequence statistics count loss, late replies, duplicates, and out-of-order replies.
- RTT min/avg/p95/max and variation are computed from on-time unique replies.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py -q
```

Expected: FAIL because `argus.link.udp_sequence` does not exist.

- [ ] **Step 2: Implement codec and statistics**

Implement:

- `UdpSequencePacket`
- `SequenceReply`
- `UdpSequenceStats`
- `build_probe_packet(...)`
- `parse_probe_packet(...)`
- `summarize_sequence_results(...)`
- `UdpSequencePacketError`

Use packet magic `VZLP`, protocol version `1`, 16-byte session id, unsigned 64-bit sequence number, sender monotonic timestamp, nonce, and 16-byte truncated HMAC-SHA256.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py -q
python3 -m uv run ruff check src/argus/link/udp_sequence.py tests/link/test_udp_sequence.py
python3 -m uv run mypy src/argus/link/udp_sequence.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/udp_sequence.py backend/tests/link/test_udp_sequence.py
git commit -m "feat: add link udp sequence codec"
```

## Task 2: Reflector Server

**Files:**
- Create: `backend/src/argus/link/reflector.py`
- Test: `backend/tests/link/test_reflector.py`

- [ ] **Step 1: Write failing reflector tests**

Add async tests that:

- start a reflector on `127.0.0.1:0`;
- send an authenticated request packet;
- receive an authenticated reply with the same session id, sequence, sender timestamp, and nonce;
- confirm wrong-secret packets get no reply;
- confirm disabled profiles do not bind a UDP socket.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py -q
```

Expected: FAIL because `argus.link.reflector` does not exist.

- [ ] **Step 2: Implement reflector lifecycle**

Implement:

- `UdpSequenceReflectorProtocol(asyncio.DatagramProtocol)`
- `ReflectorRuntime`
- `start_reflector(...)`
- `stop_reflector(...)`
- CLI options `--bind`, `--port`, `--secret`, `--key-id`, `--rate-limit-pps`

The reflector must drop bad auth, keep reply size no larger than request size, and maintain per-source counters for packet/rate-limit telemetry.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py tests/link/test_udp_sequence.py -q
python3 -m uv run ruff check src/argus/link/reflector.py tests/link/test_reflector.py
python3 -m uv run mypy src/argus/link/reflector.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/reflector.py backend/tests/link/test_reflector.py
git commit -m "feat: add link udp reflector"
```

## Task 3: Reflector Profile Persistence

**Files:**
- Create: `backend/src/argus/migrations/versions/0041_core_link_master_reflector_profiles.py`
- Create: `backend/src/argus/link/reflector_profiles.py`
- Modify: `backend/src/argus/link/tables.py`
- Modify: `backend/src/argus/link/contracts.py`
- Modify: `backend/src/argus/link/service.py`
- Test: `backend/tests/link/test_link_service.py`

- [ ] **Step 1: Write failing persistence tests**

Add tests for:

- migration text contains `link_reflector_profiles`, `encrypted_secret`, `udp_port`, and `enabled`;
- `ensure_master_reflector_profile(...)` creates a disabled default profile for the control-plane site;
- enabling a profile generates a key id and encrypted secret;
- disabling keeps the profile but marks it disabled;
- rotating the key changes the secret and key id.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_master_reflector_profile_defaults_disabled tests/link/test_link_service.py::test_master_reflector_profile_enable_disable_and_rotate_key -q
```

Expected: FAIL because profile persistence does not exist.

- [ ] **Step 2: Implement model and service methods**

Add `LinkReflectorProfile` with:

- `id`
- `tenant_id`
- `site_id`
- `profile_kind`
- `enabled`
- `mode`
- `public_address`
- `bind_address`
- `udp_port`
- `key_id`
- `encrypted_secret`
- `allowed_edge_site_ids`
- `allowed_source_cidrs`
- `rate_limit_pps_per_source`
- `last_status`
- `last_error`
- timestamps

Add service methods:

- `ensure_master_reflector_profile(...)`
- `get_master_reflector_profile(...)`
- `update_master_reflector_profile(...)`
- `enable_master_reflector_profile(...)`
- `disable_master_reflector_profile(...)`
- `rotate_master_reflector_key(...)`

Encrypt secrets with the existing config encryption key path used by configuration-sensitive data. If no helper exists, create a focused helper in `reflector_profiles.py` and test round trip.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py -q
python3 -m uv run ruff check src/argus/link tests/link/test_link_service.py
python3 -m uv run mypy src/argus/link
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/migrations/versions/0041_core_link_master_reflector_profiles.py backend/src/argus/link/tables.py backend/src/argus/link/contracts.py backend/src/argus/link/reflector_profiles.py backend/src/argus/link/service.py backend/tests/link/test_link_service.py
git commit -m "feat: persist master link reflector profile"
```

## Task 4: Reflector API And Control-Target Helper

**Files:**
- Modify: `backend/src/argus/link/api.py`
- Test: `backend/tests/api/test_link_routes.py`

- [ ] **Step 1: Write failing API tests**

Add tests that:

- `GET /api/v1/link/reflectors/master` returns the disabled default profile.
- admin can enable, disable, update, and rotate key.
- viewer cannot mutate profile.
- `POST /api/v1/link/sites/{edge_site_id}/control-targets/master` creates HTTPS-only target metadata.
- the same helper creates UDP reflector target metadata when profile is enabled.
- the helper rejects master/control-plane sites as source sites with `409`.
- UDP reflector mode rejects when the master profile is disabled.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py::test_master_reflector_profile_api_defaults_disabled tests/api/test_link_routes.py::test_control_target_helper_rejects_udp_when_reflector_disabled -q
```

Expected: FAIL before the endpoints exist.

- [ ] **Step 2: Implement API models and routes**

Add request/response models for:

- `LinkReflectorProfileResponse`
- `LinkReflectorProfileUpdate`
- `LinkControlTargetMode`: `https_only`, `udp_reflector`, `https_and_udp_reflector`
- `LinkMasterControlTargetCreate`

Add routes under existing Link router. All mutation routes require admin/operator-equivalent write permission already used by link config routes.

The control-target helper writes structured monitoring target metadata and never writes raw JSON strings.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link/api.py tests/api/test_link_routes.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/api.py backend/tests/api/test_link_routes.py
git commit -m "feat: expose master link reflector controls"
```

## Task 5: Master Runtime And Deployment Manifests

**Files:**
- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/src/argus/main.py`
- Modify: `infra/install/compose/compose.master.yml`
- Modify: `infra/helm/argus/values.yaml`
- Modify: `infra/helm/argus/templates/deployment-central-backend.yaml`
- Modify: `infra/helm/argus/templates/service-backend.yaml`
- Test: `backend/tests/test_app_lifecycle.py` or closest existing app lifecycle test file
- Test: `backend/tests/link/test_reflector.py`

- [ ] **Step 1: Write failing runtime/deployment tests**

Add tests that:

- `Settings` defaults reflector to disabled, bind `0.0.0.0`, port `8622`, rate limit `100`;
- app startup does not bind when disabled;
- app startup starts a reflector runtime when enabled and a secret exists;
- app shutdown closes the UDP transport;
- compose/helm files contain reflector env defaults and UDP port mapping.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py tests/test_app_lifecycle.py -q
```

Expected: FAIL until settings/lifecycle are wired.

- [ ] **Step 2: Implement runtime wiring**

Add settings:

- `link_reflector_enabled: bool = False`
- `link_reflector_bind_address: str = "0.0.0.0"`
- `link_reflector_public_address: str | None = None`
- `link_reflector_port: int = 8622`
- `link_reflector_key_id: str = "master-reflector-default"`
- `link_reflector_secret: SecretStr | None = None`
- `link_reflector_rate_limit_pps: int = 100`

In app startup, start reflector only when enabled and a secret is available. In shutdown, stop it. Store runtime status on `app.state.link_reflector_runtime` so the API can report listener status.

Update Compose and Helm:

- preserve disabled default;
- expose `${VEZOR_LINK_REFLECTOR_PORT:-8622}:8622/udp` only for the reflector service/profile path;
- add env passthrough for the settings above.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_reflector.py tests/test_app_lifecycle.py -q
python3 -m uv run ruff check src/argus/core/config.py src/argus/main.py tests/link/test_reflector.py tests/test_app_lifecycle.py
python3 -m uv run mypy src/argus/link src/argus/main.py
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/core/config.py backend/src/argus/main.py backend/tests/link/test_reflector.py backend/tests/test_app_lifecycle.py infra/install/compose/compose.master.yml infra/helm/argus/values.yaml infra/helm/argus/templates/deployment-central-backend.yaml infra/helm/argus/templates/service-backend.yaml
git commit -m "feat: wire master link reflector runtime"
```

## Task 6: Edge Agent UDP Sequence Sender

**Files:**
- Modify: `backend/src/argus/link/edge_agent.py`
- Test: `backend/tests/link/test_edge_agent.py`

- [ ] **Step 1: Write failing edge-agent tests**

Add tests for:

- `parse_args` accepts `--method udp_sequence`, `--reflector`, `--reflector-port`, `--reflector-key-id`, `--reflector-secret`, `--packet-spacing-ms`, and `--loss-timeout-ms`.
- `run_udp_sequence_probe` sends N packets and computes stats from replies.
- payload builder includes `method: "udp_sequence"` and sequence metadata.

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py -q
```

Expected: FAIL because only ICMP mode is supported.

- [ ] **Step 2: Implement sender mode**

Add:

- method selection with `icmp_sequence` default;
- UDP sequence send/receive loop;
- packet spacing;
- timeout/late reply handling;
- DSCP setting where supported;
- payload mapping from `UdpSequenceStats` to the existing edge sample route.

Do not run throughput tests automatically from interval monitoring. This task is packet-loss/RTT/jitter only.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_edge_agent.py tests/link/test_udp_sequence.py tests/link/test_reflector.py -q
python3 -m uv run ruff check src/argus/link/edge_agent.py tests/link/test_edge_agent.py
python3 -m uv run mypy src/argus/link
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/edge_agent.py backend/tests/link/test_edge_agent.py
git commit -m "feat: add edge agent udp sequence probes"
```

## Task 7: Frontend Control-Link Enablement

**Files:**
- Modify: `frontend/src/components/link/types.ts`
- Modify: `frontend/src/components/link/LinkActionDialogs.tsx`
- Modify: `frontend/src/components/link/LinkMasterTargetPanel.tsx`
- Modify: `frontend/src/components/link/LinkProbePanel.tsx`
- Modify: `frontend/src/pages/Links.test.tsx`

- [ ] **Step 1: Write failing UI tests**

Add tests that:

- master target panel shows reflector disabled/listening status.
- edge Add link path flow exposes `Vezor Master` control-link mode choices.
- UDP reflector choice is disabled when profile is disabled.
- enabling profile reveals UDP reflector target fields.
- saving `HTTPS + UDP reflector` creates structured target metadata with `reflector_profile_id`, address, port, packet count, timeout, spacing, and key id.
- sample history displays received/sent, loss, RTT average, RTT variation, late, duplicate, and out-of-order counts.

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: FAIL before UI support exists.

- [ ] **Step 2: Implement UI**

Add:

- reflector profile fetch/mutation hooks or local API calls matching existing Link page patterns;
- master panel status rows and admin enable/disable/rotate actions;
- control-link mode selector in the target/link dialog;
- disabled-state copy when reflector is unavailable;
- structured target payload builder;
- UDP sequence sample summary formatting.

Keep policy and target configuration as fields, not raw JSON.

- [ ] **Step 3: Run GREEN**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/link/types.ts frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/LinkMasterTargetPanel.tsx frontend/src/components/link/LinkProbePanel.tsx frontend/src/pages/Links.test.tsx
git commit -m "feat: add master reflector control link UI"
```

## Task 8: API Generation, End-To-End Verification, And Push

**Files:**
- Modify if changed: `frontend/src/lib/openapi.json`
- Modify if changed: `frontend/src/lib/api.generated.ts`
- Modify: docs only if implementation details changed from this plan

- [ ] **Step 1: Regenerate OpenAPI**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.scripts.export_openapi_schema ../frontend/src/lib/openapi.json
```

- [ ] **Step 2: Regenerate frontend API types**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm generate:api
```

- [ ] **Step 3: Full scoped verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_udp_sequence.py tests/link/test_reflector.py tests/link/test_edge_agent.py tests/link/test_link_service.py tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link src/argus/core/config.py src/argus/main.py tests/link tests/api/test_link_routes.py
python3 -m uv run mypy src/argus/link src/argus/main.py

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build

cd /Users/yann.moren/vision
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Commit generated/schema changes**

```bash
cd /Users/yann.moren/vision
git status --short
git add frontend/src/lib/openapi.json frontend/src/lib/api.generated.ts docs/superpowers/specs/2026-06-07-core-link-master-reflector-deployment-design.md docs/superpowers/plans/2026-06-07-core-link-master-reflector-deployment.md
git commit -m "docs: plan master link reflector deployment"
```

If generated files did not change, commit only the docs if they are still uncommitted.

- [ ] **Step 5: Push**

```bash
cd /Users/yann.moren/vision
git push origin codex/sceneops-pack-registry
```

Do not stage unrelated untracked files.

## Self-Review

- Spec coverage: deployment capability, enable/disable choice, edge-agent UDP sequence, authenticated reflector, UI status, source-site boundary, and packet-loss semantics are all mapped to tasks.
- Placeholder scan: no task relies on undefined future behavior; STAMP/TWAMP are explicitly out of scope for this implementation.
- Type consistency: reflector profile, target metadata, API helper, and UI mode names are consistent across the spec and plan.
