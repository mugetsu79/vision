# Argus V4 — AI Coder Prompt Blueprint

> Paired with `argus_v4_spec.md`. Feed that spec first, then this file prompt-by-prompt to Codex / Claude Code. **Do not skip the verification gates between prompts.**

---

## Bootstrapping instruction (paste first, once)

> You are going to build `Argus V4`, a **domain-agnostic** hybrid edge/central video analytics platform for 5–50 sites and 25–250 cameras. The product is **not a car counter**. Spec §10 enumerates the capability surface: all 80 COCO classes are built-in, and any custom ONNX detector or secondary attribute classifier (PPE, forklifts, weapons, ANPR, uniforms, wildlife, fire/smoke, abandoned objects, etc.) plugs in with config only — no code changes. A single deployment can run traffic counting, worksite PPE compliance, retail analytics, and perimeter security on different cameras of the same tenant, simultaneously. Counting / measurement modes include instantaneous, cumulative, line-crossing, speed, dwell, density, trajectory, proximity, attribute combinations, loitering, and abandoned-object detection. Reference edge hardware is the **NVIDIA Jetson Orin Nano Super 8 GB** on JetPack 6.2; reference central hardware is an **NVIDIA L4 24 GB** GPU. Before writing any code, read `argus_v4_spec.md` end-to-end and reply with a one-paragraph acknowledgment that lists: (a) the three processing modes, (b) the five supported LLM providers / adapters, (c) the four RBAC roles, (d) the five green gates that must pass between prompts, (e) the two ADRs under `docs/ADR/` and their decisions, and (f) at least four verticals from spec §10.4 that this codebase must support at feature-parity. Do not generate code yet.
>
> **Absolute rule — no V1 reuse:** a `/v1/` directory may exist in the repo as historical reference. You must not read it, port it, copy it, or import from it. If you find yourself tempted to reuse Flask / Flask-SocketIO / eventlet / MobileNet-SSD / SORT / jQuery / Bootstrap / the V1 SQLite schema, stop and rewrite from first principles using V4's stack.
>
> Ground rules for every prompt:
> - Always obey `argus_v4_spec.md`. If a prompt conflicts with the spec, the spec wins and you must ask before diverging.
> - Python 3.12, `uv` for deps, Ruff + mypy --strict, Pydantic v2, SQLAlchemy 2.x async.
> - Frontend: React 19 + Vite 6 + TypeScript strict + Tailwind v4 + shadcn/ui + TanStack Query.
> - All Docker images are multi-arch (`linux/amd64` + `linux/arm64`); the edge image is built against `nvcr.io/nvidia/l4t-jetpack:r36.4.0` and must boot on Jetson Orin Nano Super 8 GB at the 25 W power mode.
> - Inference must be class-agnostic: the YOLO model's class list is read from `models.classes`, never hard-coded. "car" is not special.
> - After every prompt, run the five gates and report the result. If any gate fails, fix it before declaring the prompt done.

---

## Prompt 1 — Monorepo scaffold, tooling, DB schema

> Create the exact folder structure from §6 of the spec. In `backend/`, initialize a `uv` project (`pyproject.toml`) with dependency groups `runtime`, `dev`, `vision`, `llm`. Runtime deps include: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `nats-py`, `httpx`, `structlog`, `opentelemetry-api/sdk/exporter-otlp`, `python-jose[cryptography]`, `passlib[argon2]`, `cryptography`, `prometheus-client`. Vision deps: `opencv-python-headless`, `onnxruntime-gpu` (with a CPU extra), `ultralytics`, `numpy<2`, `Pillow`, `shapely`. LLM deps: `litellm`, `instructor`, `ollama`. Dev deps: `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `testcontainers[postgres,redis,nats]`, `playwright`.
>
> Wire Ruff and mypy strict mode. Add a `Makefile` with targets `fmt`, `lint`, `test`, `models`, `dev-up`, `dev-down`, `migrate`, `revision`.
>
> In `frontend/`, bootstrap Vite + React 19 + TS strict + Tailwind v4 + shadcn/ui. Configure ESLint (flat config) + Prettier. Add `vitest` + `playwright`.
>
> In `backend/src/argus/models/`, implement SQLAlchemy 2.x models for every table in spec §4 — including `models` (primary + secondary), `detection_rules`, `rule_events`, and the per-camera `zones`/`attribute_rules`/`secondary_model_id` columns. Create the first Alembic migration. Make both `tracking_events` and `rule_events` TimescaleDB hypertables (use raw-SQL ops in the migration: `SELECT create_hypertable('tracking_events','ts');` and same for `rule_events`). Create two continuous aggregates, `events_1m` and `events_1h`, from `tracking_events` only, grouped by `camera_id, class_name`.
>
> Add `infra/docker-compose.dev.yml` with: `postgres` (timescale/timescaledb:latest-pg16), `redis:7`, `nats:2.10` (JetStream enabled), `minio`, `keycloak` (dev realm auto-imported from `infra/keycloak/realm-export.json`), `mediamtx` (latest), `otel-collector`, `prometheus`, `loki`, `tempo`, `grafana` (pre-provisioned dashboards). Mount source dirs for hot reload.
>
> **Verification:** all five gates green; `alembic upgrade head` runs against the compose DB; opening `http://localhost:3000` shows a shadcn-styled empty shell.

---

## Prompt 2 — Core infra: config, security, DB layer, event bus, observability

> Implement `core/config.py` using `pydantic-settings` (env + `.env` + secrets dir). Include settings for: DB URL, Redis URL, NATS URL + nkey, MediaMTX URL + creds, Keycloak issuer, RTSP encryption key, LLM provider/model, observability endpoints.
>
> Implement `core/db.py` with an async engine, session factory, and FastAPI dependency `get_session`.
>
> Implement `core/events.py`: a thin NATS JetStream client wrapper with `publish(subject, payload: BaseModel)` and `subscribe(subject, handler)`. Subjects: `evt.tracking.<camera_id>`, `cmd.camera.<camera_id>`, `edge.heartbeat.<node_id>`. Ensure JetStream streams are declared idempotently on startup.
>
> Implement `core/security.py`: OIDC validator for Keycloak (JWKS cached 1h), FastAPI `CurrentUser` dependency, RBAC decorator `require(role)`, support for tenant realms plus a dedicated `platform-admin` realm for `superadmin`, and edge-key middleware that validates scoped API keys for `/api/v1/edge/*`. RTSP URL encryption helpers (AES-GCM).
>
> Implement `core/logging.py` (structlog JSON + trace_id correlation) and `core/tracing.py` (OTel auto-instrumentation of FastAPI + SQLAlchemy + httpx + NATS). Expose `/metrics` via `prometheus_client`.
>
> Add a FastAPI app factory in `main.py` that wires middleware, routers, startup/shutdown hooks, and health probes. No business routes yet.
>
> **Verification:** gates; `curl /healthz` returns 200; `curl /metrics` shows Python + custom metrics; a token minted via Keycloak dev realm is accepted by a dummy protected route; a test that publishes to NATS and receives the message via a subscriber passes.

---

## Prompt 3 — Vision core: detector, tracker, preprocessing, homography, privacy

> In `vision/`:
>
> 1. `preprocess.py` — implement CLAHE on YUV-Y, optional tonemap (Drago) and DCP dehaze. Pure functions, numpy in/out, benchmark-friendly.
> 2. `detector.py` — `YoloDetector` class. Constructor loads **any** ONNX detection model whose class list is read from its associated `models.classes` row (never hard-coded). Provider priority `TensorRT → CUDA → OpenVINO → CoreML → CPU`; log the selected provider. `detect(frame, allowed_classes) -> list[Detection]` runs inference, NMS, and filters classes. Include unit tests using fixture frames that exercise at least three domains (vehicle, person, PPE/custom).
> 3. `tracker.py` — wrap `ultralytics.trackers` to expose `BoTSortTracker` and `ByteTrackTracker` behind a single `Tracker` interface. Config-driven selection.
> 4. `homography.py` — `Homography` class stores src/dst points + ref distance, exposes `pixel_to_world(x,y)` and `speed_kph(track_history, fps)` using a moving-average filter (window configurable).
> 5. `privacy.py` — `PrivacyFilter` runs face and plate detectors (ONNX), applies Gaussian blur or pixelation to the frame in-place. Config: `{blur_faces: bool, blur_plates: bool, method, strength}`. Must be idempotent and safe to call on every frame.
> 6. `attributes.py` — `AttributeClassifier` loads an optional secondary ONNX model keyed off `cameras.secondary_model_id`. For each relevant primary detection (configurable which classes — e.g. only `person`), crop the bbox, run the classifier, return `dict[str, Any]` of attributes (e.g. `{hi_vis: true, hard_hat: false}`). Batch crops when possible. Model must be pluggable: a fresh PPE / uniform / forklift model is registered via the `models` API and pointed at a camera with zero code changes.
> 7. `zones.py` — `Zones` loads `cameras.zones` polygons and provides `zone_for_point(x,y) -> zone_id | None` using `shapely`. Cheap; called once per tracked detection per frame.
> 8. `rules.py` — `RuleEngine` evaluates `detection_rules` against each tracked detection + its attributes + its zone. Emits `rule_events` to NATS and the DB; honors per-rule cooldowns.
>
> Add unit tests for each module using recorded fixtures under `tests/fixtures/vision/` covering vehicle, pedestrian, and PPE domains.
>
> **Verification:** gates; `pytest tests/vision` passes; a benchmark script prints p50/p95 latency per module on a 1080p frame for both CPU and CUDA. A second benchmark, `bench_jetson.py`, must be runnable on Jetson Orin Nano Super and must confirm ≥25 FPS end-to-end for YOLO12n @ 640×640 FP16 with BoT-SORT + zones + rules on a single 1080p stream at the 25 W power mode.

---

## Prompt 4 — Inference engine: hardware-aware camera + hybrid worker

> Implement `vision/camera.py` as a factory returning a frame iterator. Detect platform:
> - Jetson + MIPI-CSI → GStreamer `nvarguscamerasrc` pipeline,
> - Jetson + RTSP → `rtspsrc ! rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! video/x-raw,format=BGRx ! videoconvert ! appsink` (uses **NVDEC**; no encode step),
> - x86 → `cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)`.
>
> Honor `frame_skip` and `fps_cap`. Handle reconnection with exponential backoff (max 60s). Emit structured logs on reconnect.
>
> Implement `inference/engine.py` as an async loop that takes an `EngineConfig` (Pydantic) and runs: capture → preprocess → detect → filter → track → speed → attributes → zones → rules → privacy → publish. Subscribe to `cmd.camera.<id>` for live reconfiguration of `active_classes`, `tracker_type`, `privacy`, `attribute_rules`, and `zones` — no restart required.
>
> **Dual publish profiles (critical for Orin Nano):**
>
> - `profile=jetson-nano` (default on `arm64` when NVENC is absent): publish JSON events to NATS. If `privacy.blur_faces=false` and `privacy.blur_plates=false`, MediaMTX may re-serve the original RTSP as passthrough and the browser overlays boxes on an HTML canvas using the JSON events.
> - `profile=jetson-nano` with privacy required: raw passthrough is forbidden for that camera. The worker must publish only a privacy-filtered low-res preview stream via CPU x264 (`ultrafast`,`zerolatency`) with capped resolution / fps.
> - `profile=central-gpu`: the worker runs on HQ's L4 GPU and MAY also push an annotated stream to MediaMTX via WHIP (hardware H.264 via NVENC on the L4).
>
> The profile is auto-detected at startup by probing `nvidia-smi` encoder capabilities; an explicit env var `PUBLISH_PROFILE` overrides.
>
> Implement `inference/publisher.py` with two transports: `NatsPublisher` (default) and `HttpPublisher` (fallback to `POST /api/v1/edge/telemetry` when NATS is unreachable, batches events with a 500ms flush).
>
> Implement `streaming/mediamtx.py` — three modes: (a) RTSP passthrough (register a pull source for the camera's RTSP URL), used only when jetson-nano privacy is off; (b) privacy-filtered CPU preview stream, used when jetson-nano privacy is on; (c) WHIP push of annotated frames, used by central-gpu profile.
>
> Add a CLI `python -m argus.inference.engine --camera-id <uuid>` that loads config from the API and runs the worker. Add a `scheduler.py` on the master that reads the `cameras` table on startup and spawns one worker per `central` or `hybrid` camera (subprocess with a supervision loop).
>
> **Verification:** gates; end-to-end test: seed a camera row pointing at a looping test RTSP published by MediaMTX → worker runs → `tracking_events` rows accumulate → MediaMTX exposes the expected stream variant. Run the end-to-end test three ways: (1) x86 `central-gpu` profile with annotated stream, (2) Jetson `jetson-nano` with privacy off and passthrough + canvas, and (3) Jetson `jetson-nano` with privacy on and only the filtered preview stream exposed.

---

## Prompt 5 — FastAPI master node: CRUD, edge APIs, LLM adapter

> Implement routers in `api/v1/` for `sites`, `cameras`, `models`, `edge`, `query`, `history`, `export`, `incidents`, `streams`, and a WS handler at `/ws/telemetry`. All routes use the RBAC dependency from Prompt 2.
>
> `sites` and `cameras` are full CRUD with Pydantic v2 request/response models. Camera create/update validates the 8 homography points + ref distance, primary / secondary model references, and the `privacy` object against the tenant policy (privacy policy may force certain flags true).
>
> `models` supports list, create, and patch. `POST /api/v1/models` registers ONNX metadata (task, classes, shape, checksum, license) so cameras can reference models without code changes.
>
> `POST /api/v1/edge/register` bootstraps a new edge node: issues a scoped NATS nkey + edge API key, returns config (MediaMTX creds, overlay network hints).
>
> `POST /api/v1/edge/telemetry` accepts a batch of tracking events (JSON), validates, writes to `tracking_events`, republishes to NATS for WS fan-out. Idempotent on `(camera_id, ts, track_id)`.
>
> `WS /ws/telemetry` subscribes the connected user to NATS `evt.tracking.*` filtered to the tenant's cameras. Use backpressure (drop oldest) if the client is slow.
>
> `GET /api/v1/history` queries the appropriate continuous aggregate (`events_1m` or `events_1h`) based on `granularity`, grouped by `class_name`.
>
> `GET /api/v1/export` streams CSV or Parquet (`format=csv|parquet` query param).
>
> `POST /api/v1/streams/{camera_id}/offer` implements WebRTC signaling by proxying to MediaMTX's WebRTC egress endpoint.
>
> Implement the LLM adapter in `llm/`:
> - `adapter.py` defines the `LLMClient` Protocol and the `ClassFilterResponse` Pydantic model.
> - `providers/openai.py`, `providers/anthropic.py`, `providers/gemini.py` route through LiteLLM.
> - `providers/ollama.py` and `providers/vllm.py` hit local HTTP endpoints with JSON-mode.
> - `parser.py` composes the prompt, calls the configured provider, validates via Instructor, falls back to a keyword matcher on failure. Responses are audit-logged with prompt + model + latency.
>
> `POST /api/v1/query` takes `{prompt, camera_ids[]}`, runs the LLM, and publishes `cmd.camera.<id>` with the new `active_classes` for each camera. Returns the resolved class list.
>
> **Verification:** gates; contract tests for every route; a test that POSTs to `/api/v1/query` with `"only watch buses and trucks"` flips the worker's `active_classes` observable via NATS within 1s.

---

## Prompt 6 — Streaming UX: MediaMTX wiring, WebRTC signaling, MJPEG fallback

> Finalize MediaMTX configuration in `infra/mediamtx/mediamtx.yml`: auth via JWT, enable WebRTC + LL-HLS + MJPEG, CORS for the SPA origin, per-stream publish auth keyed off the camera's id, and stream-level policy so privacy-required edge cameras never expose raw passthrough variants.
>
> In the backend, implement `streaming/webrtc.py` with a `negotiate_offer(camera_id, sdp_offer)` that returns the SDP answer after checking auth and issuing a short-lived JWT for MediaMTX.
>
> Add `GET /video_feed/{camera_id}` as a server-side proxy to MediaMTX's MJPEG endpoint (kept for forensic use); apply rate-limiting (10 concurrent per user).
>
> **Verification:** gates; opening the MediaMTX web UI shows the expected stream variant for a running camera (annotated on `central-gpu`, passthrough on `jetson-nano` with privacy off, filtered preview on `jetson-nano` with privacy on); a plain HTML test page consumes the WebRTC offer route successfully.

---

## Prompt 7 — Frontend foundation: auth, layout, shell, type-safe API client

> In `frontend/`:
>
> 1. Generate a TypeScript API client from the OpenAPI schema (`openapi-typescript` + `openapi-fetch`). Wire TanStack Query with typed hooks (`useSites`, `useCameras`, etc.).
> 2. Implement OIDC PKCE login via `oidc-client-ts` against Keycloak. Store the user in a Zustand store. Add a `<RequireAuth>` boundary and a `<RequireRole role>` component.
> 3. Build the app shell: top nav (Dashboard, Live, History, Incidents, Settings), tenant switcher (only for `superadmin` users authenticated via the `platform-admin` realm), user menu with logout.
> 4. Implement `pages/Sites.tsx` and `pages/Cameras.tsx` as shadcn data tables with create/edit dialogs. The camera form must include: processing-mode select (central / edge / hybrid), RTSP URL (masked), primary / secondary model selectors, tracker type, privacy toggles, and a `HomographyEditor` component for 4 src + 4 dst points on a frame snapshot + ref distance.
>
> **Verification:** gates; Playwright test: login → create site → create camera with homography → verify it shows on the Cameras table.

---

## Prompt 8 — Live Dashboard: WebRTC player + telemetry overlay + dynamic stats + NL query

> Implement `components/VideoStream.tsx`:
> - Try WebRTC first (via `POST /api/v1/streams/{id}/offer`); fall back to LL-HLS via `hls.js`; final fallback is MJPEG `<img>`.
> - Render a `<canvas>` absolutely positioned over the `<video>`/`<img>` sized to match.
>
> Implement `components/TelemetryCanvas.tsx` that subscribes to `/ws/telemetry` and draws bounding boxes, class labels, track IDs, and speed (if present) on the canvas. Throttle redraw to `requestAnimationFrame`; decouple from video decode.
>
> Implement `components/DynamicStats.tsx` that auto-generates stat cards from the `counts` object in each telemetry frame (one card per distinct `class_name`). No hardcoded class list.
>
> Implement `components/AgentInput.tsx` — chat bar wired to `POST /api/v1/query`, supports per-camera or global scope, shows the resolved class list + model + latency inline.
>
> `pages/Dashboard.tsx` renders an N×M responsive grid of `VideoStream` tiles for the user's subscribed cameras. Include presence indicators (online/offline per last heartbeat).
>
> **Verification:** gates; Playwright: start two test cameras → dashboard shows both tiles with live overlays → issue NL query `"only show cars"` → within 2s, bus detections disappear from the canvas.

---

## Prompt 9 — History, exports, incidents

> Implement `pages/History.tsx`:
> - Date-range picker (shadcn + `react-day-picker`).
> - Granularity select (1m / 5m / 1h / 1d).
> - Camera & class multi-select filters.
> - ECharts time-series with one line per class; supports brush zoom and CSV/Parquet download buttons that call `/api/v1/export`.
>
> Implement `pages/Incidents.tsx` listing recent incidents with snapshot previews (MinIO signed URLs), filterable by camera and type.
>
> Add a server-side aggregation endpoint that returns denormalized rows suitable for ECharts directly (to avoid client-side reshaping on huge ranges).
>
> **Verification:** gates; a seeded 7-day dataset renders within 500ms on the History page; CSV export of a 24h range downloads and validates.

---

## Prompt 10 — DevOps hardening: Docker, k3s, observability dashboards, CI/CD, secrets

> 1. Multi-stage Dockerfiles. **Backend/central** image: distroless base, non-root, `linux/amd64`. **Edge/Jetson** image: base `nvcr.io/nvidia/l4t-jetpack:r36.4.0`, `linux/arm64`, includes GStreamer + `onnxruntime-gpu` Jetson wheel + TensorRT runtime + non-root user. Frontend image: nginx, `linux/amd64`. Drive all builds via `buildx` and a `Makefile` target `build-multiarch`.
> 2. Helm chart in `infra/helm/argus/` with values for `central` and `edge` profiles. The `edge` profile sets `publishProfile: jetson-nano`, disables NVENC-dependent features, and pins resource limits suited to 8 GB unified memory.
> 3. `infra/docker-compose.edge.yml` for single-node edge with only `inference-worker`, `mediamtx`, `nats-leaf`, `otel-collector`. Include a `device_cgroup_rules` / `runtime: nvidia` block so the worker gets GPU access on Jetson.
> 4. Confirm bootability on Jetson Orin Nano Super 8 GB: document the one-liner (`sudo nvpmodel -m 2 && sudo jetson_clocks`) to enable the 25 W Super mode, and include a `scripts/jetson-preflight.sh` that checks JetPack 6.2, CUDA 12.6, TRT 10.x, NVDEC present, NVENC absent, Docker + nvidia-container-toolkit. CI must run at least a `docker build --platform linux/arm64` of the edge image, and the release workflow must produce signed arm64 images.
> 5. Grafana dashboards committed under `infra/grafana/dashboards/`: `fleet-overview.json`, `per-camera-health.json`, `inference-perf.json`, `llm-cost-latency.json`, `privacy-enforcement.json`.
> 6. Prometheus rules + Alertmanager routes for the alerts listed in spec §8.
> 7. Secrets via SOPS + age; document the rotation procedure in `docs/runbook.md`.
> 8. GitHub Actions: `ci.yml` (lint → type → test → build images → push to GHCR on tags), `release.yml` (semantic-release, publish Helm chart, sign images with cosign, generate SBOM with syft).
> 9. Playwright E2E matrix runs against compose in CI.
> 10. Copy the two seed ADRs (`ADR-0001-identity-provider.md`, `ADR-0002-central-gpu.md`) into `docs/ADR/` and add a short `docs/ADR/README.md` explaining the MADR format and how to add new ADRs.
>
> **Verification:** gates; `helm template` renders cleanly; compose-edge boots on a Jetson Orin Nano Super dev box (or qemu arm64) and registers with HQ; GitHub Actions pipeline is green end-to-end.

---

## Stretch Prompt 11 (optional) — ANPR, incident clipping, multi-tenant quota

> Add an ANPR post-processor that runs only on vehicles crossing a configured virtual line; plate numbers are hashed before storage unless the tenant opts in to plain-text (with justification). Add automatic 10-second pre/post-event clip capture to MinIO on `incident.triggered` NATS subject. Add per-tenant rate limits on `/api/v1/query` and storage quotas on incidents.

---

## How to use this blueprint with Codex

1. Open an empty repo.
2. Paste the **Bootstrapping instruction** block first and wait for the acknowledgment.
3. Paste **Prompt 1** verbatim. After Codex finishes, run the five gates locally yourself as a sanity check.
4. Commit (`feat: scaffold v4 monorepo`), then paste **Prompt 2**. Repeat.
5. Never skip the gates between prompts — debt compounds fast in a multi-service system like this.
6. If Codex proposes a change that conflicts with `argus_v4_spec.md`, it must stop and ask. Reject silent divergence.

---

## The Five Gates (repeat after every prompt)

1. `docker compose -f infra/docker-compose.dev.yml up -d` boots cleanly.
2. `uv run pytest` passes.
3. `pnpm test` passes.
4. `ruff check` and `uv run mypy --strict src/` are clean.
5. The feature described in the prompt is demoable via the UI (or API for pure-backend prompts).
