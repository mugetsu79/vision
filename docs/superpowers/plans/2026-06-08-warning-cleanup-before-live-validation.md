# Warning Cleanup Before Live Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove known backend and frontend test warnings so live-stack validation output is high-signal and warning regressions are caught automatically.

**Architecture:** Treat each warning family as a separate root-cause fix with a narrow regression check. Backend warning fixes stay in configuration/status-constant code and backend tests; frontend warning fixes introduce shared test helpers so individual tests do not copy future flags or async `act` mechanics.

**Tech Stack:** Python 3.12, Pydantic Settings v2, FastAPI/Starlette, pytest, TypeScript, React Testing Library, React Router v6, Vitest.

---

## Spec

- Backend tests must no longer emit `directory "/run/secrets" does not exist` when local tests run outside Docker.
- Docker and installer environments must still load secrets from `/run/secrets` when that directory exists.
- Explicit `ARGUS_SECRETS_DIR=/path/to/secrets` must be honored without requiring `_secrets_dir=...` at every `Settings(...)` call site.
- Backend source must stop using deprecated `status.HTTP_422_UNPROCESSABLE_ENTITY`.
- Frontend tests must stop emitting React Router future-flag warnings.
- `VideoStream` tests must stop emitting React `act(...)` warnings.
- Add a warning gate that fails if these warnings return.
- Do not change product behavior or live-stack behavior.
- Do not stage/commit/push unless explicitly requested by the user.

## Files

- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/tests/core/test_config.py`
- Modify: `backend/tests/core/test_edge_dockerfile.py`
- Modify: `backend/src/argus/services/camera_sources.py`
- Modify: `backend/src/argus/services/query.py`
- Modify: `backend/src/argus/link/api.py`
- Create: `frontend/src/test/router.tsx`
- Modify tests using `MemoryRouter` without `future`, including:
  - `frontend/src/pages/Dashboard.test.tsx`
  - `frontend/src/pages/FleetOps.test.tsx`
  - `frontend/src/pages/FleetOpsBilling.test.tsx`
  - `frontend/src/pages/FleetOpsEvidence.test.tsx`
  - `frontend/src/pages/FleetOpsOnboarding.test.tsx`
  - `frontend/src/pages/FleetOpsSupport.test.tsx`
  - `frontend/src/pages/FleetOpsVesselDetail.test.tsx`
  - `frontend/src/pages/FleetOpsVessels.test.tsx`
  - `frontend/src/pages/FirstRun.test.tsx`
  - `frontend/src/pages/Links.test.tsx`
  - `frontend/src/pages/Settings.test.tsx`
  - `frontend/src/components/layout/AppShell.test.tsx`
  - `frontend/src/components/layout/WorkspaceTransition.test.tsx`
  - `frontend/src/components/operations/AttentionStack.test.tsx`
  - `frontend/src/components/operations/SceneIntelligenceMatrix.test.tsx`
  - any other file found by `rg -n "MemoryRouter(?![^\\n]*future=)" frontend/src -g "*.test.tsx"`
- Modify: `frontend/src/components/live/VideoStream.test.tsx`
- Create: `scripts/verify-no-test-warnings.sh`
- Modify: `scripts/run-full-validation.sh`

---

### Task 1: Backend Settings Secrets Warning

**Files:**
- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/tests/core/test_config.py`

- [ ] **Step 1: Write failing tests for local/no-secret-dir and explicit secret-dir behavior**

Add to `backend/tests/core/test_config.py`:

```python
from __future__ import annotations

import warnings

from pydantic import SecretStr

from argus.core.config import Settings


def test_default_settings_do_not_warn_when_run_secrets_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("ARGUS_SECRETS_DIR", raising=False)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Settings(_env_file=None)

    assert not [
        warning
        for warning in caught
        if "/run/secrets" in str(warning.message)
    ]


def test_settings_honor_argus_secrets_dir(monkeypatch, tmp_path) -> None:
    secrets_dir = tmp_path / "secrets"
    secrets_dir.mkdir()
    (secrets_dir / "ARGUS_RTSP_ENCRYPTION_KEY").write_text(
        "secret-from-env-dir\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ARGUS_SECRETS_DIR", str(secrets_dir))

    settings = Settings(_env_file=None)

    assert isinstance(settings.rtsp_encryption_key, SecretStr)
    assert settings.rtsp_encryption_key.get_secret_value() == "secret-from-env-dir"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend
python3 -m uv run pytest -q tests/core/test_config.py::test_default_settings_do_not_warn_when_run_secrets_is_missing tests/core/test_config.py::test_settings_honor_argus_secrets_dir
```

Expected before implementation:

- `test_default_settings_do_not_warn_when_run_secrets_is_missing` fails because Pydantic warns about `/run/secrets`.
- `test_settings_honor_argus_secrets_dir` fails because `ARGUS_SECRETS_DIR` is not used to configure `Settings` secrets loading.

- [ ] **Step 3: Implement dynamic secrets-dir selection**

In `backend/src/argus/core/config.py`, add imports and helper:

```python
import os
from pathlib import Path
from typing import Any, Literal
```

Replace the current `model_config` secrets entry with no static `secrets_dir`:

```python
    model_config = SettingsConfigDict(
        env_prefix="ARGUS_",
        env_file=(".env", ".env.local"),
        extra="ignore",
    )
```

Add an `__init__` method inside `Settings`:

```python
    def __init__(self, **values: Any) -> None:
        if "_secrets_dir" not in values:
            values["_secrets_dir"] = _settings_secrets_dir()
        super().__init__(**values)
```

Add helper near the parser helpers:

```python
def _settings_secrets_dir() -> str | None:
    configured = os.getenv("ARGUS_SECRETS_DIR")
    if configured:
        return configured
    default_path = Path("/run/secrets")
    return str(default_path) if default_path.is_dir() else None
```

- [ ] **Step 4: Verify focused tests pass**

Run:

```bash
cd backend
python3 -m uv run pytest -q tests/core/test_config.py::test_default_settings_do_not_warn_when_run_secrets_is_missing tests/core/test_config.py::test_settings_honor_argus_secrets_dir
```

Expected: `2 passed`.

---

### Task 2: Backend Deprecated 422 Status Constants

**Files:**
- Modify: `backend/src/argus/services/camera_sources.py`
- Modify: `backend/src/argus/services/query.py`
- Modify: `backend/src/argus/link/api.py`
- Modify: `backend/tests/core/test_edge_dockerfile.py`

- [ ] **Step 1: Add static regression test**

Add to `backend/tests/core/test_edge_dockerfile.py`:

```python
def test_argus_runtime_does_not_use_deprecated_fastapi_status_aliases() -> None:
    offenders = [
        path.relative_to(BACKEND_ROOT)
        for path in ARGUS_SOURCE_ROOT.rglob("*.py")
        if "HTTP_422_UNPROCESSABLE_ENTITY" in path.read_text(encoding="utf-8")
    ]

    assert offenders == []
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd backend
python3 -m uv run pytest -q tests/core/test_edge_dockerfile.py::test_argus_runtime_does_not_use_deprecated_fastapi_status_aliases
```

Expected before implementation: FAIL listing files that still contain `HTTP_422_UNPROCESSABLE_ENTITY`.

- [ ] **Step 3: Replace deprecated status references**

In each source file that currently imports `status` and uses `status.HTTP_422_UNPROCESSABLE_ENTITY`, add a module-level constant after imports:

```python
HTTP_422_UNPROCESSABLE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)
```

Replace each use:

```python
status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
```

with:

```python
status_code=HTTP_422_UNPROCESSABLE
```

Known initial files:

- `backend/src/argus/services/camera_sources.py`
- `backend/src/argus/services/query.py`
- `backend/src/argus/link/api.py`

- [ ] **Step 4: Verify static test and backend warnings**

Run:

```bash
cd backend
python3 -m uv run pytest -q tests/core/test_edge_dockerfile.py::test_argus_runtime_does_not_use_deprecated_fastapi_status_aliases
python3 -m uv run pytest -q -W error::DeprecationWarning tests/services/test_camera_sources.py tests/services/test_query_service.py tests/link/test_link_service.py
```

Expected: all pass without deprecation warnings.

---

### Task 3: React Router Future-Flag Warnings

**Files:**
- Create: `frontend/src/test/router.tsx`
- Modify all test files with `MemoryRouter` wrappers that do not already pass future flags.

- [ ] **Step 1: Add failing warning reproduction command**

Run:

```bash
tmpfile="$(mktemp)"
corepack pnpm --dir frontend test -- src/pages/FleetOps.test.tsx 2>&1 | tee "$tmpfile"
! rg "React Router Future Flag Warning" "$tmpfile"
```

Expected before implementation: FAIL because `FleetOps.test.tsx` emits React Router future-flag warnings.

- [ ] **Step 2: Create shared router helper**

Create `frontend/src/test/router.tsx`:

```tsx
import type { ComponentProps, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

export const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

type TestMemoryRouterProps = Omit<ComponentProps<typeof MemoryRouter>, "future"> & {
  children?: ReactNode;
};

export function TestMemoryRouter({
  children,
  ...props
}: TestMemoryRouterProps) {
  return (
    <MemoryRouter future={routerFuture} {...props}>
      {children}
    </MemoryRouter>
  );
}
```

- [ ] **Step 3: Replace direct `MemoryRouter` imports in tests**

For each affected test file:

1. Change imports like:

```tsx
import { MemoryRouter } from "react-router-dom";
```

to:

```tsx
import { TestMemoryRouter } from "@/test/router";
```

2. If the file also imports `Route`, `Routes`, or other router exports, keep those:

```tsx
import { Route, Routes } from "react-router-dom";
import { TestMemoryRouter } from "@/test/router";
```

3. Replace JSX wrappers:

```tsx
<MemoryRouter initialEntries={["/live"]}>
  {children}
</MemoryRouter>
```

with:

```tsx
<TestMemoryRouter initialEntries={["/live"]}>
  {children}
</TestMemoryRouter>
```

4. Remove local `routerFuture` constants where the helper replaces them.

- [ ] **Step 4: Verify no router warning remains in focused tests**

Run:

```bash
tmpfile="$(mktemp)"
corepack pnpm --dir frontend test -- src/pages/FleetOps.test.tsx src/pages/FleetOpsEvidence.test.tsx src/pages/FleetOpsOnboarding.test.tsx src/pages/FleetOpsSupport.test.tsx src/components/operations/AttentionStack.test.tsx src/components/operations/SceneIntelligenceMatrix.test.tsx 2>&1 | tee "$tmpfile"
! rg "React Router Future Flag Warning" "$tmpfile"
```

Expected: command exits `0`.

---

### Task 4: React `act(...)` Warnings In `VideoStream.test.tsx`

**Files:**
- Modify: `frontend/src/components/live/VideoStream.test.tsx`

- [ ] **Step 1: Add failing warning reproduction command**

Run:

```bash
tmpfile="$(mktemp)"
corepack pnpm --dir frontend test -- src/components/live/VideoStream.test.tsx 2>&1 | tee "$tmpfile"
! rg "not wrapped in act" "$tmpfile"
```

Expected before implementation: FAIL because `VideoStream.test.tsx` emits React `act(...)` warnings.

- [ ] **Step 2: Add async test helpers near `initialAuthState`**

Add these helpers in `frontend/src/components/live/VideoStream.test.tsx` after `const initialAuthState = useAuthStore.getState();`:

```tsx
async function flushAsyncEffects(cycles = 3) {
  for (let index = 0; index < cycles; index += 1) {
    await Promise.resolve();
  }
}

async function renderVideoStream(ui: React.ReactElement) {
  let result: ReturnType<typeof render> | undefined;
  await act(async () => {
    result = render(ui);
    await flushAsyncEffects();
  });
  if (!result) {
    throw new Error("renderVideoStream failed to render.");
  }
  return result;
}

async function advanceTimersByTime(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
    await flushAsyncEffects();
  });
}

async function emitPeerConnectionState(
  peerConnection: FakeRTCPeerConnection | undefined,
  connectionState: string,
  iceConnectionState = connectionState,
) {
  await act(async () => {
    peerConnection?.emitConnectionState(connectionState, iceConnectionState);
    await flushAsyncEffects();
  });
}

async function emitIntersection(
  element: Element,
  isIntersecting: boolean,
) {
  await act(async () => {
    observedElements.get(element)?.(
      [
        {
          boundingClientRect: element.getBoundingClientRect(),
          intersectionRatio: isIntersecting ? 1 : 0,
          intersectionRect: element.getBoundingClientRect(),
          isIntersecting,
          rootBounds: null,
          target: element,
          time: 0,
        },
      ] as IntersectionObserverEntry[],
      {} as IntersectionObserver,
    );
    await flushAsyncEffects();
  });
}
```

Also add the React type import at the top:

```tsx
import type React from "react";
```

- [ ] **Step 3: Replace bare render calls**

Replace patterns like:

```tsx
act(() => {
  render(
    <VideoStream
      cameraId="11111111-1111-1111-1111-111111111111"
      cameraName="North Gate"
      defaultProfile="720p10"
    />,
  );
});
```

with:

```tsx
await renderVideoStream(
  <VideoStream
    cameraId="11111111-1111-1111-1111-111111111111"
    cameraName="North Gate"
    defaultProfile="720p10"
  />,
);
```

Replace every direct `render(<VideoStream ... />)` in the file with `await renderVideoStream(...)`.

- [ ] **Step 4: Replace timer advances and direct peer/visibility event emissions**

Replace:

```tsx
await act(async () => {
  await vi.advanceTimersByTimeAsync(5_000);
});
```

with:

```tsx
await advanceTimersByTime(5_000);
```

Replace:

```tsx
act(() => {
  peerConnection?.emitConnectionState("disconnected");
});
```

with:

```tsx
await emitPeerConnectionState(peerConnection, "disconnected");
```

Replace direct `observedElements.get(root)?.(...)` callback invocations with:

```tsx
await emitIntersection(root, true);
```

or:

```tsx
await emitIntersection(root, false);
```

- [ ] **Step 5: Verify no `act` warning remains in focused test**

Run:

```bash
tmpfile="$(mktemp)"
corepack pnpm --dir frontend test -- src/components/live/VideoStream.test.tsx 2>&1 | tee "$tmpfile"
! rg "not wrapped in act" "$tmpfile"
```

Expected: command exits `0`.

---

### Task 5: Warning Gates For Full Validation

**Files:**
- Create: `scripts/verify-no-test-warnings.sh`
- Modify: `scripts/run-full-validation.sh`

- [ ] **Step 1: Create warning gate script**

Create `scripts/verify-no-test-warnings.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

backend_log="$(mktemp)"
frontend_log="$(mktemp)"
trap 'rm -f "$backend_log" "$frontend_log"' EXIT

echo "==> backend warning gate"
(
  cd backend
  python3 -m uv run pytest -q \
    -W error::DeprecationWarning \
    -W error::UserWarning
) 2>&1 | tee "$backend_log"

if rg -n 'directory "/run/secrets" does not exist|HTTP_422_UNPROCESSABLE_ENTITY|DeprecationWarning|UserWarning' "$backend_log"; then
  echo "backend warning gate failed" >&2
  exit 1
fi

echo "==> frontend warning gate"
corepack pnpm --dir frontend test 2>&1 | tee "$frontend_log"

if rg -n 'not wrapped in act|React Router Future Flag Warning' "$frontend_log"; then
  echo "frontend warning gate failed" >&2
  exit 1
fi

echo "test warning gates passed"
```

- [ ] **Step 2: Make the script executable**

Run:

```bash
chmod +x scripts/verify-no-test-warnings.sh
```

- [ ] **Step 3: Wire into full validation**

In `scripts/run-full-validation.sh`, after the existing backend/frontend test sections, add:

```bash
log_step "Running test warning gates"
./scripts/verify-no-test-warnings.sh
```

- [ ] **Step 4: Verify warning gate**

Run:

```bash
./scripts/verify-no-test-warnings.sh
```

Expected: `test warning gates passed`.

- [ ] **Step 5: Verify normal suites still pass**

Run:

```bash
cd backend
python3 -m uv run ruff check .
python3 -m uv run mypy --strict src
python3 -m uv run pytest -q
cd ../frontend
corepack pnpm lint
corepack pnpm build
corepack pnpm test
cd ..
./scripts/verify-no-test-warnings.sh
git diff --check
```

Expected:

- Ruff passes.
- Mypy passes.
- Backend pytest passes.
- Frontend lint/build/test pass.
- Warning gate passes with no matched warning lines.
- `git diff --check` exits `0`.

---

## Execution Notes

- Run `rg -n "HTTP_422_UNPROCESSABLE_ENTITY" backend/src` after Task 2; it must return no source matches.
- Run `rg -n "React Router Future Flag Warning|not wrapped in act" frontend/test-results frontend/src` only as a sanity check; the authoritative check is the captured test output in Task 5.
- If `-W error::UserWarning` exposes legitimate non-Pydantic warnings after Task 1, do not blanket-ignore them. Either fix the source warning or narrow the warning gate to the exact Pydantic secrets warning after documenting why.
- Keep Core Link domain-neutral; this plan must not introduce FleetOps nouns into `backend/src/argus/link/*`.

## Self-Review

- Spec coverage: Task 1 covers `/run/secrets`; Task 2 covers deprecated 422 aliases; Task 3 covers React Router warnings; Task 4 covers React `act` warnings; Task 5 covers regression gates.
- Placeholder scan: no `TBD`, `TODO`, or “add appropriate” placeholders remain.
- Type consistency: frontend helper exports `routerFuture` and `TestMemoryRouter`; backend helper is `_settings_secrets_dir`; status constant name is `HTTP_422_UNPROCESSABLE`.
