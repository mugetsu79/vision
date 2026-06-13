# Next Chat Handoff: Platform Support And Installer Plans

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`
Pre-planning base commit: `c8d138eb` (`Implement tracker continuity replay gate`)

## Purpose

This handoff is for starting a clean implementation chat after the
platform-support and installer-process planning work. The current chat
has accumulated tracker validation, Jetson/Central A/B runs, platform
support design discussion, and installer planning context; a new chat is
recommended for focused TDD/subagent execution.

## Current Work Product

Read these files first:

1. `docs/superpowers/specs/2026-06-13-eve-os-edge-app-packaging-design.md`
2. `docs/superpowers/specs/2026-06-13-master-installer-process-optimizations-design.md`
3. `docs/superpowers/plans/2026-06-13-edge-eve-os-and-bare-metal-image-matrix-implementation-plan.md`
4. `docs/superpowers/plans/2026-06-13-master-installer-process-optimizations-implementation-plan.md`

The edge spec was revised from EVE-OS-only framing to:

- Linux bare-metal amd64 edge installs as the shared product path;
- EVE-OS qcow2 VM packaging layered on that same installer/runtime path;
- explicit `generic-amd64`, `nvidia-amd64`, and
  `intel-openvino-amd64` edge worker image profiles;
- Jetson path preserved separately;
- no EVE-OS OCI app artifact.

The master installer spec is separate from edge work and is scoped to
bare-metal Linux/macOS master/control-plane installer process
optimizations.

## Implementation Mode

Use `superpowers:subagent-driven-development`.

Use TDD:

1. Write failing tests first.
2. Run them and confirm the expected failure.
3. Implement the smallest change for that task.
4. Run the targeted tests.
5. Update plan checkboxes as tasks complete.
6. Review the diff before moving to the next task.

Do not commit or push from the implementation chat unless the user
explicitly asks.

## Recommended Execution Order

1. Implement
   `docs/superpowers/plans/2026-06-13-master-installer-process-optimizations-implementation-plan.md`
   first if the goal is lower-risk installer reliability work.
2. Implement
   `docs/superpowers/plans/2026-06-13-edge-eve-os-and-bare-metal-image-matrix-implementation-plan.md`
   first if the goal is product platform support.

The plans are independent enough to run in separate chats or separate
subagent-driven sessions. Do not mix edge image-matrix implementation
with master installer process changes in the same task unless the plan
explicitly says to touch a shared file.

## Hard Constraints

- Preserve unrelated and untracked local files.
- Do not implement DeepStream.
- Do not implement an EVE-OS OCI app artifact.
- Do not claim central Dockerized GPU or Apple M-series acceleration.
- Do not trigger implicit ReID model downloads.
- Do not paste or commit secrets, RTSP credentials, bearer tokens,
  bootstrap tokens, sudo passwords, or raw process args.
- Redact RTSP URLs as `rtsp://***:***@<host>:8554/<path>`.
- Keep NATS, persistence, WebSocket telemetry, supervisor runtime
  reports, and existing pairing contracts compatible.

## Files Expected From This Planning Commit

Tracked modifications:

- `docs/superpowers/specs/2026-06-13-eve-os-edge-app-packaging-design.md`

New docs expected to be tracked:

- `docs/superpowers/specs/2026-06-13-master-installer-process-optimizations-design.md`
- `docs/superpowers/plans/2026-06-13-edge-eve-os-and-bare-metal-image-matrix-implementation-plan.md`
- `docs/superpowers/plans/2026-06-13-master-installer-process-optimizations-implementation-plan.md`
- `docs/superpowers/status/2026-06-13-next-chat-platform-support-and-installer-plans-handoff.md`

Unrelated local/untracked files were present before this handoff and
must remain preserved. Do not stage broad globs.

## Verification Already Run For Planning Docs

Fresh checks run before writing this handoff:

- `git diff --check`
- trailing-whitespace scan on touched spec/plan docs
- placeholder scan for plan anti-patterns
- filtered scan for sensitive-looking literals

These were docs/plans only; no backend or installer implementation tests
were run for this planning commit.

## Suggested Next-Chat Opening Prompt

```text
Continue on branch codex/sceneops-pack-registry.
Read docs/superpowers/status/2026-06-13-next-chat-platform-support-and-installer-plans-handoff.md.
Use superpowers:subagent-driven-development.
Implement the selected plan task-by-task with TDD, preserving unrelated
local files and respecting all hard constraints in the handoff.
```
