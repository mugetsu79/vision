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
