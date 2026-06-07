# Core Link Logical Paths And Policy Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace confusing physical-network "connection" UI with logical Link paths, monitoring target metadata, and field-based policy controls.

**Architecture:** Keep existing Core Link routes and database schema. Store new logical path details in existing connection `metadata`, validate the generated policy shape in the core link service, and replace frontend raw JSON editing with typed controls that serialize to the existing policy object.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, SQLAlchemy async service tests, React 19, TypeScript, TanStack Query, Vitest, Testing Library, pnpm, uv.

---

## Constraints

- Preserve CC-1 through CC-10 constraints from FleetOps/Core Link plans.
- Do not add maritime or traffic nouns to core link contracts, routes, services, page copy, or tests.
- Do not implement real probing runtime, SD-WAN controller integrations, credentials, or discovery.
- Do not add migrations. Use existing connection `metadata`.
- Do not expose raw policy JSON in the Link workspace.
- Do not stage unrelated scratch files or directories.

## File Structure

Backend:

- Modify `backend/src/argus/link/service.py`
  - Add policy validation helpers.
  - Include new budget behavior flags in default policy.
- Modify `backend/tests/link/test_link_service.py`
  - Add validation/default policy tests.

Frontend:

- Modify `frontend/src/components/link/types.ts`
  - Add metadata parsing/building helpers for Link path model, visibility, and monitoring targets.
  - Add policy parse/build helpers.
- Modify `frontend/src/components/link/LinkActionDialogs.tsx`
  - Rename operator-facing copy to Link path.
  - Add link model, visibility, external reference, and monitoring target controls.
  - Persist these values through `metadata`.
- Modify `frontend/src/components/link/LinkConnectionsPanel.tsx`
  - Rename panel/controls to Link paths.
  - Render model, visibility, provider/reference, target count.
- Modify `frontend/src/components/link/LinkBudgetPolicyPanel.tsx`
  - Replace raw JSON editor with field controls.
- Modify `frontend/src/pages/Links.test.tsx`
  - Add/adjust TDD tests for provider-managed SD-WAN path, inventory-only path, row rendering, and policy controls.

## Task 1: Backend Policy Validation

- [ ] **Step 1: Write failing backend tests**

Add to `backend/tests/link/test_link_service.py`:

```python
def test_default_policy_includes_budget_behavior_flags(link_service: LinkService) -> None:
    policy = link_service.get_policy(
        tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
        site_id=UUID("00000000-0000-4000-8000-000000000002"),
    )

    assert policy == {
        "priority_order": ["safety", "evidence", "telemetry", "bulk"],
        "backpressure": {
            "degraded_pauses": ["telemetry", "bulk"],
            "dark_allows": ["safety"],
            "pause_bulk_when_daily_budget_exhausted": True,
            "avoid_metered_for_bulk_when_budget_exhausted": True,
        },
    }


def test_policy_rejects_unknown_lanes(link_service: LinkService) -> None:
    with pytest.raises(ValueError, match="Invalid link policy lane"):
        link_service.put_policy(
            tenant_id=UUID("00000000-0000-4000-8000-000000000001"),
            site_id=UUID("00000000-0000-4000-8000-000000000002"),
            policy={"priority_order": ["safety", "evidence", "bulk", "unknown"]},
        )
```

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py::test_default_policy_includes_budget_behavior_flags tests/link/test_link_service.py::test_policy_rejects_unknown_lanes -q
```

Expected: FAIL because defaults do not include the flags and invalid lanes are accepted.

- [ ] **Step 2: Implement minimal policy validation**

In `backend/src/argus/link/service.py`:

- Add ` _validate_policy(policy: JsonObject) -> JsonObject`.
- Validate `priority_order`, `backpressure.degraded_pauses`, and `backpressure.dark_allows` only when present.
- Return a shallow copy.
- Call it from `put_policy` and `aput_policy`.
- Extend `_default_policy()`.

- [ ] **Step 3: Verify backend task**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py -q
```

Expected: PASS.

## Task 2: Link Path Metadata UI

- [ ] **Step 1: Write failing frontend tests**

In `frontend/src/pages/Links.test.tsx`, add tests:

```tsx
test("link path form saves a provider-managed path with a monitoring target", async () => {
  const user = userEvent.setup();
  const createConnection = vi.fn().mockResolvedValue({});
  mockLinkHooks({ summaries: [createSummary({ site_id: "site-1" })], createConnection });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  await user.click(await screen.findByRole("button", { name: /add link path/i }));
  await user.type(screen.getByLabelText(/link path label/i), "Managed SD-WAN overlay");
  await user.selectOptions(screen.getByLabelText(/link model/i), "provider_managed");
  await user.type(screen.getByLabelText(/provider/i), "Acme MSP");
  await user.type(screen.getByLabelText(/external reference/i), "CH-ZRH-01 edge pair");
  await user.selectOptions(screen.getByLabelText(/visibility/i), "handoff_only");
  await user.click(screen.getByRole("button", { name: /add monitoring target/i }));
  await user.type(screen.getByLabelText(/target label/i), "Vezor ingest");
  await user.type(screen.getByLabelText(/target address/i), "ingest.example.vezor");
  await user.selectOptions(screen.getByLabelText(/probe type/i), "https");
  await user.clear(screen.getByLabelText(/target port/i));
  await user.type(screen.getByLabelText(/target port/i), "443");
  await user.click(screen.getByRole("button", { name: /save link path/i }));

  expect(createConnection).toHaveBeenCalledWith(
    expect.objectContaining({
      label: "Managed SD-WAN overlay",
      transport_kind: "other",
      provider: "Acme MSP",
      metadata: expect.objectContaining({
        link_model: "provider_managed",
        visibility: "handoff_only",
        external_reference: "CH-ZRH-01 edge pair",
        monitoring_targets: [
          expect.objectContaining({
            label: "Vezor ingest",
            address: "ingest.example.vezor",
            probe_type: "https",
            port: 443,
          }),
        ],
      }),
    }),
  );
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx --testNamePattern "provider-managed"
```

Expected: FAIL because controls do not exist.

- [ ] **Step 2: Implement metadata helpers and dialog controls**

Add helpers in `types.ts`, then wire `LinkActionDialogs.tsx` to build `metadata`.

- [ ] **Step 3: Verify task**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
```

Expected: PASS.

## Task 3: Field-Based Policy Controls

- [ ] **Step 1: Write failing frontend policy tests**

Replace the invalid JSON test with:

```tsx
test("policy controls save generated policy without exposing JSON", async () => {
  const user = userEvent.setup();
  const updatePolicies = vi.fn().mockResolvedValue({});
  mockLinkHooks({
    summaries: [createSummary({ site_id: "site-1" })],
    policies: {
      priority_order: ["safety", "evidence", "telemetry", "bulk"],
      backpressure: {
        degraded_pauses: ["telemetry", "bulk"],
        dark_allows: ["safety"],
      },
    },
    updatePolicies,
  });

  renderWithProviders(<Links />, { route: "/links?site=site-1" });

  expect(screen.queryByLabelText(/policy json/i)).not.toBeInTheDocument();
  await user.click(await screen.findByRole("button", { name: /move evidence down/i }));
  await user.click(screen.getByRole("checkbox", { name: /pause evidence when degraded/i }));
  await user.click(screen.getByRole("button", { name: /save policy/i }));

  expect(updatePolicies).toHaveBeenCalledWith({
    policy: expect.objectContaining({
      priority_order: ["safety", "telemetry", "evidence", "bulk"],
      backpressure: expect.objectContaining({
        degraded_pauses: ["telemetry", "bulk", "evidence"],
      }),
    }),
  });
});
```

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx --testNamePattern "policy controls"
```

Expected: FAIL because JSON editor is still present.

- [ ] **Step 2: Implement policy controls**

In `types.ts`, add `normalizeLinkPolicy` and `buildLinkPolicy`.

In `LinkBudgetPolicyPanel.tsx`, replace the textarea with:

- lane order list with Move up/down buttons
- degraded pause checkboxes
- dark allow checkboxes
- budget behavior checkboxes

- [ ] **Step 3: Verify task**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build
```

Expected: PASS.

## Task 4: Final Verification And Commit

- [ ] **Step 1: Full targeted verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/link/test_link_service.py tests/api/test_link_routes.py -q
python3 -m uv run ruff check src/argus/link tests/link tests/api/test_link_routes.py
python3 -m uv run mypy src/argus/link

cd /Users/yann.moren/vision/frontend
corepack pnpm test --run src/pages/Links.test.tsx
corepack pnpm lint
corepack pnpm build
```

Expected: PASS.

- [ ] **Step 2: Commit and push**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/link/service.py backend/tests/link/test_link_service.py frontend/src/components/link/types.ts frontend/src/components/link/LinkActionDialogs.tsx frontend/src/components/link/LinkConnectionsPanel.tsx frontend/src/components/link/LinkBudgetPolicyPanel.tsx frontend/src/pages/Links.test.tsx docs/superpowers/plans/2026-06-07-core-link-logical-paths-and-policy-controls.md
git commit -m "feat: refine core link path controls"
git push origin codex/sceneops-pack-registry
```

## Plan Self-Review

- Spec coverage: logical path model, targets, policy fields, validation, and tests are covered.
- Placeholder scan: no TODO/TBD placeholders are present.
- Type consistency: metadata keys and policy keys match the spec.
