# Pre-Polish Operator Corrections Design

Date: 2026-06-03
Status: Proposed for `codex/guidance-progressive-disclosure`

## Product Goal

Fix the concrete operator-facing issues found while testing the progressive
guidance branch, without turning this into the broader OmniSight UI/UX polish
work. The branch should remain useful for MacBook field testing before the
larger redesign starts.

## Scope

This is a focused correction pass for four problems:

1. Scene setup `Privacy, Processing & Delivery` layout breaks when the page is
   narrower than fullscreen.
2. The detection-region calibration illustration is cramped; the exclusion zone
   sits too low and visually collides with calibration lines.
3. The Operations scene intelligence matrix is difficult to scan, especially
   the `central / Central` mode copy and the dense table lines.
4. Deployment installer package copy implies a separate "macOS master" product,
   even though the installed runtime is Docker/Linux services on a macOS host.

## Non-Goals

- Do not change runtime semantics, installer scripts, deployment APIs, or stream
  profile behavior.
- Do not redesign the whole Operations page.
- Do not rename routes.
- Do not add new dependencies.
- Do not rework the configuration progressive-disclosure component model.

The whole Operations page being overloaded is real, but it belongs in the later
UI/UX polish work because it needs information architecture changes across
Deployment, Operations, Control Plane Configuration, scene workers, diagnostics,
and runtime state.

## Recommended Approach

Use a small corrective pass now:

- Make the Scene setup delivery controls responsive and self-contained.
- Recompose the region illustration so source/destination mapping stays legible
  and the include/exclusion regions are visually separate from calibration
  connectors.
- Replace the matrix table with a compact per-scene row/card layout that keeps
  the same data but removes the spreadsheet feel.
- Rename installer cards as host targets, not operating-system product flavors.

This keeps field testing moving while the broader polish spec can later address
Operations page density, navigation, disclosure, and workflow grouping.

## Scene Setup Delivery Layout

The current `Live delivery` section uses a two-column grid where the transport
profile, rendition segmented controls, and processed resolution/FPS controls can
overflow into the sidebar when the page is not fullscreen.

Required behavior:

- The section must fit at tablet/medium desktop widths without horizontal
  overlap.
- The transport select and rendition controls should stack before they force
  overflow.
- The processed rendition controls should use a compact two-column layout only
  when enough width exists; otherwise they stack.
- The `Processed custom` option should not be clipped by the wizard sidebar.
- The warning list about unavailable source resolutions should wrap inside the
  card and remain readable.

Suggested copy:

- Rename `Live delivery` to **Browser stream**.
- Keep the visible explanation short: `Choose the transport path and the video
  rendition operators will watch in Live.`
- Keep detailed transport/rendition explanation behind the existing guidance
  disclosure if additional help is needed later.

## Calibration Region Illustration

The region illustration should communicate that include/exclusion regions are
drawn on the calibrated top-down plane after source/destination mapping.

Required behavior:

- The region variant should have more internal space than the generic
  source/destination illustration.
- Connector lines should sit behind regions and labels.
- The include region should be centered inside the top-down plane.
- The exclusion region should be inside the plane, not pressed against the
  bottom edge.
- Labels must not overlap connectors, destination point labels, or the region
  shapes.
- The illustration must remain accessible with a mode-specific name and
  description.
- Reduced-motion behavior remains unchanged.

Implementation preference:

- Keep one reusable `CalibrationFlowIllustration` component.
- Add mode-specific layout coordinates rather than separate components.
- Do not use generated image assets; keep the SVG code-native and testable.

## Scene Intelligence Matrix

The current table shows useful runtime truth, but the presentation is too dense
and table-like. The `Mode` cell such as `central / Central` is not meaningful to
operators, and row dividers plus badge columns create visual noise.

Required behavior:

- Rename **Scene intelligence matrix** to **Scene readiness**.
- Replace the table with a responsive card/list row layout inside the same
  component.
- Each scene row should lead with scene name, site, and a clear placement line:
  - `Central processing on master supervisor`
  - `Edge processing on Jetson`
  - fallback: `<Mode> processing on <Node>`
- Preserve honest status signals for privacy, worker, rules, transport, live
  rendition, and telemetry.
- Group signals into two readable clusters:
  - **Runtime:** worker, telemetry, rules
  - **Stream:** transport, live rendition, privacy
- Keep the row action link accessible and visible.
- Keep unknown/offline/not-reported states explicit.

Non-goal:

- Do not hide diagnostics behind tabs in this correction pass. That is later
  Operations page polish.

## Installer Package Copy

The installer target cards should describe where the installer runs and what it
installs.

Required behavior:

- Replace `macOS master` with **MacBook local master** or **macOS host master**.
- Describe it as `Docker-backed local master`.
- Keep `installer/macos/install-master.sh` visible because the command is still
  correct.
- Clarify that the macOS installer creates a launchd wrapper for Docker-backed
  master services.
- Rename `Linux master` to **Linux host master** and describe it as
  `Systemd Docker master`.
- Keep `Jetson edge` unchanged except for copy consistency.

## Acceptance Criteria

- Scene setup delivery controls do not overflow at 1024px width.
- Detection region help opens with a clear non-overlapping diagram.
- Operations scene readiness rows are easier to scan and no longer show
  `central / Central`.
- Installer target names accurately describe host targets and Docker-backed
  runtime.
- Existing focused frontend tests pass.
- Frontend build passes.

## Later UX/UI Polish Carry-Forward

The broader polish spec must explicitly include Operations page overload:

- Operators need an attention-first Operations landing state.
- Dense diagnostics should be progressively disclosed.
- Worker lifecycle, deployment nodes, stream diagnostics, configuration
  bindings, and effective runtime state should become navigable sections rather
  than one long loaded page.
