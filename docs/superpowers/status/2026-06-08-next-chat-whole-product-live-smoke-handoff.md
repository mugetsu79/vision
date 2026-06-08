# Whole-Product Live Smoke Next-Chat Handoff

Date: 2026-06-08
Current branch: `codex/sceneops-pack-registry`
Current pushed head: `d84fca55`

## Purpose

The next chat should run a true whole-product smoke on a live stack. This is a
validation pass first. Do not start by implementing unless the live smoke finds
a confirmed blocker that prevents the smoke from continuing.

The required outcome is a high-signal smoke report with exact commands,
screenshots or logs where useful, pass/fail status, and concrete follow-up bugs.
Do not mark the product as smoke-passed unless first-run, auth, scenes/cameras,
worker lifecycle, Link Performance with emulated edge-agent probes, FleetOps,
Deployment/support bundles, and basic docs/deployment posture have all been
exercised on a running stack.

## Read First

Read these before touching the stack:

1. `docs/superpowers/status/2026-06-07-next-chat-core-link-reflector-completion-handoff.md`
2. `docs/superpowers/plans/2026-06-08-warning-cleanup-before-live-validation.md`
3. `docs/core-link-performance-guide.md`
4. `docs/product-installer-and-first-run-guide.md`
5. `docs/operator-deployment-playbook.md`
6. `docs/runbook.md`
7. `README.md`
8. Active FleetOps/Core Link specs and plans:
   - `docs/superpowers/specs/2026-06-05-one-pack-sceneops-engine-pack-boundary-design.md`
   - `docs/superpowers/specs/2026-06-05-maritime-fleetops-runtime-pack-design.md`
   - `docs/superpowers/specs/2026-06-06-fleetops-operator-completion-design.md`
   - `docs/superpowers/specs/2026-06-07-core-link-performance-workspace-design.md`
   - `docs/superpowers/specs/2026-06-07-core-link-edge-agent-design.md`
   - `docs/superpowers/specs/2026-06-07-core-link-reflector-loss-design.md`
   - `docs/superpowers/specs/2026-06-07-core-link-master-target-site-design.md`
   - `docs/superpowers/specs/2026-06-07-core-link-master-reflector-deployment-design.md`
   - `docs/superpowers/plans/2026-06-07-core-link-master-reflector-deployment.md`

Preserve all `CC-*` constraints. Core Link remains domain-neutral. FleetOps may
link into Core Link by site id, but maritime/FleetOps nouns must not leak into
core routes, contracts, services, tests, or generic Core Link copy.

## Current Branch State

The latest pushed commit before this handoff is:

```text
d84fca55 fix: harden live validation blockers
```

That commit fixed the pre-live blockers found during review:

- claimless first-run admin direct-grant tokens now resolve tenant context from
  local user subject before falling back to realm slug.
- claimless unknown users are rejected once local users exist.
- first-run collects first/last name and provisions Keycloak users without
  `VERIFY_PROFILE`.
- first-run creates/repairs the `argus-cli` direct-grant client and tenant
  mappers.
- fresh tenants can repair/create the Vezor Master control-plane site when the
  Link Performance master target routes are called.
- edge-agent UDP sequence samples are not degraded solely because throughput was
  unmeasured.
- support bundles include edge-node service reports and still redact
  token-like diagnostics.
- docs/specs no longer claim master reflector profile changes require restart.

Verification already run after that commit:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest -q
python3 -m uv run ruff check src tests
python3 -m uv run mypy

cd /Users/yann.moren/vision/frontend
npm test -- --run
npm run lint
npm run build

cd /Users/yann.moren/vision
git diff --check
```

Observed results:

- backend pytest: `1084 passed`
- backend Ruff: passed
- backend mypy: passed
- frontend Vitest: `94 passed`, `471 tests passed`
- frontend lint: passed
- frontend build: passed
- diff whitespace check: passed

## Working Tree Warning

Before doing anything:

```bash
cd /Users/yann.moren/vision
git fetch origin codex/sceneops-pack-registry
git status --short --branch
git rev-parse --short HEAD
```

Expected branch/head: `codex/sceneops-pack-registry` at or after `d84fca55`.

This workspace has unrelated untracked local files and folders such as
`.claude/`, `.codex/`, `.playwright-mcp/`, `.superpowers/brainstorm/...`,
`.vite/`, screenshots, strategy drafts, and `taste-skill/`. Do not stage them.
Use explicit paths if a later bugfix is requested. Do not use `git add -A`.

## Destructive Stack Reset

The user explicitly requested that the next chat remove the existing Vezor
Docker stack completely and start the smoke from scratch. Do not reuse the
currently running Vezor stack. This reset is required so first-run, Keycloak
realm provisioning, tenant bootstrap, migrations, seeded control-plane site
repair, and reflector profile behavior are validated from a fresh state.

The reset must stay targeted to Vezor validation stacks. Do not run global
commands such as `docker system prune -a --volumes`, and do not delete unrelated
Docker resources. Do not delete model files under `models/` or
`/var/lib/vezor/models`; model artifacts are validation inputs, not stack state.

Start by inventorying what will be removed:

```bash
cd /Users/yann.moren/vision
docker compose ls
docker ps -a --format 'table {{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'vezor|argus|validation|infra|backend|frontend|keycloak' || true
docker volume ls --format 'table {{.Name}}\t{{.Label "com.docker.compose.project"}}' \
  | grep -E 'vezor|argus|validation|infra' || true
```

Stop any installed product service manager wrapper first, if present:

```bash
sudo launchctl bootout system/com.vezor.master 2>/dev/null || true
sudo systemctl stop vezor-master.service 2>/dev/null || true
```

Bring down the known Compose stacks with volumes:

```bash
docker compose -f infra/docker-compose.dev.yml down -v --remove-orphans || true
docker compose -p vezor-live-validation \
  -f infra/install/compose/compose.master.yml \
  down -v --remove-orphans || true
```

Remove any remaining containers and volumes that still carry the known Vezor
Compose project labels:

```bash
for project in infra vezor-live-validation vezor-master; do
  for container_id in $(docker ps -aq --filter "label=com.docker.compose.project=$project"); do
    docker rm -f "$container_id"
  done
  for volume_name in $(docker volume ls -q --filter "label=com.docker.compose.project=$project"); do
    docker volume rm "$volume_name"
  done
done
```

Remove name-matched leftover Vezor validation containers. Review the printed
list first; the command is intentionally scoped to Vezor naming patterns:

```bash
docker ps -a --format '{{.ID}} {{.Names}}' \
  | grep -E 'vezor|argus|validation' || true

for container_id in $(
  docker ps -a --format '{{.ID}} {{.Names}}' \
  | awk '/vezor|argus|validation/ {print $1}'
); do
  docker rm -f "$container_id"
done
```

Remove name-matched leftover Vezor validation volumes:

```bash
docker volume ls --format '{{.Name}}' \
  | grep -E 'vezor|argus|validation|^infra_' || true

for volume_name in $(
  docker volume ls --format '{{.Name}}' \
  | awk '/vezor|argus|validation|^infra_/ {print $1}'
); do
  docker volume rm "$volume_name"
done
```

Verify the reset before starting the fresh stack:

```bash
docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' \
  | grep -E 'vezor|argus|validation|infra|backend|frontend|keycloak' || true
docker volume ls --format 'table {{.Name}}\t{{.Label "com.docker.compose.project"}}' \
  | grep -E 'vezor|argus|validation|infra' || true
```

Expected after reset: no Vezor validation containers remain. If Vezor-named
volumes remain, explain why they are intentionally preserved; otherwise remove
them before first-run.

## Stack Choice

Use a fresh product-mode stack for the smoke. A reused dev stack is not
acceptable for this run because the user asked for a full reset and first-run
proof from scratch.

Preferred product-mode validation:

1. macOS master installer path from `docs/product-installer-and-first-run-guide.md`, or
2. Linux master installer path from the same guide, or
3. an isolated Compose project that uses `infra/install/compose/compose.master.yml`
   with fresh Postgres/Keycloak volumes and mapped ports.

The old isolated live-validation stack from the previous chat may have used
project name `vezor-live-validation` and alternate host ports around:

```text
frontend 3100
backend 8100
Keycloak 18080
reflector UDP 18622
```

If that stack existed, the destructive reset above should remove it before the
new smoke starts. Do not reuse it.

```bash
docker compose -p vezor-live-validation ps
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}' | grep -E 'vezor|argus|validation|frontend|backend|keycloak' || true
```

Development-stack fallback after the destructive reset:

```bash
cd /Users/yann.moren/vision
make dev-up
until docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv --version >/dev/null 2>&1; do
  echo "waiting for backend Python environment..."
  sleep 3
done
docker compose -f infra/docker-compose.dev.yml exec backend \
  python -m uv run alembic upgrade head
until curl -fsS http://127.0.0.1:8000/healthz >/dev/null; do
  echo "waiting for backend health..."
  sleep 3
done
corepack pnpm --dir frontend generate:api
```

Dev-stack URLs:

- frontend: `http://127.0.0.1:3000`
- backend: `http://127.0.0.1:8000`
- Keycloak: `http://127.0.0.1:8080`
- dev login: `admin-dev` / `argus-admin-pass`

## Product-Mode Preflight

For product-mode first-run, follow the installer guide. The minimum proof points
are:

```bash
curl -fsS http://127.0.0.1:8000/healthz
docker ps --filter name=vezor-master
```

If using the installed master, `docker ps --filter name=vezor-master` must show
installed product containers. If it only shows `infra-*` containers, the smoke
is pointed at the dev stack.

Generate the first-run bootstrap token only from the master host:

```bash
/opt/vezor/current/bin/vezorctl bootstrap-master \
  --api-url http://127.0.0.1:8000 \
  --rotate-local-token \
  --json
```

Complete `/first-run` with:

- tenant name
- first admin email
- first admin password
- first admin first name
- first admin last name
- master node name
- optional central supervisor id, for example `100`

After first-run, create a fresh admin token for API probes:

```bash
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export KC_URL="http://127.0.0.1:8080"
export KC_REALM="argus-dev"

printf "Vezor admin email: "
read VEZOR_ADMIN_USERNAME

printf "Vezor admin password: "
stty -echo
read VEZOR_ADMIN_PASSWORD
stty echo
echo

export VEZOR_ADMIN_ACCESS_TOKEN="$(
  curl -fsS -X POST "$KC_URL/realms/$KC_REALM/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=password" \
    --data-urlencode "client_id=argus-cli" \
    --data-urlencode "username=$VEZOR_ADMIN_USERNAME" \
    --data-urlencode "password=$VEZOR_ADMIN_PASSWORD" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)"
```

Confirm the direct-grant token contains tenant context:

```bash
python3 - <<'PY'
import base64, json, os
token = os.environ["VEZOR_ADMIN_ACCESS_TOKEN"]
payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
claims = json.loads(base64.urlsafe_b64decode(payload))
print(json.dumps({k: claims.get(k) for k in ("sub", "email", "tenant", "tenant_id")}, indent=2))
assert claims.get("tenant") or claims.get("tenant_id")
PY
```

Use this helper for API checks:

```bash
api() {
  curl -fsS \
    -H "Authorization: Bearer $VEZOR_ADMIN_ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    "$@"
}
```

## Required Smoke Matrix

Record each section as `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. Include exact
commands, response snippets, screenshots, and log excerpts as evidence.

### 1. Auth, First-Run, Tenant Boundary

Required checks:

- `/first-run` appears on a fresh stack before completion.
- first-run completion accepts first/last admin name and does not leave the
  admin stuck in Keycloak `VERIFY_PROFILE`.
- signed-in admin can load `/deployment`, `/settings`, `/links`, `/cameras`,
  `/live`, `/history`, `/incidents`, `/fleetops`, `/fleetops/vessels`,
  `/fleetops/evidence`, `/fleetops/billing`, and `/fleetops/support`.
- direct-grant `argus-cli` token can call tenant-scoped APIs.
- a browser token and CLI token resolve the same tenant.

API probes:

```bash
api "$ARGUS_API_BASE_URL/api/v1/deployment/bootstrap/status" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/sites" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/link/reflectors/master" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/link/sites/summary" | python3 -m json.tool
```

Expected:

- bootstrap status reports `first_run_required: false`.
- `/api/v1/sites` includes a normal edge site after one is created and a
  `site_kind: "control_plane"` Vezor Master site after Link Performance master
  target APIs are touched.
- `/api/v1/link/reflectors/master` does not 404 on a fresh tenant.

Security boundary check:

- Use the first-run tenant admin, not Keycloak master admin.
- Do not paste tokens into the report.
- If any claimless unknown token can access tenant data after local users
  exist, record as P0.

### 2. Model Availability

Model-dependent camera and worker smoke cannot pass unless a real model file is
available.

Current repository `models/` may only contain `.gitkeep`. If so, either export
`yolo26n.onnx` from official Ultralytics weights per
`docs/product-installer-and-first-run-guide.md`, or mark model-dependent flows
as blocked.

Installed product path:

- host file: `/var/lib/vezor/models/yolo26n.onnx`
- backend/container path: `/models/yolo26n.onnx`

Register:

```bash
docker exec \
  -e ARGUS_API_BASE_URL \
  -e VEZOR_ADMIN_ACCESS_TOKEN \
  vezor-master-backend-1 sh -lc '
  /app/.venv/bin/python -m argus.scripts.register_model_preset \
    --catalog-id yolo26n-coco-onnx \
    --artifact-path /models/yolo26n.onnx \
    --api-base-url "$ARGUS_API_BASE_URL" \
    --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN"
'
```

Dev-stack path:

```bash
cd /Users/yann.moren/vision/backend
export ARGUS_API_BASE_URL="http://127.0.0.1:8000"
export ARGUS_API_BEARER_TOKEN="$VEZOR_ADMIN_ACCESS_TOKEN"
python3 -m uv run python scripts/register_model_preset.py \
  --catalog-id yolo26n-coco-onnx \
  --artifact-path /Users/yann.moren/vision/models/yolo26n.onnx \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$ARGUS_API_BEARER_TOKEN"
```

Confirm:

```bash
api "$ARGUS_API_BASE_URL/api/v1/models" | python3 -m json.tool
```

### 3. Sites, Scenes, Dummy Cameras

Validate both UI and API paths if practical.

UI path:

- open `/deployment` and confirm Sites workbench.
- create at least one edge site, for example `Smoke Edge Site`.
- open `/cameras`.
- click Add scene.
- create one central dummy RTSP scene and, if an edge node exists, one edge
  scene.
- use a reachable RTSP source if available. If not available, use a clearly
  dummy URL such as `rtsp://camera.local/live` only to validate form/API
  persistence, and mark live video/worker inference as blocked by missing
  source.

API seed fallback:

```bash
export SITE_ID="$(
  api -X POST "$ARGUS_API_BASE_URL/api/v1/sites" \
    -d '{"name":"Smoke Edge Site","description":"Whole-product smoke edge site","tz":"UTC"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

export MODEL_ID="$(
  api "$ARGUS_API_BASE_URL/api/v1/models" \
  | python3 -c 'import json,sys
items=json.load(sys.stdin)
print(items[0]["id"])
'
)"

export CAMERA_ID="$(
  api -X POST "$ARGUS_API_BASE_URL/api/v1/cameras" \
    -d "{
      \"site_id\":\"$SITE_ID\",
      \"name\":\"Smoke Dummy Scene\",
      \"rtsp_url\":\"rtsp://camera.local/live\",
      \"processing_mode\":\"central\",
      \"primary_model_id\":\"$MODEL_ID\",
      \"tracker_type\":\"bytetrack\",
      \"active_classes\":[\"person\"],
      \"frame_skip\":1,
      \"fps_cap\":10
    }" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

api "$ARGUS_API_BASE_URL/api/v1/cameras/$CAMERA_ID" | python3 -m json.tool
```

Expected:

- `/cameras` shows the created scene.
- `/live` shows scene inventory and sensible empty/degraded state if no stream
  is reachable.
- `/history` can filter/search the scene without crashing.
- camera API masks the RTSP URL in responses.

### 4. Worker Lifecycle And Runtime Truth

Smoke both product behavior and fallback reality.

Installed/product expectation:

- `/settings` Operations shows worker lifecycle controls.
- Start/Restart/Stop should create desired state or lifecycle requests owned by
  supervisor flow.
- It should not require operators to paste bearer tokens for normal installed
  operation.

Dev fallback:

- The dev stack starts platform services, not per-camera workers.
- Use the copyable Operations worker command only as a development bridge.

API checks:

```bash
api "$ARGUS_API_BASE_URL/api/v1/operations/fleet" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/cameras/$CAMERA_ID/worker-config" | python3 -m json.tool
```

If no real RTSP source/model is available, prove the worker cannot honestly run
and record `BLOCKED: missing reachable RTSP/model`, not a product pass.

If a reachable stream exists, run the worker/supervisor path and capture:

- runtime report appears in `/api/v1/operations/fleet`.
- Live page shows worker status and heartbeat.
- delivery diagnostics show stream URLs/profiles.
- Restart creates a fresh runtime report.
- Stop/Drain updates state.

Manual runtime-report fallback for UI signal validation only:

```bash
api -X POST "$ARGUS_API_BASE_URL/api/v1/operations/runtime-reports" \
  -d "{
    \"camera_id\":\"$CAMERA_ID\",
    \"heartbeat_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"runtime_state\":\"running\",
    \"restart_count\":0
  }" | python3 -m json.tool
```

Do not count this as proof that the worker can run. It only proves the UI/API
render runtime truth when reports exist.

### 5. Core Link Performance

Required UI flows:

- open `/links`.
- confirm only edge sites are configurable.
- confirm the Vezor Master site appears as target-only, not as a source for
  local link paths.
- create a link path on the edge site.
- configure a monitoring target using the Vezor Master preset.
- check empty states, error states, and operator copy.

API flow:

```bash
api "$ARGUS_API_BASE_URL/api/v1/link/sites/summary" | python3 -m json.tool

export CONNECTION_ID="$(
  api -X POST "$ARGUS_API_BASE_URL/api/v1/link/sites/$SITE_ID/connections" \
    -d '{
      "label":"Smoke WAN",
      "transport_kind":"ethernet",
      "provider":"Smoke Provider",
      "status":"online",
      "priority_rank":1,
      "availability_scope":"always",
      "metered":false,
      "expected_downlink_mbps":100,
      "expected_uplink_mbps":20,
      "expected_latency_ms":30
    }' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'
)"

export MASTER_HTTPS_TARGET_RESPONSE="$(
  api -X POST "$ARGUS_API_BASE_URL/api/v1/link/sites/$SITE_ID/control-targets/master" \
    -d "{
      \"mode\":\"https_only\",
      \"connection_id\":\"$CONNECTION_ID\",
      \"connection_label\":\"Vezor Master smoke target\",
      \"address\":\"$ARGUS_API_BASE_URL/healthz\",
      \"interval_seconds\":300
    }"
)"
printf '%s\n' "$MASTER_HTTPS_TARGET_RESPONSE" | python3 -m json.tool
```

Expected: the connection metadata includes a `monitoring_targets` entry with
`id: "vezor-master-https"`, `purpose: "vezor_control"`, and
`source_type: "edge_agent"`.

### 6. Master Reflector And Emulated Edge-Agent Probes

Reflector precondition:

- The backend container/host must expose the UDP reflector port to the emulated
  edge agent. Compose/installer/Helm defaults use container port `8622`.
- Startup binding uses `ARGUS_LINK_REFLECTOR_ENABLED=true` and
  `ARGUS_LINK_REFLECTOR_SECRET`; runtime profile enable/disable/key changes
  reconcile through the running FastAPI app after startup.
- Set `public_address` to an address the emulated edge agent can reach.

If using an alternate isolated stack, map UDP host port clearly. Previous live
validation used host UDP `18622` to container `8622`.

Enable/inspect profile:

```bash
api "$ARGUS_API_BASE_URL/api/v1/link/reflectors/master" | python3 -m json.tool
api -X POST "$ARGUS_API_BASE_URL/api/v1/link/reflectors/master/enable" \
  -d '{
    "public_address":"127.0.0.1",
    "udp_port":8622,
    "rate_limit_pps_per_source":100
  }' | python3 -m json.tool
```

The public API intentionally does not return the reflector secret. For this
validation pass only, extract the generated profile secret from the local
backend environment. Do not paste the secret into the final report.

Installed backend container:

```bash
export REFLECTOR_SECRET="$(
  docker exec vezor-master-backend-1 sh -lc '/app/.venv/bin/python - <<'"'"'PY'"'"'
import asyncio
from sqlalchemy import select

from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.link.reflector_profiles import decrypt_reflector_secret
from argus.link.tables import LinkReflectorProfile

async def main():
    settings = Settings()
    db = DatabaseManager(settings)
    try:
        async with db.session_factory() as session:
            row = (await session.execute(
                select(LinkReflectorProfile)
                .where(LinkReflectorProfile.profile_kind == "master")
                .order_by(LinkReflectorProfile.updated_at.desc())
                .limit(1)
            )).scalar_one()
            if row.encrypted_secret is None:
                raise SystemExit("reflector profile has no secret")
            print(decrypt_reflector_secret(row.encrypted_secret, settings=settings))
    finally:
        await db.dispose()

asyncio.run(main())
PY'
)"
```

Dev/local backend:

```bash
cd /Users/yann.moren/vision/backend
export REFLECTOR_SECRET="$(
  python3 -m uv run python - <<'PY'
import asyncio
from sqlalchemy import select

from argus.core.config import Settings
from argus.core.db import DatabaseManager
from argus.link.reflector_profiles import decrypt_reflector_secret
from argus.link.tables import LinkReflectorProfile

async def main():
    settings = Settings(_env_file=None)
    db = DatabaseManager(settings)
    try:
        async with db.session_factory() as session:
            row = (await session.execute(
                select(LinkReflectorProfile)
                .where(LinkReflectorProfile.profile_kind == "master")
                .order_by(LinkReflectorProfile.updated_at.desc())
                .limit(1)
            )).scalar_one()
            if row.encrypted_secret is None:
                raise SystemExit("reflector profile has no secret")
            print(decrypt_reflector_secret(row.encrypted_secret, settings=settings))
    finally:
        await db.dispose()

asyncio.run(main())
PY
)"
```

Create the UDP control target and capture its id/address:

```bash
export MASTER_UDP_TARGET_RESPONSE="$(
  api -X POST "$ARGUS_API_BASE_URL/api/v1/link/sites/$SITE_ID/control-targets/master" \
    -d "{
      \"mode\":\"udp_reflector\",
      \"connection_id\":\"$CONNECTION_ID\",
      \"connection_label\":\"Vezor Master UDP smoke target\",
      \"address\":\"127.0.0.1\",
      \"interval_seconds\":300,
      \"packet_count\":10,
      \"packet_spacing_ms\":100,
      \"loss_timeout_ms\":1000
    }"
)"
printf '%s\n' "$MASTER_UDP_TARGET_RESPONSE" | python3 -m json.tool

export TARGET_ID="$(
  printf '%s\n' "$MASTER_UDP_TARGET_RESPONSE" \
  | python3 -c 'import json,sys
connection=json.load(sys.stdin)
targets=connection.get("metadata", {}).get("monitoring_targets", [])
print(next(target["id"] for target in targets if target.get("probe_type") == "udp"))
'
)"
export TARGET_ADDRESS="$(
  printf '%s\n' "$MASTER_UDP_TARGET_RESPONSE" \
  | python3 -c 'import json,sys
connection=json.load(sys.stdin)
targets=connection.get("metadata", {}).get("monitoring_targets", [])
print(next(target["address"] for target in targets if target.get("probe_type") == "udp"))
'
)"
export REFLECTOR_KEY_ID="$(
  api "$ARGUS_API_BASE_URL/api/v1/link/reflectors/master" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["key_id"])'
)"
```

Run emulated edge-agent once. `--target` is required by the CLI even for UDP
sequence mode; use the UDP target address:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run python -m argus.link.edge_agent \
  --api-base-url "$ARGUS_API_BASE_URL" \
  --bearer-token "$VEZOR_ADMIN_ACCESS_TOKEN" \
  --site-id "$SITE_ID" \
  --target-id "$TARGET_ID" \
  --target "$TARGET_ADDRESS" \
  --method udp_sequence \
  --reflector 127.0.0.1 \
  --reflector-port 8622 \
  --reflector-key-id "$REFLECTOR_KEY_ID" \
  --reflector-secret "$REFLECTOR_SECRET" \
  --agent-id smoke-edge-agent \
  --agent-label "Smoke Edge Agent" \
  --packet-count 10 \
  --timeout-seconds 5 \
  --once
```

If the reflector is exposed through host port `18622`, use
`--reflector-port 18622`.

If the validation agent cannot extract the secret from the local stack, mark
edge-agent-to-master-reflector as `BLOCKED: reflector secret distribution is not
packaged`, and still validate the API/UI reflector profile status.

Confirm sample ingestion and health:

```bash
api "$ARGUS_API_BASE_URL/api/v1/link/sites/$SITE_ID/probes" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/link/sites/$SITE_ID/status" | python3 -m json.tool
```

Expected:

- latest probe has `source_type: "edge_agent"`.
- UDP metadata includes packet counts/loss/RTT fields.
- healthy UDP sequence probe is not degraded only because throughput is `0`.
- Link Performance UI shows the sample under the correct edge site and master
  target.

Also run one negative check:

- wrong reflector secret should fail or produce no healthy sample.
- record the exact error/log.

### 7. FleetOps Product Flow

Required pages:

- `/fleetops`
- `/fleetops/onboarding`
- `/fleetops/vessels`
- `/fleetops/vessels/:id`
- `/fleetops/evidence`
- `/fleetops/billing`
- `/fleetops/support`

API probes:

```bash
api "$ARGUS_API_BASE_URL/api/v1/maritime/runtime" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/maritime/vessels" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/maritime/evidence-context" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/maritime/billing/usage" | python3 -m json.tool
api "$ARGUS_API_BASE_URL/api/v1/maritime/support/checklist" | python3 -m json.tool
```

Create a smoke vessel through the UI or API:

```bash
api -X POST "$ARGUS_API_BASE_URL/api/v1/maritime/vessels" \
  -d '{
    "name":"MV Smoke",
    "imo_number":"1234567",
    "mmsi":"123456789",
    "create_site":{
      "name":"Smoke Vessel Site",
      "description":"Whole-product smoke vessel site",
      "tz":"UTC"
    },
    "flag_state":"NO",
    "vessel_type":"general_cargo"
  }' | python3 -m json.tool
```

The point is to prove FleetOps can create and load a vessel/site scope, then
deep-link or correlate to Core Link without polluting Core Link with FleetOps
nouns.

Expected:

- FleetOps overview loads runtime status, vessels, evidence, billing, and
  support panels.
- vessel detail loads telemetry/link/evidence/billing/support sections.
- FleetOps support link to Link Performance targets the vessel/site context.
- Core Link copy remains generic.

### 8. Deployment, Support Bundles, Secrets

Required UI:

- `/deployment` loads.
- master node appears.
- edge node appears if paired/registered.
- service reports show freshness/status.
- support bundle can be opened/exported.

API probes:

```bash
api "$ARGUS_API_BASE_URL/api/v1/deployment/nodes" | python3 -m json.tool
```

For each node id:

```bash
api "$ARGUS_API_BASE_URL/api/v1/deployment/nodes" \
| python3 -c 'import json,sys; print("\n".join(node["id"] for node in json.load(sys.stdin)))' \
| while read -r NODE_ID; do
    echo "support bundle for $NODE_ID"
    api "$ARGUS_API_BASE_URL/api/v1/deployment/nodes/$NODE_ID/support-bundle" \
      | python3 -m json.tool
  done
```

Expected:

- edge-node support bundle includes edge service reports when they exist.
- token-like diagnostics are redacted.
- no raw bootstrap token, bearer token, reflector secret, node credential, or
  Keycloak secret appears in UI/API output.

### 9. Evidence, History, Live

Minimum UI pass:

- `/live` shows created scenes and usable empty/degraded states.
- focused scene and scene browser interactions work.
- `/history` can search/filter the created scene without crashing.
- `/incidents` loads queue/evidence desk states.
- If a real worker/source is available, generate or observe at least one
  runtime/evidence signal and confirm it appears in Live/History/Evidence.

If only dummy camera data exists, explicitly record:

```text
Live video and evidence generation blocked by missing reachable RTSP source or model.
UI/API inventory states validated only.
```

### 10. Deployment Artifacts

Run these if practical after live smoke:

```bash
cd /Users/yann.moren/vision
helm template argus infra/helm/argus >/tmp/vezor-helm-master.yaml
helm template argus infra/helm/argus -f infra/helm/argus/values-edge.yaml >/tmp/vezor-helm-edge.yaml
docker compose -f infra/install/compose/compose.master.yml config >/tmp/vezor-compose-master.yaml
```

Check:

- reflector UDP port/env/secrets render correctly.
- frontend/backend/OIDC URLs match the actual smoke stack.
- no docs tell the operator to restart the backend for reflector profile
  enable/disable/key rotation.

## Browser Automation Guidance

Use Playwright or the Browser plugin for the UI path. Capture screenshots for
each major page:

- first-run form
- signed-in shell
- Deployment
- Scenes/Cameras
- Live
- Operations/Settings
- Link Performance
- FleetOps overview
- FleetOps vessel detail
- Evidence/Incidents

For each page, verify:

- loading state resolves.
- empty state is understandable.
- form validation is clear.
- error state is visible when an API call is blocked/fails.
- text does not overlap at desktop and mobile widths.
- operator copy is product-accurate.

## When To Stop And Fix

Stop live validation and implement a bugfix only when a confirmed blocker
prevents continuing the smoke. Examples:

- first-run cannot complete.
- signed-in admin cannot get tenant-scoped API access.
- master control-plane site still 404s in Link Performance.
- scene creation fails with valid model/site payload.
- worker config endpoint crashes for a saved scene.
- edge-agent sample ingestion crashes or records wrong tenant/site.
- support bundle leaks credentials/secrets.

For any fix:

1. write a failing regression test first.
2. implement the minimal fix.
3. run focused tests, then relevant full checks.
4. update docs if behavior changes.
5. commit and push only when explicitly asked by the user.

## Final Smoke Report Template

Use this shape in the next chat final report:

```markdown
# Whole-Product Live Smoke Report

Branch/head:
Stack type:
URLs:
Fresh first-run verified: yes/no
Model file used:
RTSP/source used:
Edge-agent mode:

## Summary

## Pass/Fail Matrix

| Area | Status | Evidence |
|---|---|---|
| First-run/auth/tenant | | |
| Deployment/support bundle | | |
| Model registration | | |
| Scenes/cameras | | |
| Worker lifecycle | | |
| Live/history/evidence | | |
| Core Link paths/targets | | |
| Master reflector | | |
| Emulated edge-agent probes | | |
| FleetOps | | |
| Helm/Compose/deployment posture | | |
| Docs consistency | | |

## Confirmed Bugs

## Product Gaps

## UX Clarity Issues

## Test Gaps

## Deployment/Ops Gaps

## Security/Tenant Risks

## Documentation Mismatches

## Commands Run

## Screenshots/Logs Captured

## Recommended Next Steps
```

Do not collapse blocked live dependencies into success language. If model files,
RTSP source, fresh first-run stack, reflector env, or auth data are missing,
state exactly what was missing and the command/setup that would prove it.
