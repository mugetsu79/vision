# Prompt 7 Design: Frontend Foundation

- Date: 2026-04-18
- Scope: Prompt 7 only
- Status: Approved design, ready for implementation planning after user review

## Goal

Build the first real Argus frontend foundation around four outcomes:

1. Real OIDC PKCE authentication against local Keycloak with no mock-auth bypass.
2. A typed frontend data layer generated from the backend OpenAPI schema.
3. A production-shaped app shell that matches the chosen "Hybrid Command Center" direction and the Argus visual identity.
4. Working `Sites` and `Cameras` management pages, including a guided stepped camera setup flow with homography editing and browser delivery-profile configuration.

This prompt establishes the product frame for later prompts. It should make Prompt 8's live dashboard, Prompt 9's history pages, and future admin flows feel like natural extensions of the same app rather than disconnected screens.

## User-Approved Design Decisions

The design is based on these confirmed decisions:

- Unauthenticated users land on a branded Argus sign-in screen with a `Sign in` button.
- Authentication is real Keycloak end-to-end in local development.
- The frontend shell follows direction `C`: "Hybrid Command Center".
- Camera setup uses the heavier `C` editing pattern rather than a basic modal or drawer.
- Camera create/edit is a stepped setup flow inside that split surface, not a single long form.

## Argus Visual System

Prompt 7 must establish the product's dark-first visual language, not just its route structure.

The UI should feel aligned with the approved Argus identity:

- deep obsidian and charcoal surfaces, not white-first SaaS scaffolding
- restrained cerulean-to-violet illumination used as a purposeful accent, not decorative noise
- luminous off-white typography for primary product copy
- geometric, modern, premium-feeling sans-serif typography
- subtle depth, matte-screen surfaces, and soft glow rather than flat blocks
- a vigilant, technical, premium B2B tone across sign-in, shell, tables, dialogs, and the camera wizard

This is not a logo-only requirement. The sign-in page, shell chrome, action surfaces, tables, and setup flows must all feel like they belong to the same Argus product family.

## Delivery Rendition Constraint

Prompt 7 does not need to build live playback yet, but the camera workflow should already reflect the streaming model we intend to ship.

The frontend should represent these truths clearly:

- analytics ingest may remain native even when operator viewing is bandwidth-optimized
- browser delivery can default to a lower-bitrate rendition such as `1080p15`, `720p10`, or `540p5`
- `native` remains available where policy and infrastructure allow it
- choosing a non-native browser delivery profile may activate an optional preview/transcode path, especially on Jetson deployments where bandwidth reduction is desired
- privacy-required cameras can only expose privacy-safe renditions

## Non-Goals

Prompt 7 does not include:

- live video playback or telemetry overlays
- LL-HLS / WebRTC player UI
- NL query UX
- history charts or incident visualizations
- a mock-auth or dev-bypass mode
- a generic form engine for future prompts

## Frontend Architecture

The frontend should move from a single scaffold screen to a routed application with clear app, auth, data, and page boundaries.

### Route structure

The route map should be:

- `/signin` - branded Argus entry page for anonymous users
- `/auth/callback` - OIDC PKCE callback handler
- `/` - authenticated app shell
- `/dashboard`
- `/live`
- `/history`
- `/incidents`
- `/sites`
- `/cameras`
- `/settings`

The root shell should be guarded by `RequireAuth`. Anonymous users should be redirected to `/signin`, not directly to Keycloak.

### App shell

The shell should reflect the approved "Hybrid Command Center" direction:

- top navigation for `Dashboard`, `Live`, `History`, `Incidents`, and `Settings`
- a right-side identity cluster with tenant context, user menu, and logout
- a main content region that supports both operational views and admin tables
- a secondary contextual area or panel language that can support summaries, actions, and setup guidance
- dark-first control-room styling that still works for CRUD-heavy management views

`Sites` and `Cameras` should not be added to the primary top nav, because Prompt 7 already fixes that surface. They should remain direct routes (`/sites`, `/cameras`) but be reached through admin-oriented secondary navigation inside the authenticated shell, with `Settings` as the main management entry point for human navigation.

This shell should feel operational and productized at the same time. It should avoid both extremes:

- too infrastructure-heavy, which would make CRUD pages feel like raw admin consoles
- too generic-SaaS, which would weaken Argus's monitoring identity

## Authentication Design

Authentication uses real `oidc-client-ts` PKCE against Keycloak.

### Auth flow

1. Anonymous user opens the app.
2. The app routes them to `/signin`.
3. Clicking `Sign in` starts the Keycloak PKCE redirect.
4. Keycloak returns to `/auth/callback`.
5. The callback route completes sign-in, restores session state, and routes into the authenticated shell.
6. The app restores the session on refresh if valid tokens are still present.
7. Logout clears local session state and redirects through the IdP logout path.

### Auth state ownership

Zustand owns session and identity state only:

- current OIDC user
- auth status (`anonymous`, `loading`, `authenticated`)
- sign-in action
- callback completion action
- sign-out action
- derived role and tenant-context helpers

The auth store must not become a general data cache. Server data belongs to TanStack Query.

### Role handling

Frontend route and UI gating should follow backend RBAC:

- `viewer` - read-only route access where allowed
- `operator` - command-capable areas later
- `admin` - Prompt 7 CRUD capability
- `superadmin` - sees tenant switcher only when authenticated from the `platform-admin` realm
- missing or unrecognized role claims must fail closed rather than silently downgrading to `viewer`

`RequireRole` should gate admin-only screens or actions without coupling that logic to page internals.

## API Client and Data Fetching

Prompt 7 should establish the long-term frontend data shape without overbuilding it.

### OpenAPI-driven client

The frontend should generate API types from the backend OpenAPI schema using:

- `openapi-typescript`
- `openapi-fetch`

The generated layer should remain thin. It exists to provide type-safe contracts and reduce handwritten request drift, not to create a large custom SDK.

### Query layer

TanStack Query should own server-state fetching and mutation behavior:

- `useSites`
- `useCreateSite`
- `useUpdateSite`
- `useDeleteSite`
- `useCameras`
- `useCreateCamera`
- `useUpdateCamera`
- `useDeleteCamera`
- `useModels`

The API client should inject bearer auth centrally so page code does not hand-roll authorization headers.

### State split

The frontend state model is:

- Zustand for auth/session state
- TanStack Query for backend data
- component-local state for active form step, dialog state, and transient UI

This keeps data ownership simple and predictable before Prompt 8 adds richer live interaction.

## Page and Workflow Design

### Sign-in page

`/signin` should be branded and minimal:

- Argus product identity
- short description of the platform
- one clear `Sign in` action
- lightweight status messaging for callback/login errors
- the same obsidian, luminous, premium visual language as the authenticated shell

It should feel intentional, not like a placeholder or debug screen.

### Sites page

`Sites` is the lighter CRUD surface:

- table view as the primary artifact
- create and edit actions
- fast scanning and management orientation
- contextual shell styling consistent with the command-center direction

Its create/edit experience should use the same visual language as Cameras, but with much lighter content.

### Cameras page

`Cameras` is the heaviest management workflow in Prompt 7.

The page should include:

- a table of existing cameras
- create/edit entry points
- row actions for edit and delete
- a larger split configuration surface for the selected camera workflow

## Camera Setup Flow

Camera create/edit should be implemented as a stepped flow inside a split dialog/workspace.

### Step layout

Left side:

- current form step
- actions for next/back/save
- validation messages tied to the active step

Right side:

- contextual guidance or live summary for most steps
- homography editor surface during calibration

### Steps

1. **Identity**
   - `name`
   - `site`
   - `processing mode`
   - masked `RTSP URL`

2. **Models & Tracking**
   - primary model
   - secondary model
   - tracker type

3. **Privacy, Processing & Delivery**
   - blur toggles
   - method and strength
   - frame skip
   - fps cap
   - browser delivery profile (`native`, `1080p15`, `720p10`, `540p5`)
   - clear explanation that non-native browser delivery may use an optional preview/transcode path while analytics ingest remains native
   - policy-forced fields shown clearly and locked where required

4. **Calibration**
   - `HomographyEditor`
   - 4 source points
   - 4 destination points
   - reference distance

5. **Review**
   - summarized configuration
   - final confirmation before submit

### Edit behavior

For existing cameras:

- RTSP stays masked by default
- the stored stream URL should not be revealed in plain text
- operators may explicitly replace the RTSP URL when needed

This preserves the prompt requirement for masked RTSP handling while keeping edits practical.

## Delivery Profile UX

Prompt 7 should make the bandwidth-control model understandable before Prompt 8 adds playback.

The camera workflow should therefore:

- expose a default browser delivery profile at create/edit time
- explain the difference between native ingest and operator delivery in plain product language
- avoid framing bandwidth optimization as a degradation of analytics quality
- preserve room for future per-view overrides without requiring a redesign of the camera form

## Homography Editor Design

The homography editor only needs to reach Prompt 7 readiness, not full future sophistication.

It should support:

- displaying a frame snapshot area
- collecting 4 source points
- collecting 4 destination points
- entering reference distance
- showing current point counts and validation state

It should be structured so Prompt 8 or later can improve fidelity without replacing the whole page contract.

## Component Boundaries

The implementation should keep clear boundaries between route composition and reusable UI pieces.

Suggested structure:

- `src/app/` or equivalent for providers and router bootstrap
- `src/lib/` for generated client, auth setup, and utilities
- `src/stores/` for auth/session state
- `src/components/` for shell, guards, tables, stepper, editor, and shared widgets
- `src/pages/` for route-level composition
- `src/hooks/` or feature-local hooks for query orchestration

Key reusable pieces expected from Prompt 7:

- `RequireAuth`
- `RequireRole`
- app shell and nav components
- user menu
- tenant switcher
- stepped dialog/workflow scaffold
- `HomographyEditor`

## Error Handling

Prompt 7 should explicitly handle the following failure cases:

- sign-in initiation failure
- callback/token processing failure
- expired or missing session on app boot
- tokens with missing or unrecognized Argus roles
- unauthorized role access to CRUD routes or actions
- API request failures for sites, cameras, and models
- validation errors during camera setup

The goal is calm and clear recovery, not silent failure or raw exception output.

## Verification Strategy

Prompt 7 should be verified at three levels.

### 1. Frontend unit/component coverage

Cover:

- auth guard behavior
- sign-in page action behavior
- shell rendering for authenticated users
- role-gated surfaces
- stepped camera form progression

### 2. Typed data flow verification

Cover:

- generated API client integration
- TanStack Query hooks for sites, cameras, and models
- authenticated request behavior using bearer injection

### 3. Playwright end-to-end

Playwright should validate the real local path:

1. open app
2. click `Sign in`
3. complete real Keycloak login using seeded local user
4. create a site
5. create a camera through the stepped split workflow
6. complete homography inputs
7. save
8. verify the camera appears in the Cameras table

This E2E flow must use real auth. No mock session injection should be introduced for Prompt 7 verification.

## Risks and Mitigations

### Risk: Auth complexity slows frontend delivery

Mitigation:

- use real auth once, early
- keep auth state thin
- centralize token handling in the auth layer

### Risk: Camera setup becomes too heavy for Prompt 7

Mitigation:

- use a stepped flow
- defer advanced calibration polish
- keep the homography editor functional rather than overdesigned

### Risk: Visual design collapses into generic SaaS patterns

Mitigation:

- treat the Argus visual system as a prompt requirement, not optional polish
- establish dark-first tokens and shell styling before page-level CRUD work
- keep glow accents restrained so the interface still feels precise and trustworthy

### Risk: Over-abstraction before later prompts prove reuse

Mitigation:

- only extract components that clearly support Prompt 7's real needs
- avoid building a generic admin framework

## Final Recommendation

Implement Prompt 7 as a focused vertical foundation:

- real Keycloak PKCE auth
- branded sign-in route
- strong dark-first Argus visual system
- OpenAPI-generated typed client
- TanStack Query data layer
- Zustand auth/session store
- hybrid command-center shell
- Sites CRUD
- Cameras CRUD with a stepped split configuration flow and delivery-profile controls
- real Playwright login and creation flow

This is the smallest design that still gives Argus a credible product foundation and avoids rework in Prompts 8 and 9.
