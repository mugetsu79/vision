# Argus Logo Usage Guide

Date: 2026-04-19

This guide explains how to use the Argus logo system consistently across product, marketing, documentation, and hardware surfaces.

Use this alongside [argus-logo-brand-spec.md](/Users/yann.moren/vision/docs/brand/argus-logo-brand-spec.md).

## Approved Logo Variants

The Argus identity should exist in four core variants:

1. **Hero glow lockup**
   - Used for website hero sections, launch graphics, keynote slides, and premium brand moments.
   - Includes restrained cerulean-to-violet glow.
   - Should be used sparingly.

2. **Product/UI lockup**
   - Used inside the application shell, sign-in page, settings, documentation headers, and admin surfaces.
   - Minimal lighting effects.
   - Cleaner and flatter than the hero version.

3. **Monochrome lockup**
   - Used for print, hardware labels, embossing, laser etching, and single-ink constraints.
   - No glow, no gradient dependency.

4. **Symbol-only mark**
   - Used for app icons, favicons, avatars, compact navigation, and square crops.
   - Must remain readable at very small sizes.

## Preferred Backgrounds

### Best backgrounds

- deep obsidian
- charcoal
- dark blue-black
- subtle matte gradients in the Argus dark palette

### Acceptable backgrounds

- white or very light gray only for monochrome or carefully adapted flat variants
- low-noise photography only when contrast remains strong

### Avoid

- busy textures
- heavily saturated color fields
- low-contrast mid-gray surfaces
- cluttered UI screenshots behind the mark

## Clear Space

Always keep clear space around the logo.

Minimum clear space:

- use at least the width of the logo core node around the full lockup
- for the symbol-only mark, use at least one quarter of the symbol width as clear space on all sides

Nothing should visually crowd the logo, especially in dashboards and slide headers.

## Minimum Size

The logo must stay legible at small sizes.

Recommended minimums:

- full lockup on screen: `160 px` wide
- full lockup in print: `35 mm` wide
- symbol-only icon on screen: `24 px`
- favicon-style simplified icon: `16 px`

Below those thresholds, prefer the symbol-only mark or a simplified mark.

## When To Use Each Variant

### Hero glow lockup

Use when:

- introducing the brand
- presenting the platform in marketing
- opening pitch decks
- creating launch visuals

Do not use it as the default in dense product UI.

### Product/UI lockup

Use when:

- displaying the brand inside the app
- showing the sign-in screen
- placing the brand in documentation
- using persistent top-nav or footer branding

This should be the default operational logo.

### Monochrome lockup

Use when:

- there is no reliable dark background
- production methods limit color
- the logo must be robust in harsh reproduction conditions

### Symbol-only mark

Use when:

- space is constrained
- the full wordmark would be too small
- the brand is already established elsewhere in the layout

## Typography Hierarchy

The wordmark hierarchy must remain stable:

- `Argus` is the primary reading target
- `|` is subtle and structural
- `THE OMNISIGHT PLATFORM` is secondary

Do not enlarge or bold the tagline to compete with `Argus`.

## Glow Rules

Glow is part of the identity, but it must remain controlled.

Rules:

- keep glow soft and deliberate
- keep the cerulean core brighter than the violet perimeter
- avoid making the mark look like neon signage
- reduce glow in operational UI contexts
- remove glow entirely in monochrome usage

## Icon Integrity Rules

Do not:

- stretch the symbol
- rotate the symbol arbitrarily
- redraw internal shapes inconsistently
- add extra flares, sparkles, or rings
- separate the icon into decorative fragments

If a simplified version is needed for tiny sizes, it should be a formally approved simplification, not an ad hoc redraw.

## Hardware And Print Guidance

For hardware labeling and print:

- prefer monochrome or low-effect versions
- check contrast against the actual material finish
- avoid fine glow details that will disappear in fabrication
- use the symbol-only mark when physical space is tight

For etched or embossed applications:

- use thicker internal shapes
- preserve silhouette clarity
- remove all gradient-dependent meaning

## Product UI Guidance

Inside the Argus product:

- prefer the flat or low-effect lockup
- keep the logo on clean dark surfaces
- avoid placing the logo inside visually noisy cards
- use the symbol-only mark in tight navigation patterns if the full lockup feels crowded

## QA Checklist

Before approving any new use of the logo, confirm:

- the correct variant is being used
- contrast is strong
- the tagline is secondary
- the icon remains legible
- glow is not overdone
- spacing is sufficient
- no decorative artifacts were added

## Recommended Asset Set

The final approved brand package should include:

- `argus-logo-hero.svg`
- `argus-logo-ui.svg`
- `argus-logo-mono-dark.svg`
- `argus-logo-mono-light.svg`
- `argus-symbol.svg`
- `argus-symbol-small.svg`
- PNG exports at standard app, deck, and documentation sizes
