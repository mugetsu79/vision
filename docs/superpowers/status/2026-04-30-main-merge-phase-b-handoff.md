# Main Merge And Phase B Validation Handoff

Date: 2026-04-30

Purpose: paste this document into a fresh project chat so the next session can pick up after the source-aware delivery, calibration, UI redesign, and Phase A iMac validation work was merged to `main`.

## Current Repository State

Primary branch:

- `main`

Merged checkpoint:

- `d5a593e docs(handoff): record phase a validation checkpoint`

The former work branch is also at the same commit:

- `codex/source-aware-delivery-calibration-fixes`

The branch was fast-forwarded into `main` after `make verify-all` passed on the real iMac dev machine.

To prepare a checkout for the next session:

```bash
cd "$HOME/vision"
git fetch origin
git switch main
git pull --ff-only
git log --oneline -5
git status -sb
```

Expected:

- `main` includes `d5a593e`
- no tracked local changes unless the user has edited files locally
- untracked scratch files can exist and should not be staged unless the user explicitly asks

## What Is Done

Do not re-plan these areas by default:

- Operations phase 1 at `/settings`
- source-aware browser delivery
- setup preview and normalized boundary authoring
- History / Patterns
- open-vocab control-plane foundation
- Evidence Desk review queue
- deployment docs, runbook, playbook, and iMac / Jetson lab guide
- Approach C app-wide UI redesign
- official 2D/3D logo asset wiring
- iMac-only Phase A validation
- `make verify-all` E2E repair
- Camera2 capture fallback fix

If validation finds a real bug in any of these areas, debug and fix it systematically, but do not restart their design plans unless the user explicitly asks.

## Phase A Result

Phase A was validated manually on the real iMac dev machine.

Confirmed:

- two configured cameras and workers
- Camera1 stream worked
- Camera2 initially exposed a capture edge case where raw ffmpeg stdout could stall even though OpenCV FFMPEG could read frames
- worker capture now falls back to OpenCV latest-frame capture when raw ffmpeg produces no first frame
- both video streams stayed live after the fallback fixes
- History / Patterns showed increments
- Evidence Desk rendered correctly; zero records is acceptable when no incident has been captured
- Operations remained honest by showing `0` running workers when per-worker heartbeat truth was not reported
- `make verify-all` passed after installing Helm

Relevant latest commits:

- `01567ee fix(e2e): align verify suite with redesigned workspace`
- `64489b8 fix(frontend): harden vitest browser globals`
- `bf26e79 fix(camera): satisfy opencv fallback typing`
- `6a0a92f fix(camera): drain opencv rtsp fallback in background`
- `7e00257 fix(camera): fall back when raw ffmpeg stalls`
- `047e04a Implement Approach C app-wide redesign`

## Validation Baseline

Latest known-good repo-level command on the iMac:

```bash
make verify-all
```

Expected success shape:

- backend migrations pass
- backend `ruff`, `mypy`, and tests pass
- frontend API generation, lint, tests, and build pass
- Playwright E2E passes all 8 tests
- Helm templates render
- runtime health returns `{"status":"ok"}`

Helm is required for this command:

```bash
brew install helm
helm version --short
```

Known non-fatal warnings:

- frontend lint still reports existing warnings in `HistoryTrendChart.tsx`, `TopNav.tsx`, `VideoStream.tsx`, and `Incidents.tsx`
- `VideoStream` tests emit React `act(...)` warnings
- local backend tests may warn that `/run/secrets` does not exist

## Next Goal

Proceed with **Phase B: iMac master + Jetson Orin edge validation**.

Keep the iMac as the temporary master:

- iMac runs control plane
- camera 1 stays central on the iMac
- camera 2 moves to Jetson edge
- validate Live, History / Patterns, Operations, and Evidence Desk across the split

Primary guide:

- `docs/imac-master-orin-lab-test-guide.md`

Also useful:

- `docs/superpowers/status/2026-04-28-imac-jetson-dev-validation-handoff.md`
- `docs/operator-deployment-playbook.md`
- `docs/runbook.md`
- `docs/deployment-modes-and-matrix.md`

## Phase B Checklist

1. Confirm iMac stack is healthy on `main`.
2. Keep camera 1 central worker running on the iMac.
3. Stop the iMac worker for camera 2 before moving camera 2 to edge.
4. Prepare Jetson in 25 W Super mode:

```bash
sudo nvpmodel -m 2
sudo jetson_clocks
cd "$HOME/vision"
./scripts/jetson-preflight.sh
```

5. Ensure Jetson can reach the iMac services:

- backend `8000`
- Keycloak `8080`
- Postgres `5432`
- NATS leaf upstream `7422`
- MinIO `9000`

6. Register or select the Jetson model record:

- name: `YOLO12n COCO Edge`
- path: `/models/yolo12n.onnx`
- format: `onnx`
- same SHA and size as the iMac `yolo12n.onnx`

7. Edit camera 2:

- processing mode: `edge`
- primary model: `YOLO12n COCO Edge`
- keep active classes and browser delivery profile consistent with Phase A
- assign the Jetson node if the UI exposes assignment; otherwise use `ARGUS_EDGE_CAMERA_ID`

8. Start the Jetson edge stack:

```bash
cd "$HOME/vision"
export ARGUS_API_BASE_URL="http://$IMAC_IP:8000"
export ARGUS_API_BEARER_TOKEN="$JETSON_TOKEN"
export ARGUS_DB_URL="postgresql+asyncpg://argus:argus@$IMAC_IP:5432/argus"
export ARGUS_MINIO_ENDPOINT="$IMAC_IP:9000"
export ARGUS_MINIO_ACCESS_KEY="argus"
export ARGUS_MINIO_SECRET_KEY="argus-dev-secret"
export ARGUS_EDGE_CAMERA_ID="$CAMERA_TWO_ID"
docker compose -f infra/docker-compose.edge.yml up -d --build
docker compose -f infra/docker-compose.edge.yml logs -f inference-worker
```

9. Validate split behavior:

- Live shows camera 1 and camera 2
- History / Patterns receives detections from camera 2 after Jetson worker runs
- Evidence Desk still renders and review state works if incidents exist
- Operations shows edge intent and runtime truth honestly
- worker logs show no `401`, `403`, missing model path, or crash loop

## Important Product Truth

Operations runtime state must remain honest:

- do not invent `running` when per-worker heartbeat truth is unavailable
- `not_reported`, `unknown`, `stale`, or `offline` are valid states when that is the real runtime evidence

The iMac + Jetson flow is a lab/pilot validation path. Long-term production is still expected to be a Linux `amd64` master with supervised central workers plus Jetson edge workers.

If Phase B finds bugs:

- create a fresh `codex/...` branch from `main`
- reproduce the issue narrowly
- fix it with tests where feasible
- keep manual lab validation evidence in the handoff/docs

## Suggested First Prompt For The Next Chat

Paste this into the next chat:

```text
We are now on main at d5a593e after merging codex/source-aware-delivery-calibration-fixes. Phase A iMac-only validation and make verify-all are green. Read docs/superpowers/status/2026-04-30-main-merge-phase-b-handoff.md and docs/imac-master-orin-lab-test-guide.md. I will test manually on the real iMac and Jetson; support me through Phase B iMac master + Jetson Orin edge validation. Do not re-plan completed work. Keep Operations runtime truth honest and debug systematically if validation finds a bug.
```
