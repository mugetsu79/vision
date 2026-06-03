# Next Chat Handoff: Live Sizing And Configuration Guidance Follow-Up

Date: 2026-05-29
Last updated: 2026-06-03
Status: Main merge closeout for `codex/omnisight-live-video-window-sizing`.

Purpose: record the current Live/configuration/installer state before merging
the feature branch to `main`, and give the next chat/operator a clean `main`
update path for MacBook and Jetson hosts.

## Branch And Repository State

Post-merge source of truth:

```text
main
```

Feature branch being merged:

```text
codex/omnisight-live-video-window-sizing
```

Latest implementation checkpoint before this documentation closeout:

```text
89a8be22 Tighten live rendition UX and Jetson guidance
```

The feature branch is preserved on `origin/codex/omnisight-live-video-window-sizing`;
the merged source ref for operator updates is `origin/main`.

Commit stack after the previous `main` merge base:

```text
83176921 fix(live): preserve full video frame sizing
84540396 fix(live): gate telemetry badge on scene heartbeat
0510b26a feat(operations): remove configured scene workers
5a514645 fix(operations): delete scenes with worker history
15756c20 docs: specify production configuration hardening
1d60f289 docs: plan production configuration hardening
f6f3274a feat(config): harden runtime profiles and installer networking
c6ca8cb1 docs(config): record guidance ux follow-up
1caa1694 feat(config): add operator guidance ux
0afa17f2 fix(cameras): clarify calibration speed guidance
4fc0da54 fix(operations): backfill missing runtime defaults
aadd1c3a fix(installer): wire central worker live streaming
c9dc2e51 fix(live): refine scene tile sizing controls
89a8be22 Tighten live rendition UX and Jetson guidance
```

Start the next chat/operator update from `main`:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only origin main
git status -sb
git log --oneline -12
```

Do not create another branch unless the next chat is intentionally starting a
new implementation lane. A reasonable follow-up branch for broader UI polish is:

```bash
git switch -c codex/omnisight-ui-ux-polish
```

Known local hygiene:

- unrelated untracked scratch files may exist locally
- `taste-skill/` may exist locally for later UI work
- the configuration guidance spec and plan are tracked project history:
  - `docs/superpowers/specs/2026-06-02-configuration-guidance-ux-design.md`
  - `docs/superpowers/plans/2026-06-02-configuration-guidance-ux.md`
- do not use `git add -A`
- stage only files needed for the current task
- keep unrelated untracked files untouched

## Completed Since The 2026-05-29 Handoff

Implemented and pushed on `codex/omnisight-live-video-window-sizing`:

- Live video sizing fix: tiles preserve the full video frame and keep video
  pixels aligned with overlays during resize/focus changes.
- Live telemetry badge fix: `Telemetry live` is gated on scene heartbeat so the
  page does not claim telemetry is live when Jetson/cameras are offline.
- Operations worker management: configured scene workers can be removed from the
  UI.
- Scene/profile cleanup: scene deletion works even after worker history exists,
  and profile deletion was hardened with impact-aware behavior.
- Production configuration plumbing:
  - capability catalog and binding inventory
  - binding validation plus unbind support
  - safe default profile replacement
  - desired/applied runtime configuration summaries and hash diagnostics
  - evidence storage and privacy/retention enforcement
  - transport enforcement for WebRTC, HLS, MJPEG, and normalized legacy
    transcode profiles
  - runtime selection enforcement with selected backend/artifact and
    fallback-disabled blocking
  - LLM provider policy drafting with fail-closed missing-secret behavior
  - operations mode enforcement for disabled, polling, push, and
    restart-policy-aware recovery
  - generated OpenAPI types and UI polish for inventory, impact, unbind rows,
    delete dialogs, and effective configuration diagnostics
- Installer/networking hardening:
  - MediaMTX config rendering now derives browser-facing origins and WebRTC
    hosts from the configured public URL instead of assuming localhost.
  - Master macOS/Linux installers render MediaMTX origins/hosts from
    `--public-url`.
  - Edge installer accepts optional `--frontend-url`, derives the master
    frontend origin from `--api-url`, parses edge stream host, rewrites JWKS,
    and includes WebRTC hosts.
  - Loopback-only private service binds intentionally remain for Postgres,
    Redis, MinIO, NATS normal/monitoring, MediaMTX API, and worker metrics.
- Configuration guidance UX:
  - scene setup now explains camera sources, processing modes, source points,
    destination points, inclusion/exclusion areas, boundaries, and speed
    calibration.
  - calibration source/destination points are preserved when a scene is edited
    after being created without an initial frame capture.
  - Operations -> Control Plane Configuration explains profile kinds, binding
    scope, effective desired/applied state, runtime wiring, and diagnostics.
- Live rendition and tile follow-up:
  - Live tile sizing controls now use readable collapsed and expanded sizes.
  - duplicate telemetry labels were removed from scene tiles.
  - inherited transport and central-scene status chips render as healthy when
    the scene is operating as expected.
  - browser delivery profile changes reconnect the tile to profile-specific
    MediaMTX paths such as `annotated-240p5`; Jetson privacy preview uses
    `preview-240p5`.
- Documentation:
  - added `docs/live-video-troubleshooting.md` for blank Live video, stuck
    renditions, worker restarts, and Jetson stream checks.
  - updated installer and deployment docs for current master/Jetson update
    behavior.

Validation before the 2026-06-02 main merge closeout:

```text
backend focused pytest: 5 passed
backend focused ruff: clean
frontend focused vitest: 49 passed, existing React act(...) warnings in VideoStream tests
frontend build: passed
git diff --check: passed
```

## MacBook Test Build Update

After the branch is merged, use `main` for MacBook source updates:

```bash
cd /opt/vezor/current
git fetch origin
git switch main
git pull --ff-only origin main

MASTER_PUBLIC_HOST="YOUR_MACBOOK_PRIVATE_IP_OR_DNS"
MASTER_PUBLIC_URL="http://${MASTER_PUBLIC_HOST}:3000"
MASTER_API_URL="http://${MASTER_PUBLIC_HOST}:8000"
MASTER_KEYCLOAK_URL="http://${MASTER_PUBLIC_HOST}:8080"

sudo ./installer/macos/install-master.sh \
  --version "portable-demo" \
  --manifest installer/manifests/dev-example.json \
  --public-url "$MASTER_PUBLIC_URL" \
  --data-dir /var/lib/vezor
```

Verify both local and network access:

```bash
sudo launchctl print system/com.vezor.master
curl -fsS http://127.0.0.1:8000/healthz
curl -fsS "$MASTER_API_URL/healthz"
curl -fsS "$MASTER_KEYCLOAK_URL/realms/argus-dev/.well-known/openid-configuration"
docker ps --filter name=vezor-master
sudo grep -A8 -E 'apiAllowOrigins|webrtcAllowOrigins|hlsAllowOrigins|webrtcAdditionalHosts' /etc/vezor/mediamtx/mediamtx.yml
```

Expected MediaMTX check: browser-facing origins should include the configured
MacBook private IP/DNS origin, and WebRTC additional hosts should include the
configured private IP/DNS host rather than only `localhost` or `127.0.0.1`.

## Configuration Guidance UX Spec/Plan

Yann requested better in-product explanations for complex configuration flows.
The spec/plan were written, then implemented on the same branch:

- Scene camera setup, including source/destination calibration points and
  inclusion/exclusion areas.
- Operations -> Control Plane Configuration, covering all profile kinds and
  binding/effective-runtime behavior.
- Speed-measurement calibration guidance with practical point placement rules.

Tracked planning artifacts:

```text
docs/superpowers/specs/2026-06-02-configuration-guidance-ux-design.md
docs/superpowers/plans/2026-06-02-configuration-guidance-ux.md
```

The next useful UX work is broader polish, not this configuration guidance pass.

## Field Validation Summary

Validated by Yann after the installer branch work:

- MacBook master reinstall works with LAN HTTP Keycloak sign-in.
- Jetson edge reinstall works after network address changes.
- Native video stream is online.
- Worker telemetry posts to the master after the corrected Jetson API URL.
- Second scene startup is validated after the worker metrics-port collision fix.
- Profile/rendition switching works; Yann confirmed the Live view looked correct
  after switching from `annotated` to `240p5`.
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
- Profile-addressed rendition work remains deferred as a broader product lane.
  The current Live profile switch path is validated for the installed runtime
  flow, including reduced profiles such as `240p5`; do not reopen the larger
  product-expansion plan without approval.

Remaining product validation after the `main` merge:

1. Create one real evidence clip and review it in Evidence.
2. Exercise Operations Start/Stop/Restart/Drain for the Jetson camera.
3. Run reboot validation: Mac master service, Jetson edge service, Deployment
   heartbeat, Operations status, and Live stream.
4. If stable, record Track A/B Jetson soak evidence for registered runtime
   artifacts.
5. Only after soak evidence exists, decide whether Task 24 / DeepStream can be
   opened.

## Immediate Next Work

The previous immediate field-smoke item has been completed and removed from the
active queue. Current next choices:

1. Review, commit, and merge the focused guidance progressive-disclosure branch.
2. Continue the remaining product validation list above, especially evidence
   clip review, Operations worker lifecycle controls, reboot validation, and
   Jetson soak evidence.

## Configuration Guidance Density Feedback

Yann's 2026-06-03 feedback: the newly added configuration descriptions are too
heavy in the interface. The preferred direction is to keep fields compact and
hide richer guidance behind a circular `i` info affordance that reveals details
on demand.

Recommended next UX task: treat this as a focused guidance-density correction,
not as part of the broader UI/UX polish bucket. It should get its own short
spec/plan so the implementation can move quickly and replace always-visible
guidance with consistent info triggers across Scene setup and Control Plane
Configuration.

Spec/plan created for this follow-up:

- `docs/superpowers/specs/2026-06-03-configuration-guidance-progressive-disclosure-design.md`
- `docs/superpowers/plans/2026-06-03-configuration-guidance-progressive-disclosure.md`

Implementation completed on `codex/guidance-progressive-disclosure`:

- added reusable circular `i` guidance disclosure with click/tap open, Escape
  close, outside-click close, focus return, and screen-reader summary text for
  existing `aria-describedby` consumers.
- converted Scene setup, Homography calibration, event boundaries, detection
  regions, Control Plane profile editing, binding scope, and effective runtime
  guidance from always-visible prose to on-demand help.
- added the reusable calibration flow illustration for source points,
  destination points, measured distance, event boundaries, and detection
  regions, with reduced-motion-safe connector animation.
- preserved runtime semantics; this pass changes guidance density and visual
  explanation only.

Focused verification:

```text
frontend guidance vitest: 9 passed
combined guidance/Scene/Control Plane focused vitest: 62 passed
Live/Operations regression vitest: 24 passed
frontend build: passed
```

## Broader UI/UX Polish Later

The completed UX pass was configuration comprehension, not a general redesign.
Use `taste-skill/` as local inspiration/input only after field validation is
complete.

Later polish can still look at:

- Live tile density and focus mode polish
- rendition/profile control clarity
- Deployment/Operations visual hierarchy
- broader scene setup ergonomics
- consistency with the OmniSight visual direction

Suggested later branch after this work is merged:

```bash
git switch -c codex/omnisight-ui-ux-polish
```

## Current Documentation State

Operator-facing docs now assume source users update `main` or a release tag.
While validating a future pre-merge branch, substitute the branch name
consistently on both MacBook and Jetson:

- `README.md`
- `docs/product-installer-and-first-run-guide.md`
- `docs/macbook-jetson-cross-network-reinstall-guide.md`
- `docs/live-video-troubleshooting.md`

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
