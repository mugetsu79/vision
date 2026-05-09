## Phase 5A - Operational Readiness UI

- Added a frontend-only operational readiness model that derives fleet health, deployment posture, privacy posture, scene readiness, delivery, telemetry, and evidence attention from existing APIs.
- Added a Dashboard deployment posture strip for sites, scenes, central/edge/hybrid split, privacy-configured scenes, evidence awaiting review, and fleet health.
- Added a Dashboard attention stack for pending evidence, missing workers, stale nodes, and unavailable direct streams.
- Added an Operations scene intelligence matrix, Live scene status strip, and Scenes inventory readiness cue.
- Added Live signal stabilization with class-colored overlays, calmer scene state labels, and a Telemetry Terrain surface for scene activity.
- Kept WebGL off and left runtime metrics such as `capture_wait_*` for the backend-backed Phase 5B.

## Unreleased - Phase 1 Foundations

- Added `--vz-*` token namespace (palette, elevation, radius, motion, perspective).
- Adopted Space Grotesk + Inter as brand fonts.
- Refactored `Button` with `primary | secondary | ghost` variants.
- Migrated `WorkspaceBand`, `WorkspaceSurface`, `MediaSurface`, `InstrumentRail`, `StatusToneBadge` to new tokens; legacy `--vezor-*` / `--argus-*` names remain as aliases.
- Lightened `AppShell` ambient gradient.

## Unreleased - Phase 2 Spatial Cockpit

- Replaced the 20 MB sign-in MP4 hero with a CSS-perspective `OmniSightLens`.
- Added `useLensTilt` pointer-driven rotation hook.
- Introduced `WorkspaceHero` and `KpiTile` primitives.
- Adopted them on `/signin` and `/dashboard`.
- Live scene tiles gained CSS-only corner brackets and Z-pop hover.
- Dropped the duplicate Sites table; replaced with cards + dedicated empty state.

## Unreleased — Phase 3 Motion Choreography

- Added Framer Motion + `motionPresets` + `useReducedMotionSafe`.
- Sliding cerulean focus indicator on the active nav route.
- Evidence selection cross-fade on `/incidents`.
- Animated bucket-selection shaft on `/history`.
- Token-driven `Toast` primitive with `useToast` hook; wired to evidence review.
- Tightened `WorkspaceTransition` keyframe.
