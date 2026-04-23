# Vezor Brand Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the user-facing product brand from `Argus` to `Vezor` while keeping the existing symbol, visual design, and internal technical namespace stable in the first pass.

**Architecture:** Treat this as a brand-surface rename, not a package-namespace rewrite. Introduce a single frontend brand module and neutral runtime asset filenames, update all visible product copy and documentation to `Vezor`, and explicitly defer `backend/src/argus`, `ARGUS_` env vars, and `--argus-*` CSS tokens unless the optional operational-identifier track is approved.

**Tech Stack:** React, Vite, TypeScript, FastAPI, Python, SVG assets, Keycloak OIDC, Docker Compose, Helm, GitHub Actions.

---

## Scope Decisions

### In Scope For The Recommended Rename

- visible product name in UI copy, page titles, README, and docs
- product lockup and symbol asset filenames used by the frontend runtime
- backend display name strings that are visible to operators or developers
- repo structure cleanup for brand assets and docs so future renames are cheaper

### Explicitly Out Of Scope In Phase 1

- `backend/src/argus/**`
- `ARGUS_` environment variable prefix
- CSS custom property names like `--argus-canvas`
- database names, usernames, and local dev credentials
- Docker service names and Helm chart folder names

### Optional Track (Separate Approval)

Only do this if you want the technical surface to say `Vezor` too:

- Keycloak realm `argus-dev` -> `vezor-dev`
- OIDC client `argus-frontend` -> `vezor-frontend`
- GHCR image names `argus-backend` / `argus-frontend` / `argus-edge`
- Helm chart folder/name `infra/helm/argus`

## File Structure Map

### New Or Reorganized Files

- Create: `frontend/src/brand/product.ts`
  - Single source of truth for product name, descriptor, and runtime brand asset paths.
- Create: `frontend/src/components/layout/ProductLockup.test.tsx`
  - Verifies the shared product lockup uses `Vezor` alt text and the neutral asset paths.
- Create: `frontend/public/brand/product-lockup-ui.svg`
  - Neutral runtime wordmark file used by the app.
- Create: `frontend/public/brand/product-symbol-ui.svg`
  - Neutral runtime symbol file used by the app.
- Create: `docs/brand/assets/source/`
  - Holds source SVGs and future brand-authoring assets outside the repo root.

### Existing Files To Modify In The Recommended Pass

- Modify: `frontend/src/components/layout/ProductLockup.tsx`
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/SignIn.test.tsx`
- Modify: `frontend/src/components/live/AgentInput.tsx`
- Modify: `frontend/e2e/prompt8-live-dashboard.spec.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/components/sites/SiteDialog.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
- Modify: `frontend/src/lib/auth.ts`
- Modify: `frontend/index.html`
- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/src/argus/__init__.py`
- Modify: `backend/src/argus/api/v1/streams.py`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `docs/brand/argus-logo-brand-spec.md`
- Modify: `docs/brand/usage-guide.md`
- Modify: `docs/brand/logo-generation-prompts.md`

### Files To Leave Alone In The Recommended Pass

- Leave: `backend/src/argus/**` module path
- Leave: `backend/pyproject.toml` package name `argus-backend`
- Leave: `frontend/package.json` package name `argus-frontend`
- Leave: `frontend/src/index.css` custom property names `--argus-*`
- Leave: `ARGUS_*` env vars in backend and worker config
- Leave: `infra/helm/argus/**`
- Leave: `Makefile` image tags and `.github/workflows/**` image names

## Rename Rules

- Product display name: `Argus` -> `Vezor`
- Descriptor: keep `The OmniSight Platform`
- Prefer neutral filenames for runtime brand assets:
  - `product-lockup-ui.svg`
  - `product-symbol-ui.svg`
- Prefer generic wording where brand repetition adds no value:
  - `Failed to resolve the query.` instead of `Failed to resolve the Vezor query.`
  - `recognized platform role` instead of `recognized Vezor role`

### Task 1: Introduce A Frontend Brand Source Of Truth

**Files:**
- Create: `frontend/src/brand/product.ts`
- Create: `frontend/src/components/layout/ProductLockup.test.tsx`
- Create: `frontend/public/brand/product-lockup-ui.svg`
- Create: `frontend/public/brand/product-symbol-ui.svg`
- Modify: `frontend/src/components/layout/ProductLockup.tsx`
- Test: `frontend/src/components/layout/ProductLockup.test.tsx`

- [ ] **Step 1: Write the failing lockup test**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { ProductLockup } from "@/components/layout/ProductLockup";

describe("ProductLockup", () => {
  test("uses the shared Vezor brand metadata", () => {
    render(<ProductLockup />);

    expect(
      screen.getByRole("img", { name: /vezor product lockup/i }),
    ).toHaveAttribute("src", "/brand/product-lockup-ui.svg");
  });

  test("uses the neutral symbol asset for symbol-only mode", () => {
    render(<ProductLockup symbolOnly />);

    expect(screen.getByRole("img", { name: /vezor symbol/i })).toHaveAttribute(
      "src",
      "/brand/product-symbol-ui.svg",
    );
  });
});
```

- [ ] **Step 2: Run the lockup test and verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/ProductLockup.test.tsx
```

Expected:

- FAIL because `ProductLockup.tsx` still hardcodes `Argus` alt text and `argus-*.svg` asset paths.

- [ ] **Step 3: Create the shared brand module**

Create `frontend/src/brand/product.ts`:

```ts
export const productBrand = {
  name: "Vezor",
  descriptor: "The OmniSight Platform",
  runtimeAssets: {
    lockup: "/brand/product-lockup-ui.svg",
    symbol: "/brand/product-symbol-ui.svg",
  },
} as const;

export function getProductLockupAlt(symbolOnly: boolean): string {
  return symbolOnly
    ? `${productBrand.name} symbol`
    : `${productBrand.name} product lockup`;
}

export function getProductTitle(): string {
  return `${productBrand.name} | ${productBrand.descriptor}`;
}
```

- [ ] **Step 4: Update the shared lockup component to read from the brand module**

Modify `frontend/src/components/layout/ProductLockup.tsx`:

```tsx
import type { ImgHTMLAttributes } from "react";

import { getProductLockupAlt, productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

interface ProductLockupProps
  extends Omit<ImgHTMLAttributes<HTMLImageElement>, "alt" | "src"> {
  compact?: boolean;
  symbolOnly?: boolean;
}

export function ProductLockup({
  className,
  compact = false,
  symbolOnly = false,
  ...props
}: ProductLockupProps) {
  const src = symbolOnly
    ? productBrand.runtimeAssets.symbol
    : productBrand.runtimeAssets.lockup;
  const alt = getProductLockupAlt(symbolOnly);
  const baseClasses = symbolOnly
    ? "h-11 w-11 rounded-[1rem]"
    : compact
      ? "h-10 w-auto"
      : "h-12 w-auto";

  return (
    <img
      alt={alt}
      className={cn("block select-none", baseClasses, className)}
      decoding="async"
      draggable={false}
      src={src}
      {...props}
    />
  );
}
```

- [ ] **Step 5: Add neutral runtime asset filenames**

Run:

```bash
cp frontend/public/brand/argus-lockup-ui.svg frontend/public/brand/product-lockup-ui.svg
cp frontend/public/brand/argus-symbol-ui.svg frontend/public/brand/product-symbol-ui.svg
```

Then edit the copied SVG metadata so it says `Vezor` in the `<title>`, `aria-label`, and `<desc>`.

- [ ] **Step 6: Run the lockup test and verify it passes**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/components/layout/ProductLockup.test.tsx
```

Expected:

- PASS

- [ ] **Step 7: Commit the brand source-of-truth change**

```bash
git add frontend/src/brand/product.ts frontend/src/components/layout/ProductLockup.tsx frontend/src/components/layout/ProductLockup.test.tsx frontend/public/brand/product-lockup-ui.svg frontend/public/brand/product-symbol-ui.svg
git commit -m "feat: centralize Vezor brand metadata"
```

### Task 2: Rename User-Facing Frontend Copy To Vezor

**Files:**
- Modify: `frontend/src/pages/SignIn.tsx`
- Modify: `frontend/src/pages/SignIn.test.tsx`
- Modify: `frontend/src/components/live/AgentInput.tsx`
- Modify: `frontend/e2e/prompt8-live-dashboard.spec.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/pages/Cameras.tsx`
- Modify: `frontend/src/pages/Sites.tsx`
- Modify: `frontend/src/components/sites/SiteDialog.tsx`
- Modify: `frontend/src/components/cameras/CameraWizard.tsx`
- Modify: `frontend/src/components/cameras/HomographyEditor.tsx`
- Modify: `frontend/src/lib/auth.ts`
- Test: `frontend/src/pages/SignIn.test.tsx`
- Test: `frontend/e2e/prompt8-live-dashboard.spec.ts`

- [ ] **Step 1: Update the sign-in test first**

Modify `frontend/src/pages/SignIn.test.tsx`:

```tsx
test("renders the shared product lockup and a single primary sign-in action", () => {
  render(<SignInPage />);

  expect(
    screen.getByRole("img", { name: /vezor product lockup/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^sign in$/i })).toBeInTheDocument();
  expect(screen.getByText(/vigilant intelligence/i)).toBeInTheDocument();
  expect(screen.getByText(/operate Vezor from a premium command center/i)).toBeInTheDocument();
  expect(
    screen.getByText(/Use your Vezor identity provider account to continue/i),
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the sign-in test and verify it fails**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
```

Expected:

- FAIL because `SignIn.tsx` still says `Argus`.

- [ ] **Step 3: Replace visible `Argus` strings in the frontend**

Apply these exact replacements:

```tsx
// frontend/src/pages/SignIn.tsx
<p className="max-w-xl text-lg text-[var(--argus-text-muted)]">
  Monitor cameras, manage configuration, and operate Vezor from a premium
  command center built for continuous observation.
</p>

<p className="mt-2 text-sm text-[var(--argus-text-muted)]">
  Use your Vezor identity provider account to continue.
</p>
```

```tsx
// frontend/src/components/live/AgentInput.tsx
throw toApiError(error, "Failed to resolve the query.");
setErrorMessage(toApiError(error, "Failed to resolve the query.").message);

// Visible copy
Resolve classes once, then let Vezor trim the operator view while the backend
...
Query Vezor
aria-label="Query Vezor"
```

```tsx
// frontend/src/lib/auth.ts
throw new Error("OIDC user is missing a recognized platform role.");
```

```tsx
// frontend/src/pages/History.tsx
Vezor delivers chart-ready time buckets directly from the backend so long
```

```tsx
// frontend/src/pages/Cameras.tsx
rendition for operators, and the calibration Vezor uses to understand
```

```tsx
// frontend/src/pages/Sites.tsx
throughout Vezor operations.
```

```tsx
// frontend/src/components/sites/SiteDialog.tsx
description="Add a deployment location to the Vezor fleet and attach its operating time zone."
```

```tsx
// frontend/src/components/cameras/CameraWizard.tsx
return "Choose the fleet location, processing posture, and ingest stream Vezor should bind to this camera.";
return "Calibrate four source points, four destination points, and a real-world distance so Vezor can map image motion into the physical scene.";
return "Confirm the camera configuration before Vezor saves it. RTSP stays masked unless you explicitly replace it.";
...
Vezor keeps the stored RTSP address masked. Leave this field empty to
```

```tsx
// frontend/src/components/cameras/HomographyEditor.tsx
Source points: {src.length} / 4. Destination points: {dst.length} / 4. Vezor
```

```ts
// frontend/e2e/prompt8-live-dashboard.spec.ts
await page.getByLabel("Query Vezor").fill("only show cars");
```

- [ ] **Step 4: Run the targeted frontend verification**

Run:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/SignIn.test.tsx
corepack pnpm --dir frontend exec playwright test e2e/prompt8-live-dashboard.spec.ts
```

Expected:

- Both commands PASS.

- [ ] **Step 5: Commit the user-facing rename sweep**

```bash
git add frontend/src/pages/SignIn.tsx frontend/src/pages/SignIn.test.tsx frontend/src/components/live/AgentInput.tsx frontend/e2e/prompt8-live-dashboard.spec.ts frontend/src/pages/History.tsx frontend/src/pages/Cameras.tsx frontend/src/pages/Sites.tsx frontend/src/components/sites/SiteDialog.tsx frontend/src/components/cameras/CameraWizard.tsx frontend/src/components/cameras/HomographyEditor.tsx frontend/src/lib/auth.ts
git commit -m "feat: rename frontend product copy to Vezor"
```

### Task 3: Update Titles And Backend Display Strings

**Files:**
- Modify: `frontend/index.html`
- Modify: `backend/src/argus/core/config.py`
- Modify: `backend/src/argus/__init__.py`
- Modify: `backend/src/argus/api/v1/streams.py`
- Test: `frontend/index.html`
- Test: `backend/tests/core/test_config.py`

- [ ] **Step 1: Update the HTML title and backend app name**

Apply these edits:

```html
<!-- frontend/index.html -->
<title>Vezor | The OmniSight Platform</title>
```

```py
# backend/src/argus/core/config.py
app_name: str = "Vezor | The OmniSight Platform"
```

```py
# backend/src/argus/__init__.py
"""Vezor | The OmniSight Platform backend package."""
```

```py
# backend/src/argus/api/v1/streams.py
<title>Vezor WebRTC Test</title>
<h1>Vezor WebRTC Offer Test</h1>
```

- [ ] **Step 2: Add or update a backend config assertion**

Extend `backend/tests/core/test_config.py` with:

```py
def test_default_app_name_uses_vezor_branding() -> None:
    settings = Settings(_env_file=None, rtsp_encryption_key="argus-secret-key")
    assert settings.app_name == "Vezor | The OmniSight Platform"
```

- [ ] **Step 3: Run the targeted verification**

Run:

```bash
python3 -m uv run pytest backend/tests/core/test_config.py -q
corepack pnpm --dir frontend build
```

Expected:

- pytest PASS
- frontend build PASS

- [ ] **Step 4: Commit the backend/title rename**

```bash
git add frontend/index.html backend/src/argus/core/config.py backend/src/argus/__init__.py backend/src/argus/api/v1/streams.py backend/tests/core/test_config.py
git commit -m "feat: rename visible backend titles to Vezor"
```

### Task 4: Restructure Brand Assets And Rename Product Docs

**Files:**
- Create: `docs/brand/assets/source/`
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `docs/brand/argus-logo-brand-spec.md`
- Modify: `docs/brand/usage-guide.md`
- Modify: `docs/brand/logo-generation-prompts.md`
- Modify: `frontend/public/brand/argus-lockup-ui.svg`
- Modify: `frontend/public/brand/argus-symbol-ui.svg`

- [ ] **Step 1: Move source SVGs out of the repo root**

Run:

```bash
mkdir -p docs/brand/assets/source
git mv argus-icon.svg docs/brand/assets/source/vezor-icon.svg
git mv argus-icon-v2.svg docs/brand/assets/source/vezor-icon-v2.svg
git mv argus-omnisight-logo.svg docs/brand/assets/source/vezor-omnisight-logo.svg
git mv argus-omnisight-logo-v2.svg docs/brand/assets/source/vezor-omnisight-logo-v2.svg
```

Then edit the moved SVG metadata so titles and aria labels say `Vezor`.

- [ ] **Step 2: Rename the README and docs copy**

Apply these exact structural changes:

```md
<!-- README.md -->
# Vezor | The OmniSight Platform

Vezor is a hybrid video analytics platform for multi-camera operations.
```

```md
<!-- backend/README.md -->
# Vezor | The OmniSight Platform Backend

FastAPI backend scaffold for Vezor | The OmniSight Platform.
```

For docs, run a controlled sweep:

```bash
rg -n '\bArgus\b' README.md backend/README.md docs/brand docs/imac-master-orin-lab-test-guide.md docs/deployment-modes-and-matrix.md docs/operator-deployment-playbook.md docs/runbook.md
```

Replace visible product-name usages with `Vezor`, but do **not** rename historical ADR content that discusses original project context unless it is operator-facing.

- [ ] **Step 3: Update brand-doc references so they stop hardcoding Argus filenames**

Prefer neutral references in docs:

```md
- [docs/brand/logo-brand-spec.md](/Users/yann.moren/vision/docs/brand/logo-brand-spec.md)
- [docs/brand/logo-usage-guide.md](/Users/yann.moren/vision/docs/brand/logo-usage-guide.md)
- [docs/brand/logo-generation-prompts.md](/Users/yann.moren/vision/docs/brand/logo-generation-prompts.md)
```

Run:

```bash
git mv docs/brand/argus-logo-brand-spec.md docs/brand/logo-brand-spec.md
git mv docs/brand/usage-guide.md docs/brand/logo-usage-guide.md
```

Keep `docs/brand/logo-generation-prompts.md` in place, but rewrite its content for `Vezor`.

- [ ] **Step 4: Verify the docs and branding sweep**

Run:

```bash
rg -n '\bArgus\b' README.md backend/README.md frontend/index.html frontend/src docs/brand
```

Expected:

- Only intentional historical references remain.

- [ ] **Step 5: Commit the docs and repo-structure cleanup**

```bash
git add README.md backend/README.md docs/brand docs/brand/assets/source
git commit -m "docs: rename product documentation to Vezor"
```

### Task 5: Optional Operational Identifier Rename

**Only execute this task if you want the technical surface to say `Vezor` too.**

**Files:**
- Modify: `frontend/.env.example`
- Modify: `frontend/playwright.config.ts`
- Modify: `frontend/src/lib/config.ts`
- Modify: `frontend/src/lib/config.test.ts`
- Modify: `infra/keycloak/realm-export.json`
- Modify: `infra/docker-compose.dev.yml`
- Modify: `backend/src/argus/core/config.py`
- Modify: `scripts/run-full-validation.sh`
- Modify: `frontend/e2e/prompt7-auth-and-camera.spec.ts`
- Modify: `frontend/e2e/prompt8-live-dashboard.spec.ts`
- Modify: `frontend/e2e/prompt9-history-and-incidents.spec.ts`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/release.yml`
- Modify: `Makefile`
- Modify: `infra/helm/argus/values.yaml`

- [ ] **Step 1: Parameterize the realm and client defaults**

Apply these replacements:

```env
# frontend/.env.example
VITE_OIDC_AUTHORITY=http://localhost:8080/realms/vezor-dev
VITE_OIDC_CLIENT_ID=vezor-frontend
```

```ts
// frontend/playwright.config.ts
VITE_OIDC_AUTHORITY: "http://127.0.0.1:8080/realms/vezor-dev",
VITE_OIDC_CLIENT_ID: "vezor-frontend",
```

```ts
// frontend/src/lib/config.ts dev defaults
return `${location.protocol}//${location.hostname}:8080/realms/vezor-dev`;
return "vezor-frontend";
```

```py
# backend/src/argus/core/config.py
keycloak_issuer: str = "http://localhost:8080/realms/vezor-dev"
```

- [ ] **Step 2: Update the seeded Keycloak realm export**

Edit `infra/keycloak/realm-export.json`:

```json
{
  "realm": "vezor-dev",
  "clients": [
    {
      "clientId": "vezor-frontend"
    }
  ]
}
```

- [ ] **Step 3: Update Docker, scripts, and test fixtures**

Apply these replacements:

```yaml
# infra/docker-compose.dev.yml
ARGUS_KEYCLOAK_ISSUER: http://keycloak:8080/realms/vezor-dev
VITE_OIDC_AUTHORITY: http://localhost:8080/realms/vezor-dev
VITE_OIDC_CLIENT_ID: vezor-frontend
```

```bash
# scripts/run-full-validation.sh
"http://127.0.0.1:8080/realms/vezor-dev/.well-known/openid-configuration"
```

Then run a controlled fixture sweep:

```bash
rg -n 'argus-dev|argus-frontend' backend/tests frontend/src frontend/e2e
```

Replace only test fixtures and expected values that truly represent the active realm/client.

- [ ] **Step 4: Rename image tags and Helm identifiers only after auth is green**

Apply these replacements:

```make
# Makefile
-t $(REGISTRY)/vezor-backend:$(TAG)
-t $(REGISTRY)/vezor-edge:$(TAG)
-t $(REGISTRY)/vezor-frontend:$(TAG)
```

```yaml
# .github/workflows/ci.yml and .github/workflows/release.yml
ghcr.io/${{ github.repository }}/vezor-backend:...
ghcr.io/${{ github.repository }}/vezor-edge:...
ghcr.io/${{ github.repository }}/vezor-frontend:...
```

```yaml
# infra/helm/argus/values.yaml
repository: vezor-backend
repository: vezor-frontend
repository: vezor-edge
```

Keep the chart folder name `infra/helm/argus` until a separate chart-migration change unless you are prepared to update every chart reference in the same PR.

- [ ] **Step 5: Run the full operational verification**

Run:

```bash
corepack pnpm --dir frontend exec playwright test e2e/prompt7-auth-and-camera.spec.ts e2e/prompt8-live-dashboard.spec.ts e2e/prompt9-history-and-incidents.spec.ts
python3 -m uv run pytest backend/tests/core/test_config.py backend/tests/api/test_app.py -q
corepack pnpm --dir frontend build
```

Expected:

- all Playwright tests PASS
- backend pytest PASS
- frontend build PASS

- [ ] **Step 6: Commit the optional operational rename**

```bash
git add frontend/.env.example frontend/playwright.config.ts frontend/src/lib/config.ts frontend/src/lib/config.test.ts infra/keycloak/realm-export.json infra/docker-compose.dev.yml scripts/run-full-validation.sh .github/workflows/ci.yml .github/workflows/release.yml Makefile infra/helm/argus/values.yaml backend/src/argus/core/config.py backend/tests frontend/src frontend/e2e
git commit -m "feat: rename operational identifiers to Vezor"
```

## Final Verification Checklist

- [ ] `rg -n '\bArgus\b' frontend/src frontend/public frontend/index.html README.md backend/README.md docs/brand`
- [ ] `corepack pnpm --dir frontend exec vitest run src/components/layout/ProductLockup.test.tsx src/pages/SignIn.test.tsx`
- [ ] `corepack pnpm --dir frontend exec playwright test e2e/prompt8-live-dashboard.spec.ts`
- [ ] `corepack pnpm --dir frontend build`
- [ ] `git diff --check`

## Handoff Notes

- Recommended stopping point: complete Tasks 1 through 4 and ship `Vezor` as the visible brand while keeping `argus` internal namespaces stable.
- Optional Task 5 is intentionally separate because it expands the blast radius into auth, CI, release, and image distribution.
- If later you decide to do a full internal namespace migration, create a separate plan for:
  - `backend/src/argus` -> `backend/src/vezor`
  - `ARGUS_` -> `VEZOR_`
  - `--argus-*` -> `--vezor-*`
  - Helm chart folder rename
