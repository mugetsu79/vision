# Vezor Symbol Refresh Design

- Date: 2026-04-20
- Scope: Product brand asset refresh
- Status: Approved design, ready for implementation planning after user review

## Goal

Replace the current in-product `Vezor` symbol with the exact eye-and-radar symbol direction from the user-provided logo artwork, while keeping the existing `Vezor` wordmark/descripter system and the broader brand refresh intact.

This is a focused brand-asset update, not a broader logo redesign.

## Approved Direction

The approved direction is:

- use the attached logo's **symbol**
- rebuild that symbol as **SVG**
- use the rebuilt SVG in product assets instead of the current simplified symbol

The user explicitly chose SVG reconstruction instead of using the PNG directly so the mark remains crisp in compact UI placements.

## Why SVG Reconstruction

Using the attached PNG directly would introduce softness and scaling problems in the application shell, especially in compact placements such as:

- sidebar or left-rail brand marks
- sign-in lockup usage
- smaller responsive contexts

Rebuilding the symbol as SVG keeps the mark:

- sharp at small and large sizes
- consistent across lockup and symbol-only variants
- easier to maintain as part of the repo's brand asset system

## Scope

### In Scope

- update the runtime symbol asset to match the attached symbol direction
- update the full lockup asset so it uses the same rebuilt symbol
- keep `Vezor` as the wordmark name
- keep `The OmniSight Platform` as the descriptor
- keep compatibility asset files aligned where they still exist for fallback or legacy use

### Out Of Scope

- changing the product name back to `Argus`
- redesigning the wordmark typography
- altering app layout, shell, or UI composition
- changing Keycloak, env vars, package names, or other technical identifiers
- broad changes to the brand system beyond this symbol replacement

## Asset Strategy

The refresh should update these product-facing runtime assets:

- `frontend/public/brand/product-symbol-ui.svg`
- `frontend/public/brand/product-lockup-ui.svg`

Compatibility assets should remain visually aligned:

- `frontend/public/brand/argus-symbol-ui.svg`
- `frontend/public/brand/argus-lockup-ui.svg`

The existing asset routing in the frontend should stay unchanged. The goal is to improve the artwork, not to rewire how the app references brand files.

## Visual Rules

### Symbol

The rebuilt symbol should faithfully follow the attached eye-and-radar mark:

- same overall silhouette
- same vigilant eye structure
- same central blue intelligence core
- same cerulean-to-violet gradient character
- same disciplined premium dark-mode feel

The reconstruction should preserve the recognizable shape rather than reinterpreting it into a flatter or more generic icon.

### Lockup

The full lockup should combine:

- the rebuilt attached symbol
- the current `Vezor` wordmark
- the current `THE OMNISIGHT PLATFORM` descriptor treatment

This means the symbol changes, but the brand naming and lockup hierarchy remain consistent with the current Vezor rename.

### Product Behavior

The product should continue using:

- full lockup where the app already shows a full lockup
- symbol-only asset where the app already uses symbol-only treatment

No new placement rules are needed in this change.

## Implementation Notes

- Rebuild the symbol as vector SVG rather than embedding raster artwork.
- Keep metadata (`title`, `desc`, `aria-label`) aligned with `Vezor`.
- Preserve transparent-background product usage.
- Keep the symbol legible at compact UI sizes.
- Avoid adding extra glow, sparkle, or hero-presentation artifacts beyond what the attached symbol already implies.

## Verification

Implementation should verify:

- the product lockup component still resolves the correct asset paths
- symbol-only mode still renders cleanly
- the frontend build still passes
- targeted lockup tests still pass

## Success Criteria

This refresh is successful if:

1. the app visibly uses the attached symbol direction instead of the old simplified symbol
2. the symbol remains crisp in compact and full lockup contexts
3. the `Vezor` rename remains intact
4. no frontend asset wiring or brand metadata regressions are introduced
