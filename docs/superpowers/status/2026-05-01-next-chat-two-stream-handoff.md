# Next Chat Two-Stream Handoff

Date: 2026-05-01

Purpose: paste this document into fresh chats so the next work can split cleanly into two streams:

1. model catalog and open-vocabulary runtime implementation
2. OmniSight UI/UX distinctiveness implementation

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

- `main` includes the native-stream stability fixes from `codex/omnisight-ui-distinctiveness-followup`
- `main` includes the model catalog/open-vocab spec and plan
- `main` includes the OmniSight UI/UX phase plans from Claude Code
- untracked local scratch files may exist; do not stage them unless the user explicitly asks

## Recently Merged Context

The merged branch was:

- `codex/omnisight-ui-distinctiveness-followup`

Important runtime fixes already on that branch:

- `fix: prevent telemetry reload freeze`
- `fix: bound native mjpeg stream capture`
- `fix: avoid source reprobe on privacy edit`
- `fix: ingest direct rtsp for passthrough detection`
- `fix: avoid double camera reads for native overlay`

Current video behavior:

- native and `720p10` can show video
- native/no-privacy avoids double camera reads by using worker-published clean native delivery rather than true central passthrough
- Live UI should label internal native/no-privacy stream mode as clean native, not annotated intent
- detection still runs in native mode; burned-in privacy annotations are bypassed only when privacy filters are off

## Stream 1: Model Catalog And Open-Vocab Runtime

Primary docs:

- `docs/superpowers/specs/2026-05-01-model-catalog-and-open-vocab-runtime-design.md`
- `docs/superpowers/plans/2026-05-01-model-catalog-and-open-vocab-runtime-implementation-plan.md`

Mission:

- add recommended model catalog options
- make YOLO26/YOLO11 fixed-vocab ONNX registration straightforward
- keep YOLO12 as lab compatibility, not the forward default
- add Jetson ARM64 NVIDIA runtime classification
- replace the current open-vocab wrapper with a true Ultralytics-backed YOLOE / YOLO-World adapter
- keep raw TensorRT `.engine` marked planned until a dedicated engine detector exists

Recommended execution mode:

```text
Use superpowers:executing-plans or superpowers:subagent-driven-development.
Execute docs/superpowers/plans/2026-05-01-model-catalog-and-open-vocab-runtime-implementation-plan.md task by task.
```

Key implementation decisions already made:

- registered `Model` rows remain the canonical selectable camera inventory
- the catalog is a registration aid, not a parallel runtime registry
- fixed-vocab ready path is ONNX Runtime with provider selection
- open-vocab experimental path is Ultralytics `.pt`
- raw `.engine` records must not be advertised as ready
- model binaries stay out of git

First tasks to run:

1. Extend model contracts and validation with `ModelFormat.PT`.
2. Add recommended model catalog API.
3. Add Jetson NVIDIA runtime profile.
4. Implement the true open-vocab detector adapter.

Verification focus:

```bash
cd "$HOME/vision/backend"
python3 -m uv run pytest tests/services/test_model_service.py tests/services/test_model_catalog.py tests/vision/test_runtime.py tests/vision/test_open_vocab_detector.py tests/vision/test_detector_factory.py tests/inference/test_engine.py -q
python3 -m uv run ruff check src tests
python3 -m uv run mypy src
cd "$HOME/vision"
corepack pnpm --dir frontend build
corepack pnpm --dir frontend exec vitest run src/components/cameras/CameraWizard.test.tsx src/pages/Cameras.test.tsx
```

Manual validation target:

- register `YOLO26n COCO` from `models/yolo26n.onnx`
- register `YOLOE-26N Open Vocab` from `models/yoloe-26n-seg.pt`
- create one fixed-vocab camera and one open-vocab camera
- start workers
- update open-vocab terms from Live query
- confirm worker updates detector vocabulary without restart

## Stream 2: OmniSight UI/UX Distinctiveness

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

Phase summary:

- Phase 1: `--vz-*` tokens, brand fonts, lighter shell, Button variants, WorkspaceBand density/accent, primitive token migration
- Phase 2: CSS lens/brackets, `useLensTilt`, `OmniSightLens`, `WorkspaceHero`, dashboard rewrite, sign-in rewrite, Live tile brackets, Sites cleanup
- Phase 3: Framer Motion, motion presets, nav focus shaft, evidence cross-fade, Patterns bucket shaft, toast provider/hook, tightened transitions
- Phase 4: opt-in WebGL lens behind `VITE_FEATURE_WEBGL_LENS`, capability check, optional GLB upgrade, bundle audit

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

## Coordination Between Streams

The streams can run separately, but they touch shared frontend areas:

- Camera wizard/model select may be touched by Stream 1.
- Surface primitives and workspace shell may be touched by Stream 2.

To avoid collisions:

- run Stream 1 first if model functionality is more urgent
- run Stream 2 first if visual QA/demo polish is more urgent
- if both run in parallel, keep Stream 1 frontend scope to model metadata/catalog UI only, and keep Stream 2 away from model behavior

## Known Cautions

- Do not use `git add -A`; there are unrelated untracked scratch files in the workspace.
- Do not mark TensorRT `.engine` support as ready until a real detector adapter exists.
- Do not assume OpenVocabDetector is currently real; it is control-plane ready but runtime-incomplete until Stream 1 lands.
- Do not reintroduce double RTSP reads for native/no-privacy delivery.
- Do not revert user-created or Claude-created untracked files unless explicitly asked.

## Suggested Branch Names

For Stream 1:

```bash
git switch -c codex/model-catalog-open-vocab-runtime
```

For Stream 2:

```bash
git switch -c codex/omnisight-ui-spec-implementation
```

## Completion Target

Stream 1 is complete when:

- YOLO26/YOLO11 catalog presets can be registered
- Jetson runtime profile is recognized
- YOLOE or YOLO-World `.pt` can run through a true open-vocab adapter
- Live query hot-swaps runtime vocabulary without worker restart

Stream 2 is complete when:

- phases 1-3 are committed and green
- Phase 4 is either explicitly skipped or landed behind the feature flag
- sign-in, dashboard, Live, Patterns, Evidence, Sites, Scenes, and Operations pass visual QA
