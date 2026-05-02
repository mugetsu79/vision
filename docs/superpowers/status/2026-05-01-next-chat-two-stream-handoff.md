# Next Chat Handoff: Stream 1 Closed, Stream 2 Next

Date: 2026-05-02

Purpose: paste this document into a fresh chat after `model-catalog-open-vocab-runtime` has been merged. The next chat should treat point 1 as closed and continue with point 2: OmniSight UI/UX distinctiveness.

## Repository State To Start From

Start from `main` after pulling origin:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only
git status -sb
git log --oneline -8
```

Expected:

- `main` includes the native-stream stability fixes from `codex/omnisight-ui-distinctiveness-followup`.
- `main` includes the completed model catalog and open-vocab runtime implementation from `model-catalog-open-vocab-runtime`.
- `main` includes the OmniSight UI/UX phase plans from Claude Code.
- untracked local scratch files may exist; do not stage them unless the user explicitly asks.

## Recently Closed: Point 1

Point 1 was:

```text
model catalog and open-vocabulary runtime implementation
```

Status: **closed on 2026-05-02**.

Primary docs:

- `docs/superpowers/specs/2026-05-01-model-catalog-and-open-vocab-runtime-design.md`
- `docs/superpowers/plans/2026-05-01-model-catalog-and-open-vocab-runtime-implementation-plan.md`
- `docs/imac-master-orin-lab-test-guide.md`
- `docs/runbook.md`

What landed:

- `ModelFormat.PT` and migration support for `.pt` model records.
- `GET /api/v1/model-catalog`.
- recommended catalog presets for YOLO26, YOLO11, YOLO12, YOLOE, YOLO-World, and planned TensorRT engine rows.
- `backend/scripts/register_model_preset.py` for registering operator-provided local artifacts from catalog defaults.
- validation for model format, capability, backend, and readiness combinations.
- Linux `aarch64` NVIDIA Jetson runtime profile selection.
- fixed-vocab ONNX Runtime path for YOLO26/YOLO11/YOLO12.
- experimental Ultralytics-backed open-vocab `.pt` path for YOLOE and YOLO-World.
- runtime vocabulary hot-swap for open-vocab workers.
- capability-aware Live query behavior for fixed-vocab filters versus open-vocab detector vocabulary.
- dynamic camera setup behavior: fixed-vocab active class scope uses the selected registered model classes, while open-vocab models use runtime vocabulary.
- model catalog UI cards are hidden once all ready presets are registered or intentionally planned, so registered rows do not keep cluttering camera setup.
- live stream recovery for delayed worker startup.
- worker resilience for telemetry publish timeouts and camera reconnect open failures.
- verify-all repair for the seeded model selector.

Manual lab notes from iMac testing:

- YOLO26n was much faster than YOLO12n on the tested Intel iMac/CoreML path.
- YOLO12n may still track more smoothly in some scenes because detector confidence and temporal consistency matter more than speed alone.
- for tracking accuracy, prefer frame skip `1`; start with FPS cap `20`; raise only if both workers stay stable.
- privacy blur strength affects rendering only; it does not change detector or tracker accuracy.

Still intentionally not done:

- raw TensorRT `.engine` detector runtime.

TensorRT follow-up is documented here:

- `docs/superpowers/specs/2026-05-02-tensorrt-engine-artifact-runtime-design.md`

The current TensorRT posture is: keep ONNX as the canonical portable model row; let ONNX Runtime use TensorRT/CUDA providers when available; later attach validated target-specific `.engine` artifacts to the ONNX model instead of exposing standalone `.engine` files as normal camera models.

## Next Chat: Point 2

Point 2 is:

```text
OmniSight UI/UX distinctiveness implementation
```

Primary docs:

- `docs/brand/omnisight-ui-spec-sheet.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-codex-handoff.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-1-foundations.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-2-spatial-cockpit.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-3-motion.md`
- `docs/superpowers/plans/2026-04-30-omnisight-spec-phase-4-webgl.md`

Mission:

- make OmniSight feel less generic
- land token, typography, surface, hero, motion, and optional WebGL lens phases in order
- keep the working video and setup flows stable while making pages more distinctive

Recommended execution mode:

```text
Use docs/superpowers/plans/2026-04-30-omnisight-spec-codex-handoff.md as the operating guide.
Execute phases in order.
Do not start Phase N until Phase N-1 is green and committed.
Phase 4 is gated and opt-in.
```

Pre-flight:

```bash
cd "$HOME/vision"
git status --short
corepack pnpm --dir frontend install
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Important UI notes:

- keep the obsidian/near-black canvas
- reduce default violet/blue dashboard wash
- use roughly 75% neutral dark surfaces, 15% cerulean, 5% violet, 5% status colors
- violet is a brand/entry accent, not a generic dashboard default
- avoid landing-page marketing composition inside the product
- keep video/evidence zones sharply black and inspection-oriented

## Known Cautions

- Do not use `git add -A`; unrelated untracked scratch files may exist.
- Do not mark TensorRT `.engine` support as ready until a real detector adapter and validation workflow exist.
- Do not reintroduce double RTSP reads for native/no-privacy delivery.
- Do not revert user-created or Claude-created untracked files unless explicitly asked.
- Stream 2 may touch camera/setup surfaces visually; preserve the model selection behavior from Stream 1.

## Suggested Branch Name

For Stream 2:

```bash
git switch -c codex/omnisight-ui-spec-implementation
```

## Completion Target

Stream 2 is complete when:

- phases 1-3 are committed and green
- Phase 4 is either explicitly skipped or landed behind the feature flag
- sign-in, dashboard, Live, Patterns, Evidence, Sites, Scenes, and Operations pass visual QA
