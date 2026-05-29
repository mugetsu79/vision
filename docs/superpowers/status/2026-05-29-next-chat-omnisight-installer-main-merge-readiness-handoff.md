# Next Chat Handoff: Main After Installer Merge

Date: 2026-05-29
Last updated: 2026-05-29
Status: Current handoff for continuing from `main` after the installer merge.

Purpose: start the next chat from merged `main`, verify the installed MacBook
master plus Jetson edge path if needed, then fix the Live video stream window
sizing/rendering issue before starting broader UI/UX polish.

## Branch And Repository State

Current source of truth:

```text
main
```

Latest pushed checkpoint:

```text
b9f2d5ef docs(installer): record main merge readiness
```

`codex/omnisight-installer` was fast-forward merged into `main` and pushed to
origin. `omnisight-ui-check` is not a separate blocker; it points at
`d5282c60 docs: refresh markdown cleanup and handoff`, which is already in
`main`.

Start the next chat with:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
git status -sb
git log --oneline -12
```

Recommended branch for the next focused fix:

```bash
git switch -c codex/omnisight-live-video-window-sizing
```

Known local hygiene:

- unrelated untracked scratch files may exist locally
- `taste-skill/` may exist locally for later UI work
- do not use `git add -A`
- stage only files needed for the current task
- keep unrelated untracked files untouched

## Field Validation Summary

Validated by Yann after the installer branch work:

- MacBook master reinstall works with LAN HTTP Keycloak sign-in.
- Jetson edge reinstall works after network address changes.
- Native video stream is online.
- Worker telemetry posts to the master after the corrected Jetson API URL.
- Second scene startup is validated after the worker metrics-port collision fix.
- Profile/rendition switching appears to work.
- Live scene deletion exists for cleaning up old scenes such as `Room1`.

## Carry-Forward Context From Older Handoffs

The older handoffs are superseded as starting points, but the following context
still matters. Do not treat omission from the immediate task list as proof that
these were re-tested or no longer exist.

Validated earlier in the installer branch:

- MacBook master can install and expose first-run.
- First-run can create the tenant/admin.
- Sign-in works after the LAN HTTP / Keycloak fixes.
- Deployment shows central and Jetson nodes.
- Jetson edge install succeeds with the Python 3.10 ONNX Runtime GPU wheel.
- Jetson reports hardware/service health after pairing.
- Model rows can be registered and appear in scene setup.
- TensorRT engines for YOLO26n and YOLO26s were built on the Jetson and
  registered as runtime artifacts.
- Native passthrough and annotated streams can be switched from Live.
- Annotated live video draws detection boxes.

Historical fixes now covered by current installer docs:

- Edge workers must use `nats://nats-leaf:4222`, not `127.0.0.1:4222`.
- The master NATS leaf listener must be reachable on `7422`.
- Product MediaMTX needs UDP `8189` exposed for WebRTC browser delivery.
- Jetson worker containers need the runtime model alias mounted at `/models`.
- Worker-config must allow paired supervisor credentials while still rejecting
  viewers.
- Disabled evidence recording should not block live worker config on unused
  privacy/storage residency mismatch.
- Stale product-owned Jetson containers can hold ports; the current installer
  performs cleanup before preflight.
- Older Ultralytics BoT-SORT constructors may not accept a `frame_rate`
  keyword; tracker construction handles that compatibility.

Operational guidance that still applies:

- Camera setup must assign the Jetson edge node in the scene/camera flow; an
  Operations profile binding alone does not make the source edge-owned.
- The scene model dropdown should select canonical model rows such as
  `YOLO26n COCO`. TensorRT is a runtime artifact attached to that row, not a
  separate scene model.
- The default ONNX export is static 640x640. Build TensorRT engines with
  `trtexec --onnx ... --fp16`; do not pass dynamic `--shapes=...` for that
  export.
- The installed Jetson worker image uses Python 3.10 for the Jetson ONNX
  Runtime GPU wheel. Installer/admin tooling uses Python 3.12.
- Short-lived browser/admin tokens are setup/admin tooling only, not normal
  product operation.
- If the portable network changes, rerun the Jetson installer with
  `--unpaired --public-stream-host NEW_JETSON_IP_OR_HOSTNAME`, or use the
  full public MediaMTX RTSP URL option for forwarded RTSP ports.

Historical live runtime caveats:

- Earlier logs showed annotated `720p25` rendering below 25fps because the
  inference loop was around 67-72ms/frame. Treat profile FPS values as
  targets/caps, not guaranteed burned-in annotation throughput.
- Earlier logs showed RTSP `capture_wait` p99/max spikes around 560-590ms.
  That can cause tracker flicker independent of the Live tile sizing issue.
- Profile-addressed rendition work was marked deferred after field validation.
  Current profile/rendition switching appeared to work, but do not reopen the
  larger product-expansion plan without approval.

Remaining product validation after the Live sizing fix:

1. Create one real evidence clip and review it in Evidence.
2. Exercise Operations Start/Stop/Restart/Drain for the Jetson camera.
3. Run reboot validation: Mac master service, Jetson edge service, Deployment
   heartbeat, Operations status, and Live stream.
4. If stable, record Track A/B Jetson soak evidence for registered runtime
   artifacts.
5. Only after soak evidence exists, decide whether Task 24 / DeepStream can be
   opened.

## Immediate Next Work

Priority before broad UI/UX polish:

```text
Fix Live video stream window sizing/rendering.
```

Observed issue:

- Increasing or decreasing the Live video window size can produce odd video
  resolution/rendering behavior.
- This appears separate from the installer path and separate from basic
  profile/rendition switching, which has been field-validated enough for now.

Recommended debugging shape:

1. Reproduce on current `main` with one live Jetson scene and, if practical, two
   live scenes.
2. Capture desktop and narrow/mobile screenshots or browser recordings.
3. Inspect the Live layout and stream components before changing behavior:
   - `frontend/src/pages/Live.tsx`
   - `frontend/src/components/live/VideoStream.tsx`
   - `frontend/src/components/live/TelemetryCanvas.tsx`
   - any CSS/classes controlling tile aspect ratio, object fit, and stream
     canvas/video sizing
4. Identify whether the problem is:
   - CSS/layout aspect-ratio drift
   - video element `object-fit` or intrinsic-size handling
   - overlay canvas size desync
   - WebRTC/HLS reconnect or rendition URL choice after tile resize
   - profile metadata being displayed as if it were actual decoded dimensions
5. Fix the smallest proven cause.
6. Add focused tests where possible, then do browser visual QA.

Suggested verification for this fix:

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Live.test.tsx src/components/live/VideoStream.test.tsx src/components/live/TelemetryCanvas.test.tsx
corepack pnpm --dir frontend exec eslint src/pages/Live.tsx src/components/live/VideoStream.tsx src/components/live/TelemetryCanvas.tsx
corepack pnpm --dir frontend exec tsc -b
```

Use browser visual QA after the code tests:

- one scene, native stream
- one scene, annotated stream
- one scene, reduced rendition
- two scenes visible
- resize/focus tile up and down repeatedly
- confirm overlay boxes and video pixels stay aligned

## Broader UI/UX Polish Comes After

The plan was to review UI/UX again after the installer merge, and that still
makes sense. Do this only after the video window sizing issue is fixed or
clearly isolated.

Use `taste-skill/` as local inspiration/input for the later UI pass, but keep
the first branch narrowly focused on video sizing/rendering. The later UI/UX
branch can then look at:

- Live tile density and focus mode polish
- rendition/profile control clarity
- Deployment/Operations visual hierarchy
- scene setup ergonomics
- consistency with the OmniSight visual direction

Suggested later branch:

```bash
git switch -c codex/omnisight-ui-ux-polish
```

## Current Documentation State

Operator-facing docs now assume source users update `main` or a release tag:

- `README.md`
- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/documentation-audit-2026-05-19.md`

Current operator docs to keep discoverable:

- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/runbook.md`
- `docs/operator-deployment-playbook.md`
- `docs/deployment-modes-and-matrix.md`
- `docs/model-loading-and-configuration-guide.md`
- `docs/scene-vision-profile-configuration-guide.md`

Legacy lab guides remain archived:

- `archive/macbook-pro-jetson-portable-demo-install-guide.md`
- `archive/imac-master-orin-lab-test-guide.md`

## Guardrails

- Do not reopen profile-addressed rendition work as a product-expansion lane
  without a fresh approval pass.
- Do not start Task 24 / DeepStream until Track A/B Jetson soak evidence exists
  or the risk is explicitly accepted.
- Keep WebGL off unless Yann explicitly reopens that track.
