# Dev Stack Stability Fixes Design

Date: 2026-06-13
Branch: `codex/sceneops-pack-registry`

## Goal

Remove three recurring dev-experience papercuts that show up across
handoffs and `CLAUDE.md` status notes:

1. `uvicorn --reload` inside the backend container regularly stalls in
   `Waiting for background tasks to complete. (CTRL+C to force quit)`
   after `WatchFiles detected changes`, blocking `/healthz` and forcing a
   manual `docker compose restart backend`.
2. The default `make dev-up` brings up the full observability stack
   (`otel-collector`, `prometheus`, `alertmanager`, `loki`, `tempo`,
   `grafana`) which routinely exits with 137/1 on lab machines under
   memory pressure (documented in `CLAUDE.md`). The exited containers
   then produce noisy "service not reachable" errors in the backend log
   that distract from real bugs.
3. `make verify-all` is the only documented validation flow and is
   intentionally heavy (Playwright, Helm render, full stack health).
   There is no fast confidence check between full runs.

This spec ships the three smallest fixes that do not touch production
artifacts or the Helm chart.

## Non-Goals

- No production compose changes. `infra/install/compose/compose.master.yml`
  and `infra/install/compose/compose.supervisor.yml` are untouched.
- No Helm chart changes.
- No MediaMTX `/replace`-skip work (owned by the tracker-continuity spec).
- No changes to `make verify-all` itself; the new `verify-stack-lite`
  target is additive.

## Architecture Decision

The dev compose file remains the single source of truth for the dev
stack, but stops being responsible for hot-reload. Hot-reload moves to an
explicit, fast operator action (`make dev-reload`) that does not depend
on `WatchFiles` inside the container. The observability stack moves
behind a Compose profile so the default lab invocation is light.

```text
make dev-up           -> core services only
                        (postgres, redis, nats, minio, keycloak,
                         mediamtx, backend, frontend)

make dev-up-obs       -> core + observability profile
                        (adds otel-collector, prometheus,
                         alertmanager, loki, tempo, grafana)

make dev-reload       -> backend container picks up code changes
                        (sentinel-touch + SIGHUP, no WatchFiles)

make verify-stack-lite-> fast confidence: mypy + ruff + pytest -q
                        + frontend lint + frontend build
                        (no Playwright, no Helm render, no
                         observability)
```

The production installer path (`bin/vezor install master/edge`) is
unaffected; it does not use `infra/docker-compose.dev.yml`.

## Changes

### Backend `--reload` removal

`infra/docker-compose.dev.yml` backend service `command` drops
`--reload`. The container starts uvicorn with the same arguments as the
production entrypoint, except:

- bind-mount for `backend/src` stays in place (developer code edits land
  in the container)
- the new `make dev-reload` target is the documented hot-reload path

`make dev-reload`:

```make
dev-reload:
	@touch backend/.reload-sentinel
	@docker compose -f infra/docker-compose.dev.yml kill -s HUP backend || true
	@docker compose -f infra/docker-compose.dev.yml restart backend
```

The actual hot-reload mechanism is a quick container restart, not signal
handling, because uvicorn's SIGHUP behaviour outside `--reload` mode is
inconsistent. The sentinel exists for future tooling (a watcher that
calls `dev-reload` on save can use it). The restart takes ~3 seconds and
does not leave the container in the `WatchFiles` shutdown loop.

### Observability behind a Compose profile

`infra/docker-compose.dev.yml`: add `profiles: ["obs"]` to each of:

- `otel-collector`
- `prometheus`
- `alertmanager`
- `loki`
- `tempo`
- `grafana`

The default `docker compose -f infra/docker-compose.dev.yml up -d` brings
up only the un-profiled services. `--profile obs` adds the rest.

The new `Makefile` targets (`dev-up`, `dev-up-obs`, `dev-down`) are
defined in the next section once the backend env-var lever is in place
so both pieces stay consistent.

`dev-down` uses `--profile obs` so that even if the user originally
brought up only the core stack, `dev-down` cleans up any orphan obs
containers from a previous `dev-up-obs` session.

### Backend OTLP exporter is conditional

The backend currently logs OTLP exporter errors when `otel-collector` is
not reachable. This is noise in the default light-stack mode.

`backend/src/argus/core/config.py` reads
`ARGUS_OTEL_EXPORTER_ENABLED` (default `true` in production for the
installer-managed compose files, default `false` in the dev compose
file). When disabled, the OTLP exporter is not registered and no
connection attempts are made.

In `infra/docker-compose.dev.yml`, the backend service environment uses
the standard Compose variable-interpolation form:

```yaml
backend:
  environment:
    ARGUS_OTEL_EXPORTER_ENABLED: "${ARGUS_OTEL_EXPORTER_ENABLED:-false}"
```

The Make targets set the variable in their own shell environment before
calling Compose, so the obs profile and the env flag stay in sync:

```make
dev-up:
	docker compose -f infra/docker-compose.dev.yml up -d

dev-up-obs:
	ARGUS_OTEL_EXPORTER_ENABLED=true \
	  docker compose -f infra/docker-compose.dev.yml --profile obs up -d

dev-down:
	docker compose -f infra/docker-compose.dev.yml --profile obs down
```

A single backend service is kept; no profile-only override service
block is introduced. Compose's `${VAR:-default}` interpolation is the
clean lever for this kind of conditional config.

### `make verify-stack-lite`

New target in the root `Makefile`:

```make
verify-stack-lite:
	$(MAKE) -C backend lint
	$(MAKE) -C backend test
	$(MAKE) -C frontend lint
	$(MAKE) -C frontend test
	$(MAKE) -C frontend build
```

No Playwright, no Helm render, no `make dev-up` smoke. Designed to run
in under 90 seconds on the developer's workstation as a pre-PR check.
`make verify-all` continues to be the heavy gate.

### Documentation

`docs/runbook.md` gains a short subsection ("Dev Stack Profiles")
describing:

- when to use `dev-up` vs `dev-up-obs`
- `dev-reload` as the replacement for the deprecated WatchFiles flow
- `verify-stack-lite` vs `verify-all`

No new top-level docs file.

## Acceptance Criteria

### Required (merge gate)

1. `docker compose -f infra/docker-compose.dev.yml up -d` followed by a
   `curl -fsS http://127.0.0.1:8000/healthz` returns 200 within 30
   seconds on a clean checkout.
2. `docker compose -f infra/docker-compose.dev.yml ps --all` after the
   default `dev-up` shows zero exited containers and zero containers
   from the `obs` profile.
3. `make dev-up-obs` brings up the obs profile services successfully on
   a machine with sufficient RAM; on a constrained machine the failure
   is contained to the obs services and does not affect core service
   health.
4. `make dev-reload` after a backend code edit results in the new code
   being served by uvicorn within 5 seconds, with `/healthz` reachable
   throughout (apart from the ~3 second restart window).
5. `make verify-stack-lite` runs in under 90 seconds on the project's
   reference workstation (M-series MacBook Pro 16 GB) and fails fast on
   lint, type, or test errors.
6. Existing `make verify-all` continues to pass unchanged.

### Recommended evidence (not merge gate)

- Capture a `docker compose ps --all` before/after snapshot on a known
  16 GB lab machine showing zero exited obs containers after the
  default `dev-up`.

## Test Plan

- Unit test: `tests/core/test_config.py` gains a test that
  `ARGUS_OTEL_EXPORTER_ENABLED=false` results in no OTLP exporter being
  registered.
- Manual smoke: `make dev-up && make dev-reload && make dev-down`
  exercises the new targets.
- Manual smoke: `make dev-up-obs && make dev-down` brings up and tears
  down the full stack including obs services.
- Manual smoke: `make verify-stack-lite` succeeds on a clean checkout
  and fails on an intentionally broken file.

## Files Touched

| File | Change |
|---|---|
| `infra/docker-compose.dev.yml` | drop `--reload` on backend; add `profiles: ["obs"]` to six obs services; add `backend-obs` override under `obs` profile; set `ARGUS_OTEL_EXPORTER_ENABLED=false` on default backend env |
| `Makefile` | new `dev-up-obs`, `dev-reload`, `verify-stack-lite` targets; updated `dev-down` |
| `backend/src/argus/core/config.py` | new `ARGUS_OTEL_EXPORTER_ENABLED` setting (default `true`) |
| `backend/src/argus/services/app.py` | conditional OTLP exporter registration based on the new setting |
| `backend/tests/core/test_config.py` | test the new setting |
| `docs/runbook.md` | new "Dev Stack Profiles" subsection |

## Out Of Scope

- Production compose / installer changes.
- Helm chart changes.
- Watcher tooling that calls `dev-reload` on save. The sentinel makes
  this addable later without touching this spec.
- Replacing the backend's `--reload` with a different process supervisor
  inside the container. The restart-on-demand model is intentionally
  simple.

## Open Questions

None. Implementation is mechanical.
