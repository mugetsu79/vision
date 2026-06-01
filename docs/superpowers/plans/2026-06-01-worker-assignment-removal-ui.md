# Worker Assignment Removal UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an operator remove an already configured scene worker from the UI without deleting the site, scene, camera, edge node, or historical runtime records.

**Architecture:** Use the existing Operations worker assignment model instead of hard-deleting worker history. A removal is represented by a new active worker assignment with `desired_state: "not_desired"` and `edge_node_id: null`, superseding the previous active assignment; fleet overview then renders that scene as intentionally unassigned and disables lifecycle actions until the operator assigns a worker again.

**Tech Stack:** FastAPI, SQLAlchemy, existing Operations service contracts, React, TanStack Query, Vitest, pytest.

---

## Status

Implemented on 2026-06-01 for branch
`codex/omnisight-live-video-window-sizing`.

This change stayed within the current Operations worker assignment contract and
did not introduce a new worker deletion API.

Verification completed:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operations_service.py backend/tests/api/test_operations_endpoints.py -q
corepack pnpm --dir frontend test src/hooks/use-operations.test.ts src/components/operations/SupervisorLifecycleControls.test.tsx src/pages/Settings.test.tsx
corepack pnpm --dir frontend build
```

## Recommended Execution Mode

Implement this sequentially, one task after the other, rather than using
parallel agents.

The backend contract must define the product truth first:
`desired_state: "not_desired"` means the worker assignment was removed while
the scene remains. Once that is correct, the frontend can render and mutate
against that behavior. Parallel implementation would create coordination risk
around `FleetCameraWorkerSummary`, `SupervisorLifecycleControls`, and
Settings-page expectations without saving much time.

Recommended order:

1. Backend fleet behavior.
2. Frontend remove action.
3. Settings integration coverage.
4. Focused backend/frontend verification.

## Current Context

The UI already supports:

- Creating and deleting sites.
- Creating and deleting scenes.
- Pairing and unpairing deployment nodes from Deployment.
- Starting, stopping, restarting, draining, and assigning scene workers from
  `SupervisorLifecycleControls`.

The missing operator action is:

- Remove the configured worker for a scene while keeping the scene itself.

Relevant existing code:

- `frontend/src/pages/Settings.tsx` renders the Scene workers panel from
  `fleet.data.camera_workers`.
- `frontend/src/components/operations/SupervisorLifecycleControls.tsx` owns the
  current Start, Stop, Restart, Drain, and Assign worker controls.
- `frontend/src/hooks/use-operations.ts` already posts
  `WorkerAssignmentCreate` through `/api/v1/operations/worker-assignments`.
- `backend/src/argus/api/contracts.py` already defines
  `WorkerDesiredState.NOT_DESIRED` as `"not_desired"`.
- `backend/src/argus/services/supervisor_operations.py` already supersedes the
  active worker assignment when a new assignment is created.
- `backend/src/argus/services/app.py` already excludes `"not_desired"` workers
  from `summary.desired_workers`.

Important model detail:

- A scene can have a baseline `camera.edge_node_id`.
- A worker assignment can override that baseline.
- Simply deactivating an assignment can reveal the baseline `camera.edge_node_id`
  again, which would make the worker look configured after "delete".
- A `not_desired` active assignment is therefore the correct v1 tombstone: it
  explicitly says "this scene exists, but no worker is desired right now."

## Product Semantics

### Remove Worker

The operator action is named **Remove worker**.

It means:

- Keep the scene.
- Keep the site.
- Keep the edge node and its pairing state.
- Keep historical worker assignment, runtime report, model admission, and
  lifecycle request records.
- Stop counting this scene as a desired worker.
- Clear the active worker location in Operations.
- Disable lifecycle controls until a worker is assigned again.

It does not mean:

- Delete the camera/scene.
- Delete the edge node.
- Revoke node credentials.
- Hard-delete database rows.
- Kill arbitrary host processes from the API.

### Re-Enable Worker

The existing **Desired worker location** selector and **Assign worker** button
re-enable the worker by creating a new active assignment that supersedes the
`not_desired` tombstone.

Expected re-enable states:

- Selecting an edge node posts `desired_state: "supervised"` and that
  `edge_node_id`.
- Selecting central/manual posts `desired_state: "manual"` and
  `edge_node_id: null`.

## Options Considered

### Option A: Use `not_desired` Assignment Tombstones

Use the existing `/api/v1/operations/worker-assignments` endpoint to create a
new active assignment:

```json
{
  "camera_id": "<camera id>",
  "edge_node_id": null,
  "desired_state": "not_desired"
}
```

Pros:

- Uses an existing API contract.
- No OpenAPI generation required.
- Preserves history.
- Works even when the Jetson is offline.
- Can suppress a scene-level `camera.edge_node_id` without editing the scene.

Cons:

- The database still has an active assignment row, because the tombstone is the
  removal marker.
- Fleet overview needs a small truth fix so removed workers do not keep
  lifecycle actions enabled.

Recommendation: **Use this for the current branch.**

### Option B: Add An Explicit Delete/Deactivate Endpoint

Add `DELETE /api/v1/operations/worker-assignments/{assignment_id}` or
`POST /api/v1/operations/worker-assignments/{assignment_id}/remove`.

Pros:

- More obvious API semantics.
- Can return a first-class removal response.

Cons:

- Does not solve scene-level `camera.edge_node_id` fallback by itself.
- Requires generated API updates and more backend surface.
- Still should avoid hard deletes, so it would likely create the same
  `not_desired` tombstone internally.

Recommendation: defer unless API clarity becomes a reviewer concern.

### Option C: Hard Delete Worker Rows Or Edge Nodes

Remove `worker_assignments`, runtime reports, or deployment nodes directly.

Pros:

- Superficially matches the word "delete".

Cons:

- Orphans operational history.
- Breaks auditability.
- Confuses node unpairing with scene worker removal.
- Risks hiding why a scene was running before.

Recommendation: reject.

## User Experience

Add a **Remove worker** button inside
`SupervisorLifecycleControls`, next to the assignment controls rather than next
to Deployment node unpairing.

Button behavior:

- Hidden or disabled when `worker.desired_state === "not_desired"`.
- Enabled for workers that are currently `manual`, `desired`, or `supervised`.
- Uses a destructive confirmation dialog.
- Calls the existing worker assignment mutation with
  `desired_state: "not_desired"` and `edge_node_id: null`.
- Resets the local desired-location select to central/manual after success.
- Invalidates Operations and Cameras through the existing mutation behavior.

Confirmation copy:

```text
Remove worker assignment for <scene name>? This keeps the scene and deployment node, but Operations will no longer desire a worker for this scene until you assign one again.
```

If the runtime is currently `running`, `starting`, `draining`, or `stale`, the
same confirmation can add:

```text
Use Stop or Drain first if you need the supervisor to shut down the current process before removing the assignment.
```

Removed worker copy:

```text
Worker assignment removed. Assign a worker location to enable processing again.
```

## Backend Behavior

Fleet overview should treat an active `not_desired` assignment as an explicit
operator removal.

Expected `FleetCameraWorkerSummary` for a removed worker:

- `desired_state`: `"not_desired"`
- `node_id`: `null`
- `node_hostname`: `null`
- `lifecycle_owner`: `"none"`
- `allowed_lifecycle_actions`: `[]`
- `detail`: `"Worker assignment removed. Assign a worker location to enable processing again."`
- `assignment`: the active tombstone assignment response
- `runtime_report`: may still show last reported truth for diagnostics
- `latest_lifecycle_request`: may still show last historical request

Expected `FleetSummary`:

- `desired_workers` does not count removed workers.
- `running_workers` may still count a fresh running runtime report if the
  supervisor has not stopped yet; this preserves reported truth.

## Implementation Tasks

### Task 1: Backend Fleet Truth For Removed Assignments

**Files:**

- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_operations_service.py`

- [x] **Step 1: Add a failing service test**

Add a test that creates an edge scene with a baseline `camera.edge_node_id` and
an active worker assignment with:

```python
desired_state=WorkerDesiredState.NOT_DESIRED.value
edge_node_id=None
active=True
```

Expected assertions:

```python
assert response.summary.desired_workers == 0
assert worker.desired_state == WorkerDesiredState.NOT_DESIRED
assert worker.node_id is None
assert worker.node_hostname is None
assert worker.lifecycle_owner == "none"
assert worker.allowed_lifecycle_actions == []
assert worker.detail == (
    "Worker assignment removed. Assign a worker location to enable processing again."
)
assert worker.assignment is not None
assert worker.assignment.active is True
```

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operations_service.py -q
```

Expected before implementation: fail because removed assignments still inherit
normal lifecycle controls or scene-level edge ownership.

- [x] **Step 2: Implement removed-assignment override**

In `OperationsService.get_fleet_overview`, after loading the active assignment,
calculate:

```python
assignment_removed = (
    assignment is not None
    and WorkerDesiredState(assignment.desired_state) is WorkerDesiredState.NOT_DESIRED
)
```

When `assignment_removed` is true, force these values and skip
`resolve_worker_operations_controls`:

```python
desired = WorkerDesiredState.NOT_DESIRED
assigned_edge_node_id = None
owner = "none"
detail = "Worker assignment removed. Assign a worker location to enable processing again."
controls = None
```

When `assignment_removed` is false, keep the existing runtime configuration and
control-resolution path.

Do not remove `runtime_report`, `latest_lifecycle_request`, or
`latest_model_admission`; those remain useful diagnostics.

- [x] **Step 3: Verify backend service tests**

Run:

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operations_service.py -q
```

Expected: pass.

### Task 2: UI Remove Worker Action

**Files:**

- Modify: `frontend/src/components/operations/SupervisorLifecycleControls.tsx`
- Modify: `frontend/src/components/operations/SupervisorLifecycleControls.test.tsx`

- [x] **Step 1: Add a failing component test**

Add a test that renders a supervised worker, confirms the removal, clicks
**Remove worker**, and expects:

```ts
expect(assignmentMutateAsync).toHaveBeenCalledWith({
  camera_id: "00000000-0000-0000-0000-000000000101",
  edge_node_id: null,
  desired_state: "not_desired",
});
```

Also assert `window.confirm` was called with copy that includes
`Remove worker assignment for Driveway`.

Run:

```bash
corepack pnpm --dir frontend test src/components/operations/SupervisorLifecycleControls.test.tsx
```

Expected before implementation: fail because there is no remove button.

- [x] **Step 2: Add the remove action**

In `SupervisorLifecycleControls.tsx`:

- import `Trash2` from `lucide-react`
- add `const workerRemoved = worker.desired_state === "not_desired";`
- add `removeWorkerAssignment`
- update change detection so a removed worker can be re-enabled to
  central/manual even when `targetNodeId` is still empty

Implementation shape:

```ts
const selectedDesiredState = targetNodeId ? "supervised" : "manual";
const desiredStateChanged = selectedDesiredState !== worker.desired_state;
const targetChanged =
  targetNodeId !== (worker.node_id ?? "") || desiredStateChanged;

async function removeWorkerAssignment() {
  const runningCopy = ["running", "starting", "draining", "stale"].includes(
    worker.runtime_status,
  )
    ? " Use Stop or Drain first if you need the supervisor to shut down the current process before removing the assignment."
    : "";
  const confirmed = window.confirm(
    `Remove worker assignment for ${worker.camera_name}? This keeps the scene and deployment node, but Operations will no longer desire a worker for this scene until you assign one again.${runningCopy}`,
  );
  if (!confirmed) return;

  await assignment.mutateAsync({
    camera_id: worker.camera_id,
    edge_node_id: null,
    desired_state: "not_desired",
  });
  setTargetNodeId("");
}
```

Add a secondary/destructive-looking button in the assignment control row:

```tsx
<Button
  type="button"
  onClick={() => void removeWorkerAssignment()}
  disabled={workerRemoved || assignment.isPending}
  variant="secondary"
  className="self-end border-[#5f2630] bg-[#2a0d14]/60 text-[#ffb4c2] hover:border-[#9b4052] hover:text-[#ffe6ea]"
>
  <Trash2 className="mr-2 size-4" />
  {workerRemoved ? "Worker removed" : "Remove worker"}
</Button>
```

- [x] **Step 3: Guard assignment/lifecycle actions for removed workers**

Make sure lifecycle buttons are disabled when `workerRemoved` is true.

Use:

```ts
disabled={
  workerRemoved ||
  !allowedActions.has(action) ||
  !admissionAllowsAction(worker, action) ||
  lifecycle.isPending
}
```

Keep **Assign worker** enabled when the operator chooses a new target or
central/manual value that changes the desired state away from removed. The
`desiredStateChanged` logic above is what makes central/manual re-enable work
when both `worker.node_id` and `targetNodeId` are empty.

- [x] **Step 4: Verify component tests**

Run:

```bash
corepack pnpm --dir frontend test src/components/operations/SupervisorLifecycleControls.test.tsx
```

Expected: pass.

### Task 3: Integration Coverage For Settings Operations

**Files:**

- Modify: `frontend/src/pages/Settings.test.tsx`

- [x] **Step 1: Add a Settings-level regression**

Add or extend a test for the Scene workers panel to show that:

- A removed worker displays `not_desired`.
- The panel copy includes the removed-worker detail.
- There is still a path to assign the worker again.

Run:

```bash
corepack pnpm --dir frontend test src/pages/Settings.test.tsx
```

Expected before implementation: fail if removed-worker details or controls are
not surfaced correctly.

- [x] **Step 2: Adjust UI copy only if needed**

If `SupervisorLifecycleControls` already renders the backend detail clearly,
do not add extra Settings-page copy. Keep the UI compact.

- [x] **Step 3: Verify Settings tests**

Run:

```bash
corepack pnpm --dir frontend test src/pages/Settings.test.tsx
```

Expected: pass.

### Task 4: Full Focused Verification

**Files:**

- No additional files expected.

- [x] **Step 1: Run backend Operations tests**

```bash
python3 -m uv run --project backend pytest backend/tests/services/test_operations_service.py backend/tests/api/test_operations_endpoints.py -q
```

Expected: pass.

- [x] **Step 2: Run frontend Operations tests**

```bash
corepack pnpm --dir frontend test src/hooks/use-operations.test.ts src/components/operations/SupervisorLifecycleControls.test.tsx src/pages/Settings.test.tsx
```

Expected: pass.

- [x] **Step 3: Build frontend**

```bash
corepack pnpm --dir frontend build
```

Expected: pass.

- [x] **Step 4: Commit**

```bash
git add backend/src/argus/services/app.py backend/tests/services/test_operations_service.py frontend/src/components/operations/SupervisorLifecycleControls.tsx frontend/src/components/operations/SupervisorLifecycleControls.test.tsx frontend/src/pages/Settings.test.tsx docs/superpowers/plans/2026-06-01-worker-assignment-removal-ui.md
git commit -m "feat(operations): remove configured scene workers"
```

## Manual QA

On the MacBook test build after pulling the branch and rebuilding:

1. Open Control -> Operations.
2. Find a scene worker assigned to the Jetson or central/manual runtime.
3. Click **Remove worker**.
4. Confirm the dialog.
5. Confirm the worker card changes to `not_desired` or equivalent removed copy.
6. Confirm lifecycle buttons are disabled.
7. Confirm `Planned workers` decrements.
8. Confirm the scene still exists in Control -> Scenes.
9. Assign a worker location again.
10. Confirm the worker returns to `manual` or `supervised` and can be started
    through normal lifecycle controls.

## Risks And Follow-Ups

- If product reviewers dislike tombstone semantics, add the explicit remove
  endpoint later while keeping the same internal `not_desired` assignment.
- If removed workers should disappear from the Scene workers list entirely,
  add a filter toggle such as **Show removed workers**. Do not hide them by
  default until there is a clear re-enable path elsewhere.
- If a running supervisor process must be stopped automatically before removal,
  add a future **Stop and remove** workflow that creates a `stop` lifecycle
  request and only writes the removal tombstone after completion.
