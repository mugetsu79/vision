# Next Chat Handoff: Live Sizing And Configuration Guidance Follow-Up

Date: 2026-05-29
Last updated: 2026-06-02
Status: Current handoff for continuing from pushed branch `codex/omnisight-live-video-window-sizing` before merge to `main`.

Purpose: start the next chat from the pushed Live/configuration branch, verify
the MacBook test build if needed, then continue with the new configuration
guidance UX spec/plan.

## Branch And Repository State

Current source of truth:

```text
codex/omnisight-live-video-window-sizing
```

Latest pushed checkpoint:

```text
f6f3274a feat(config): harden runtime profiles and installer networking
```

The branch is pushed to `origin/codex/omnisight-live-video-window-sizing`.
`main` remains the last merged base for this work until the branch is merged.

Commit stack after `main`:

```text
83176921 fix(live): preserve full video frame sizing
84540396 fix(live): gate telemetry badge on scene heartbeat
0510b26a feat(operations): remove configured scene workers
5a514645 fix(operations): delete scenes with worker history
15756c20 docs: specify production configuration hardening
1d60f289 docs: plan production configuration hardening
f6f3274a feat(config): harden runtime profiles and installer networking
```

Start the next chat with:

```bash
cd "$HOME/vision"
git fetch origin
git switch codex/omnisight-live-video-window-sizing
git pull --ff-only origin codex/omnisight-live-video-window-sizing
git status -sb
git log --oneline -12
```

Do not create another branch unless the next chat is intentionally starting a
new implementation lane. If the configuration guidance UX work begins before
this branch is merged, a reasonable follow-up branch is:

```bash
git switch -c codex/omnisight-configuration-guidance-ux
```

Known local hygiene:

- unrelated untracked scratch files may exist locally
- `taste-skill/` may exist locally for later UI work
- the current uncommitted intended docs are:
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

Validation before the latest push:

```text
backend pytest: 145 passed, 57 warnings
backend ruff: clean
frontend vitest: 75 passed, existing React act(...) warnings in VideoStream tests
frontend build: passed
installer validation: 67 passed, shell syntax, executable bits, manifest validation, secret scan, master/edge compose render all passed
```

## MacBook Test Build Update

Use this branch, not `main`, until the branch is merged:

```bash
cd /opt/vezor/current
git fetch origin
git switch codex/omnisight-live-video-window-sizing
git pull --ff-only origin codex/omnisight-live-video-window-sizing

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

Yann requested better in-product explanations for complex configuration flows,
especially:

- Scene camera setup, including source/destination calibration points and
  inclusion/exclusion areas.
- Operations -> Control Plane Configuration, covering all profile kinds and
  binding/effective-runtime behavior.
- Additional guidance wherever it improves the operator experience.

Created but not yet committed unless the next chat chooses to commit them:

```text
docs/superpowers/specs/2026-06-02-configuration-guidance-ux-design.md
docs/superpowers/plans/2026-06-02-configuration-guidance-ux.md
```

Recommended next implementation shape:

1. Smoke the branch install/UI on the MacBook if field validation is the next
   priority.
2. Execute the configuration guidance UX plan if product UX is next:
   - add shared guidance data/types/components
   - add `scene-guidance.ts` and `configuration-guidance.ts`
   - integrate Scene calibration guidance in the camera wizard, homography, and
     boundary canvas surfaces
   - integrate Control Plane Configuration guidance in profile editing,
     bindings, and effective desired/applied runtime panels
   - run focused frontend tests and build

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

Remaining product validation now that the branch includes the Live sizing fix:

1. Create one real evidence clip and review it in Evidence.
2. Exercise Operations Start/Stop/Restart/Drain for the Jetson camera.
3. Run reboot validation: Mac master service, Jetson edge service, Deployment
   heartbeat, Operations status, and Live stream.
4. If stable, record Track A/B Jetson soak evidence for registered runtime
   artifacts.
5. Only after soak evidence exists, decide whether Task 24 / DeepStream can be
   opened.

## Immediate Next Work

Primary choices for the next chat:

1. Field-smoke the pushed branch on the MacBook:
   - update the install from `codex/omnisight-live-video-window-sizing`
   - confirm local and LAN health endpoints
   - confirm MediaMTX origins/hosts are rendered from the configured MacBook
     private IP/DNS
   - check Live when Jetson/cameras are offline so `Telemetry live` stays hidden
   - check scene/profile/worker deletion behavior
   - check runtime configuration panels for effective desired/applied state
2. Begin the configuration guidance UX implementation:
   - use the plan in
     `docs/superpowers/plans/2026-06-02-configuration-guidance-ux.md`
   - consider `superpowers:executing-plans` for sequential execution or
     subagent-driven work if the next chat explicitly wants parallel agents
   - keep the implementation UX-focused and avoid changing runtime semantics
     unless the plan exposes a real integration gap
3. If product stability is the priority, continue the remaining validation list
   above before starting a broader UI/UX polish branch.

Suggested verification after guidance UX work:

```bash
corepack pnpm --dir frontend exec vitest run
corepack pnpm --dir frontend run build
```

Use browser visual QA after code tests:

- scene camera setup with source/destination calibration guidance visible
- inclusion/exclusion area editing with clear guidance and validation states
- each Control Plane Configuration profile kind
- bindings, unbind, default profile, delete impact, and effective runtime views
- narrow and desktop viewports

## Broader UI/UX Polish Later

The focused next UX pass is configuration comprehension, not a general redesign.
Use `taste-skill/` as local inspiration/input only after the guidance work or
field validation is complete.

Later polish can still look at:

- Live tile density and focus mode polish
- rendition/profile control clarity
- Deployment/Operations visual hierarchy
- broader scene setup ergonomics
- consistency with the OmniSight visual direction

Suggested later branch after this pushed branch is merged:

```bash
git switch -c codex/omnisight-ui-ux-polish
```

## Current Documentation State

Operator-facing docs still assume source users update `main` or a release tag.
For testing the current changes before merge, use
`codex/omnisight-live-video-window-sizing`:

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
