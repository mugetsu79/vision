# Whole-Product Live Smoke Closure Report

Date: 2026-06-09

Branch/head during smoke: `codex/sceneops-pack-registry` at `79112d02`, `0 0` ahead/behind `origin/codex/sceneops-pack-registry` before local closure changes.
Stack type: installed macOS master product stack, targeted destructive reset completed, then rebuilt from local repo images.
URLs: frontend `http://192.168.1.166:3000`, backend `http://192.168.1.166:8000`, Keycloak `http://192.168.1.166:8080`, MediaMTX RTSP `rtsp://192.168.1.166:8554`.
Fresh first-run verified: yes, after preserving `/var/lib/vezor/models/yolo26n.onnx` and `/var/lib/vezor/models/yolo26s.onnx`.
Deterministic smoke run id: `closure-20260609T080923Z`.
RTSP/source used: deterministic fixture plus local placeholder camera source; real Office RTSP credentials were not available in this session.
Edge-agent mode: local diagnostic only; real Jetson/edge origin remained blocked.

## Summary

The fresh installed master stack now proves the central supervisor credential
path from reset through first-run. The installer generated the central
credential, first-run registered the central supervisor as `supervisor_id=100`,
and the running supervisor posted service and hardware reports with 200/201 API
responses and no invalid-credential 401s after first-run.

The remaining deterministic whole-product lanes are now live: a seeded
tracking event produces history class evidence, an incident is reviewable
through public incident APIs, scene/privacy/runtime snapshots and ledger are
retrievable, local evidence artifact content returns 200 with matching SHA256,
and billing usage plus invoice line items are generated through the real
billing service.

Three live blockers were found and fixed narrowly with regression tests:

- Central supervisor install fallback wrote `central-master-1` instead of
  backend supervisor id `100`.
- Async billing invoice generation inserted line items before flushing the
  invoice row, causing an FK violation in Postgres.
- The deterministic fixture wrote a non-public `recording_policy.mode`, causing
  `/api/v1/incidents` to 500 during response validation.

Master-side Core Link reflector secret distribution now passes: the normal
profile API redacts raw secret material, the scoped edge-agent config endpoint
returns a private config to an authorized caller, and a local diagnostic UDP
edge-agent probe posted a 5/5 successful sample. Real Jetson-origin supervisor
sync, TensorRT engine build, Office RTSP validation, and real edge-origin UDP
probe remain BLOCKED because the Jetson host refused SSH/API access and no RTSP
credentials were available.

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| Targeted destructive reset | PASS | Removed only Vezor containers/volumes/config/state; no global Docker prune; `/var/lib/vezor/models/yolo26n.onnx` and `yolo26s.onnx` preserved. |
| Fresh first-run/auth/tenant | PASS | First-run completed for tenant `vezor-smoke-closure`; admin token had tenant id `90bcaedf-9053-4efe-b2ef-24b486454ab4` and admin role. |
| Central supervisor credential binding | PASS | `/etc/vezor/supervisor.json` has `supervisor_id=100`; `/etc/vezor/secrets/central_supervisor_credential` and `/var/lib/vezor/credentials/supervisor.credential` SHA256 both `bde58f763f076fe10a2a64075fa8d48de9ff5bef529e3d49026876abae21c37b`; supervisor logs show model/operations polls 200 and service/hardware reports 201. |
| YOLO26 bundled model files/catalog | PASS | `/api/v1/model-catalog` shows `yolo26n-coco-onnx` and `yolo26s-coco-onnx` registered with `artifact_exists=true`; `/api/v1/models` lists `/models/yolo26n.onnx` size `9941944` and `/models/yolo26s.onnx` size `38291117`. |
| Deterministic detection/history fixture | PASS | Fixture seeded run `closure-20260609T080923Z`; `/api/v1/history` returned one `person` bucket with `event_count=1`; `/api/v1/history/classes` returned `person` with `event_count=1`. |
| Incident/evidence APIs | PASS | `/api/v1/incidents`, scene contract, privacy manifest, runtime passport, ledger, and artifact content all returned 200; incident `recording_policy.mode=event_clip`; artifact SHA256 `05ac3fee7a64a67dbb1d93ab4862b9696daacfd099aa213efd426fb62785b81a` matched fixture output. |
| Billing usage/invoice | PASS | `/api/v1/billing/usage` contains smoke usage for `evidence_pack_export` and `managed_edge_node`; invoice `3c71941c-f350-4893-b982-8c2eb23259c4` has line items `$5.00` and `$25.00`. |
| Master reflector profile redaction | PASS | `GET /api/v1/link/reflectors/master` returned `enabled=true`, `secret_state=present`, and no raw secret field. |
| Scoped reflector config distribution | PASS | `GET /api/v1/link/sites/{site_id}/control-targets/master/edge-agent-config` returned 200 for the smoke edge site; raw response stored only in `/tmp` mode `0600`; report redacts `reflector_secret`. |
| Local diagnostic UDP edge-agent probe | PASS | Local edge-agent used scoped config, posted probe `3cf261ad-4dae-47b1-bbae-d7932223676c`, `reachable=true`, `packet_loss_percent=0.0`, `packets_received=5/5`. This is diagnostic only, not the real Jetson acceptance lane. |
| Real Jetson supervisor/API sync and inventory | BLOCKED | `192.168.1.165` ping ok, but TCP `22`, `8000`, and `9997` refused; SSH exited 255; no real Jetson API/supervisor inventory could be collected. |
| Real Office RTSP smoke | BLOCKED | Jetson/camera host TCP `8554` is open, but no real RTSP credentials were available in env; deterministic fixture used a placeholder local RTSP source. |
| TensorRT engine build on Jetson | BLOCKED | TensorRT builder implementation and tests pass, but Jetson SSH/API access was refused, so no `trtexec` availability check or real engine build could run on Jetson. |
| Real UDP edge-agent probe from Jetson | BLOCKED | Master reflector and local diagnostic passed, but real edge-origin probe could not run because Jetson SSH/API access was refused. |
| Helm/k3s deployment posture | NOT RUN | This closure focused on the installed macOS master stack and compose installer path. |

## Confirmed Bugs Fixed

- `installer/macos/install-master.sh` and `installer/linux/install-master.sh`:
  default central supervisor id now falls back to `100`, matching the first-run
  central deployment node.
- `backend/src/argus/billing/service.py`: async invoice generation now flushes
  `InvoiceRun` before inserting `InvoiceLineItem` rows.
- `backend/src/argus/scripts/seed_whole_product_smoke_fixture.py`: fixture
  uses `/var/lib/vezor/evidence` as the artifact root and writes an API-valid
  `event_clip` recording policy.
- `infra/install/compose/compose.master.yml`: backend container now sets
  `ARGUS_INCIDENT_LOCAL_STORAGE_ROOT=/var/lib/vezor/evidence`, matching the
  mounted evidence volume.

## Product Gaps

- Real Jetson edge supervisor pairing/sync/inventory is still not proven.
- Real Office RTSP playback and 720p/1296p camera validation are still blocked
  without RTSP credentials.
- Jetson TensorRT `.engine` build is still blocked without Jetson access.
- Real Jetson-origin Core Link UDP probe is still blocked without Jetson access.
- Helm/k3s was not exercised in this closure run.

## Security/Tenant Risks

- No raw admin password, bearer token, bootstrap token, RTSP credential, node
  credential, or reflector secret is committed in this report.
- Raw edge registration and scoped reflector config responses were stored only
  under `/tmp/vezor-live-smoke/` with redacted summaries used for evidence.
- Public/profile reflector APIs expose `secret_state` only; the scoped
  edge-agent config endpoint returns secret material only for authorized callers
  and must be treated as credential material.

## Documentation Updates

- `docs/core-link-performance-guide.md` now documents the scoped
  `edge-agent-config` flow and redaction requirements.
- `docs/runbook.md` now tells operators to use `--config-url` for the Vezor
  master reflector and to avoid logging or committing `reflector_secret`.

## Commands Run

Representative commands, with secrets redacted:

```bash
git fetch origin codex/sceneops-pack-registry
git status --short --branch
docker compose -p vezor-master -f infra/install/compose/compose.master.yml down -v --remove-orphans
sudo find /var/lib/vezor -mindepth 1 -maxdepth 1 ! -name models -exec rm -rf {} +
sudo ./bin/vezor install master --public-url http://192.168.1.166:3000
curl -fsS http://127.0.0.1:8000/healthz
docker build -f /opt/vezor/current/backend/Dockerfile -t vezor/backend:portable-demo /opt/vezor/current
docker compose --env-file /etc/vezor/master.env -p vezor-master -f /opt/vezor/current/infra/install/compose/compose.master.yml up -d backend vezor-supervisor
docker exec vezor-master-backend-1 /app/.venv/bin/python -m argus.scripts.seed_whole_product_smoke_fixture --tenant-id [redacted] --site-id [redacted] --camera-id [redacted] --smoke-run-id closure-20260609T080923Z --occurred-at [timestamp] --evidence-root /var/lib/vezor/evidence
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/history/classes
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/incidents
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/billing/usage
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/billing/invoice-runs/[invoice-id]
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/link/reflectors/master
curl -fsS -H "Authorization: Bearer [redacted]" http://127.0.0.1:8000/api/v1/link/sites/[site-id]/control-targets/master/edge-agent-config
python3 -m uv run --project backend python -m argus.link.edge_agent --once
nc -vz -w 3 192.168.1.165 22
nc -vz -w 3 192.168.1.165 8000
nc -vz -w 3 192.168.1.165 8554
nc -vz -w 3 192.168.1.165 9997
```

Verification results captured during implementation:

- focused backend closure suite: `126 passed`
- backend Ruff on touched files: `All checks passed`
- installer artifact tests: `43 passed`
- `make verify-installers`: `86 passed`, shell syntax, executable bits,
  manifest validation, product service secret scan, and master/edge compose
  render passed
- `git diff --check`: passed
- targeted closure-file secret-pattern scan: no hits
- live stack health after final rebuild: backend and supervisor healthy
- live fixture/API validation: all history, incidents, snapshots, ledger,
  artifact content, billing usage, and billing invoice endpoints returned 200

## Recommended Next Steps

1. Restore real Jetson SSH/API access or provide the expected node credential
   path, then rerun supervisor sync, model inventory, TensorRT build, and
   edge-agent UDP probe from the Jetson.
2. Provide local-only RTSP env credentials and rerun the real Office RTSP 720p
   and 1296p lanes.
3. Add a cache-friendly backend Dockerfile layer order so source-only rebuilds
   do not redownload runtime/vision dependencies.
4. Package the edge-agent as an installed service using node credentials instead
   of an admin bearer token for operational probes.
