# Traffic Monitor V4 — Architecture & Implementation Design

> **Status:** Supersedes [archive/traffic_monitor_v3_spec.md](/Users/yann.moren/vision/archive/traffic_monitor_v3_spec.md). Retains V3's domain-agnostic, hybrid edge/central vision while resolving the V3 draft's mismatches around edge privacy/streaming, auth tenancy, and control-plane APIs.
>
> **Scope target:** mid-scale commercial VMS — 5–50 sites, 25–250 cameras.
>
> **Primary consumers of this doc:** (1) human reviewers, (2) `ai-coder-prompt-v4.md` which feeds Codex / Claude Code.

---

## 1. Goals & Directives for the AI Coder

1. **V1 is dead code.** Do **not** port, copy, refactor, or import anything from V1 (Flask, Flask-SocketIO, eventlet, MobileNet-SSD, SORT, jQuery, Bootstrap, the `traffic.db` schema, any V1 Python modules, or any V1 HTML/CSS/JS). V1 is listed in `/v1/` only so the AI coder recognizes the *problem shape*; no line of V1 code is to survive in V4.
2. **Domain-agnostic by design.** The system is *not* a car counter. It is a general-purpose real-time multi-object detection, tracking, and analytics platform. See §10 for the full capability catalogue. In short:
   - **All 80 COCO classes** are detected and countable out of the box — people, bicycles, cars, trucks, buses, motorcycles, animals, bags, and more.
   - **Any custom ONNX model** plugs in via the `models` table with zero code changes — PPE (hard hat, hi-vis vest, gloves, boots, goggles, respirator), forklifts, weapons, license plates, uniforms, drones, livestock, fire/smoke, fallen persons, abandoned objects, wildlife, emergency vehicles, etc.
   - **Attributes per tracked object** are produced by an optional secondary classifier (see §5.1.7): *"this person is wearing a hi-vis vest but no hard hat"*.
   - **Counting modes** include instantaneous count, cumulative count, directional line-crossing, speed, dwell time, density, trajectory, proximity between objects, attribute combinations, queue length, loitering, abandoned-object detection, and (opt-in) cross-camera re-identification.
   - **Rules** compose freely across class × attribute × zone × time-window × speed × proximity, with actions `count | alert | record_clip | webhook`.
   - **Mixing domains in one deployment is first-class**: Camera A does traffic speed, Camera B does PPE compliance, Camera C does retail queue analytics, Camera D does perimeter security — same database, same dashboard, no code forks.
   - *Out of scope by design:* facial identification, action recognition networks bundled in-box, video-LLM scene captioning. These are roadmap / separate-SKU items (see §10.7).
3. **Reference edge hardware is the NVIDIA Jetson Orin Nano Super 8 GB.** The spec and blueprint must be buildable and runnable on that device out of the box. See §3.2 for the hardware profile and its constraints — most importantly: **no NVENC** on Orin Nano, so V2's "annotated-frame re-encode at the edge" path is infeasible. V4 routes around this (see §5.5).
4. Build a **true hybrid** inference pipeline: a camera can be `central` (master pulls RTSP and runs inference locally on HQ GPU), `edge` (Orin Nano runs inference and publishes events), or `hybrid` (edge does primary detection, central does re-identification and long-term analytics). Same worker binary, different deployment profile.
5. **LLM-driven dynamic tracking** via a provider-agnostic adapter, with a first-class local mode (Ollama / vLLM) so an air-gapped site can keep working.
6. **Low-latency streaming** (WebRTC / LL-HLS) replaces V2's MJPEG as the default; MJPEG stays as a forensic fallback.
7. **Privacy by default**: on-frame face + license-plate anonymization, toggleable per camera, enforced in the inference pipeline so anonymization happens *before* any frame leaves the edge.
8. **Production concerns are not optional**: OIDC/JWT auth, RBAC, OpenTelemetry traces/metrics/logs, secrets management, migrations, CI/CD, multi-arch Docker images (`linux/amd64` + `linux/arm64` for Jetson).
9. **Typed everywhere**: Pydantic v2 on the backend, TypeScript strict on the frontend, JSON-Schema on LLM outputs and edge payloads.

---

## 2. System Architecture

### 2.1 Logical topology

```
                                ┌──────────────────────────────────────────────┐
                                │               Master Node (HQ)               │
                                │                                              │
  ┌────────────┐    OIDC / JWT  │  ┌───────────┐   ┌────────────┐              │
  │  Browser   │────────────────┼──│  FastAPI  │──▶│ PostgreSQL │              │
  │ React SPA  │◀───WebRTC/WS──┐│  │  API + WS │   │ TimescaleDB│              │
  └────────────┘                │  └─────┬─────┘   └─────┬──────┘              │
         ▲                      │        │               │                     │
         │ HLS / WebRTC         │  ┌─────▼─────┐   ┌─────▼──────┐              │
         └──────────────────────┼──│ MediaMTX  │   │    Redis   │  (cache,     │
                                │  │ (WebRTC,  │   │            │   active_cls)│
                                │  │  LL-HLS,  │   └────────────┘              │
                                │  │  MJPEG)   │                               │
                                │  └─────┬─────┘                               │
                                │        │                                     │
                                │  ┌─────▼──────────────────────────┐          │
                                │  │ NATS JetStream (event bus)     │◀─┐       │
                                │  └─────┬──────────────────────────┘  │       │
                                │        │                             │       │
                                │  ┌─────▼───────┐   ┌───────────────┐ │       │
                                │  │  Inference  │   │   LLM Adapter │ │       │
                                │  │  Worker(s)  │   │ (cloud/local) │ │       │
                                │  └─────┬───────┘   └───────────────┘ │       │
                                │        │ RTSP                        │       │
                                └────────┼─────────────────────────────┼───────┘
                                         │ (central-mode cameras)      │
                                         ▼                             │
                                 Cameras @ HQ LAN                      │
                                                                       │
  ┌──────────────────────────────────────────────────────────────────┐ │
  │                       Edge Site (Jetson / x86)                   │ │
  │                                                                  │ │
  │  Cameras ──RTSP──▶ Inference Worker ──▶ Privacy Filter           │ │
  │                         │                    │                   │ │
  │                         ▼                    ▼                   │ │
  │                  MediaMTX (local)     NATS client ──────────────┼─┘
  │                         │                                        │
  │                         └── WebRTC peer to browser (if direct)   │
  │                                                                  │
  │  Tailscale / WireGuard overlay back to HQ                        │
  └──────────────────────────────────────────────────────────────────┘
```

### 2.2 Process model

| Process                | Runs on              | Responsibility                                                             |
|------------------------|----------------------|----------------------------------------------------------------------------|
| `api`                  | Master               | FastAPI app — REST, WS, SSE, signaling, auth, CRUD                         |
| `scheduler`            | Master               | Spawns / supervises central-mode workers, rebalances on camera changes     |
| `inference-worker`     | Master or Edge       | One per camera: capture → preprocess → YOLO → tracker → speed → privacy → publish |
| `mediamtx`             | Master + Edge        | RTSP ingest, re-pack to WebRTC / LL-HLS / MJPEG, per-stream auth tokens    |
| `nats`                 | Master (+ edge leaf) | JetStream event bus (tracking events, telemetry, commands)                 |
| `postgres+timescale`   | Master               | Config + time-series events hypertable                                     |
| `redis`                | Master               | Ephemeral state (active_classes cache, rate-limit, WS presence)            |
| `otel-collector`       | Master + Edge        | Fan-in of metrics/logs/traces                                              |
| `prometheus/grafana/loki/tempo` | Master      | LGTM observability stack                                                   |
| `keycloak`             | Master               | OIDC provider, RBAC, tenant realms + platform-admin realm                   |

Edge sites run a slim subset: `inference-worker`, `mediamtx`, a **NATS leaf node** (so events flow over a single persistent mux connection back to HQ), and an `otel-collector` agent. No Postgres at edge.

### 2.3 Deployment unit

* Dev: `docker compose -f infra/docker-compose.dev.yml up`.
* Prod central: Helm chart on k3s/k8s.
* Prod edge: `docker compose -f infra/docker-compose.edge.yml up -d` or k3s single-node + Flux for GitOps.
* Overlay network: Tailscale (zero-config) or WireGuard (self-hosted).
* Multi-arch images (`linux/amd64`, `linux/arm64`) built via Docker Buildx.

---

## 3. Technology Stack & Reference Hardware (April 2026)

### 3.1 Stack table

| Layer                 | Choice                                                                 | Why                                                                   |
|-----------------------|------------------------------------------------------------------------|------------------------------------------------------------------------|
| Language (backend)    | Python 3.12+                                                          | 3.13 free-threaded build still experimental; 3.12 is the safe target  |
| Web framework         | **FastAPI 0.115+**                                                    | Async, OpenAPI, battle-tested; Litestar considered and declined for ecosystem maturity |
| Package manager       | **uv**                                                                 | 10-100× faster than pip, replaces pip + venv + pip-tools              |
| Lint / format         | **Ruff** (lint + format), **mypy --strict** on `src/`                 |                                                                        |
| ORM / migrations      | SQLAlchemy 2.x async + `asyncpg`, **Alembic**                         |                                                                        |
| Schemas               | **Pydantic v2**, `pydantic-settings` for config                       |                                                                        |
| Database              | **PostgreSQL 16 + TimescaleDB 2.14+**                                 | Time-series hypertable on `tracking_events`, continuous aggregates     |
| Cache / pub-sub       | **Redis 7** + **NATS JetStream 2.10**                                 | Redis for ephemeral state; NATS for durable event bus incl. edge leafs |
| Object store          | **MinIO** (S3-compatible) for incident snapshots & clip storage       |                                                                        |
| Detection model       | **Ultralytics YOLO12** (fallback YOLO11) exported to ONNX             | Latest stable as of Q1 2026; drop-in ONNX export                      |
| Inference runtime     | **ONNX Runtime 1.20+** with providers: TensorRT → CUDA → OpenVINO → CoreML → CPU | Portable across Jetson Orin, Intel, Apple Silicon                    |
| Tracker               | **BoT-SORT** (default) with ByteTrack as alt                          | Better occlusion handling; ultralytics ships it natively              |
| Pre-processing        | CLAHE (YUV Y-channel), optional tonemap / WDR, optional dehaze        |                                                                        |
| Privacy models        | YOLOv8-face (or RetinaFace) + plate detector (OpenALPR-v2 or YOLO fine-tune) | Applied *before* re-encode; enforced at worker level        |
| Streaming server      | **MediaMTX** (WebRTC / LL-HLS / HLS / RTSP / MJPEG)                   | Replaces hand-rolled MJPEG from V2                                    |
| LLM adapter           | **LiteLLM** (cloud providers) + **Ollama** / **vLLM** (local)         | Same `chat.completions` surface for both                              |
| Structured output     | **Instructor** / JSON-Schema response_format                          | Reliable class-list extraction                                        |
| Auth                  | **Keycloak** (OIDC) + FastAPI `fastapi-users` or custom middleware    | Tenant realms + platform-admin realm; RBAC via roles; API keys for edge nodes |
| Observability         | **OpenTelemetry SDK** → **OTel Collector** → Prometheus, Loki, Tempo, Grafana | Single pipeline, replaces ad-hoc logging                       |
| Secrets               | **SOPS + age** in repo, runtime injection via env; Vault optional     |                                                                        |
| Container             | Multi-stage Dockerfiles, distroless runtime, non-root                 |                                                                        |
| Orchestration         | Docker Compose (dev) / **k3s + Helm + Flux** (prod)                   |                                                                        |
| CI/CD                 | **GitHub Actions** + Renovate; release via semantic-release           |                                                                        |
| Testing               | `pytest`, `pytest-asyncio`, `testcontainers` (Postgres/NATS), `playwright` (frontend E2E) |                                                        |
| Frontend framework    | **React 19 + Vite 6 + TypeScript (strict)**                           |                                                                        |
| Styling               | **Tailwind CSS v4** + **shadcn/ui** (Radix primitives)                | Tokens via Tailwind v4 `@theme`                                       |
| Server state          | **TanStack Query v5**                                                 |                                                                        |
| Client state          | **Zustand**                                                           |                                                                        |
| Routing               | **TanStack Router** (type-safe) or React Router v7                    |                                                                        |
| Charts                | **Apache ECharts** (via `echarts-for-react`)                          | Better time-series perf than Chart.js, WebGL renderer available       |
| Video player          | Native `<video>` + **hls.js** (LL-HLS), `RTCPeerConnection` (WebRTC)  |                                                                        |
| Forms                 | react-hook-form + zod                                                 |                                                                        |

### 3.2 Reference edge hardware — NVIDIA Jetson Orin Nano Super 8 GB

This is the **canonical edge device for V4**. Everything must boot on it.

| Attribute                     | Value                                                                |
|-------------------------------|----------------------------------------------------------------------|
| SoC                           | Ampere GPU, 1024 CUDA + 32 Tensor cores                              |
| AI perf ("Super" firmware)    | Up to 67 TOPS (INT8), ~1.7× pre-Super                                |
| Memory                        | 8 GB LPDDR5 **unified** (shared CPU + GPU)                           |
| Power modes                   | 7 W / 15 W / **25 W (Super, recommended)**                           |
| OS / BSP                      | **JetPack 6.2** → L4T r36.4, Ubuntu 22.04                            |
| CUDA / cuDNN / TensorRT       | CUDA 12.6 / cuDNN 9 / **TensorRT 10.x**                              |
| Hardware video decode (NVDEC) | H.264 / H.265 / VP9 / AV1 — **used** for RTSP ingest                 |
| Hardware video encode (NVENC) | **None on Orin Nano** — see annotation strategy below                |
| Container runtime             | Docker with `nvidia-container-toolkit`                               |
| Base image                    | `nvcr.io/nvidia/l4t-jetpack:r36.4.0` (multi-arch `arm64`)            |
| ONNX Runtime                  | `onnxruntime-gpu` for Jetson, prebuilt wheel from Jetson Zoo or NVIDIA NGC; TRT EP first |
| Overlay network               | Tailscale (preferred) or WireGuard back to HQ                        |

**NVENC-free edge streaming strategy.** Because Orin Nano lacks a hardware encoder, V4 does *not* make "annotated re-encode at the edge" the default path. Instead the worker chooses one of these privacy-aware delivery modes:

1. Decodes RTSP with NVDEC.
2. Runs YOLO + tracker on the decoded frames (GPU).
3. **Publishes JSON telemetry events** to NATS (`evt.tracking.<camera_id>`) — typically a few KB/s per camera.
4. If the camera's privacy policy does **not** require anonymization, MediaMTX may re-serve the original RTSP as a passthrough stream and the React client draws boxes / labels / speeds on an HTML `<canvas>` over the decoded `<video>`.
5. If the camera's privacy policy **does** require anonymization, raw passthrough is disabled for that camera. The worker applies blur / pixelation and publishes only a privacy-filtered low-res preview stream using CPU H.264 (`x264 ultrafast, zerolatency`) with capped resolution / fps. No unfiltered frame is exposed outside the worker.
6. For `central-gpu` cameras at HQ, the worker may also push a privacy-safe annotated stream via NVENC.

This keeps Orin Nano inside its thermal and bandwidth envelope while preserving the live-overlay UX. The expensive CPU preview path is conditional on privacy-required edge cameras, not the universal default.

**Performance envelope (observed on Orin Nano Super @ 25 W).**

| Model           | Resolution | Batch | Provider       | FPS (end-to-end incl. tracker) | Notes                                    |
|-----------------|------------|-------|----------------|--------------------------------|------------------------------------------|
| YOLO12n (ONNX)  | 640×640    | 1     | TensorRT FP16  | ~55–60                         | Comfortable for 2 cameras @ 25 fps       |
| YOLO12n (ONNX)  | 1280×1280  | 1     | TensorRT FP16  | ~22–25                         | Use for speed-sensitive roads            |
| YOLO12s (ONNX)  | 640×640    | 1     | TensorRT FP16  | ~28–32                         | Single-camera only on 8 GB variant       |
| YOLO12n INT8    | 640×640    | 1     | TensorRT INT8  | ~80–95                         | Requires calibration dataset             |

**Default edge profile:** YOLO12n FP16 @ 640, BoT-SORT, 2 cameras per Orin Nano, `frame_skip=1`, `fps_cap=25`. Configurable per camera.

**Memory budget:** keep the *sum* of loaded ONNX engines + CUDA workspace + decoder buffers + worker Python under ~5 GB so the rest of the system has headroom on the unified 8 GB pool.

### 3.3 Reference central hardware

See `docs/ADR/ADR-0002-central-gpu.md` for the GPU provisioning decision. Summary: start with **1× NVIDIA L4 (24 GB)** for up to ~50 central cameras; scale to 2× L4 or 1× L40S as central-processed stream count grows.

### 3.4 Explicit non-choices

* **No** Flask, Flask-SocketIO, eventlet (V1 stack, abandoned).
* **No** MobileNet-SSD + SORT (V1, obsolete accuracy).
* **No** raw MJPEG as primary transport (kept only for forensic archive).
* **No** plain multiprocessing queues across the edge boundary — events must go through NATS (durable, replayable).

---

## 4. Data Model

All tables use `uuid` primary keys; timestamps are `timestamptz`. `tracking_events` is a TimescaleDB hypertable partitioned by `ts`.

```sql
-- Tenancy & identity -------------------------------------------------
tenants(id, name, slug, created_at)
users(id, tenant_id, email, oidc_sub, role, created_at)          -- role ∈ {viewer, operator, admin, superadmin}
api_keys(id, tenant_id, name, hashed_key, scope jsonb, expires_at)

-- Topology -----------------------------------------------------------
sites(id, tenant_id, name, description, tz, geo_point, created_at)
edge_nodes(id, site_id, hostname, public_key, version, last_seen_at)
cameras(
  id, site_id, edge_node_id NULL, name,
  rtsp_url_encrypted,                 -- AES-GCM, key in KMS/env
  processing_mode,                    -- enum: 'central' | 'edge' | 'hybrid'
  primary_model_id,                   -- FK → models (detector)
  secondary_model_id NULL,            -- FK → models (attribute classifier, e.g. PPE)
  tracker_type,                       -- enum: 'botsort' | 'bytetrack' | 'ocsort'
  active_classes jsonb,               -- ['car','bus','person','bicycle','worker',...]
  attribute_rules jsonb,              -- see §5.1.7 — e.g. person must wear hi-vis in zone_A
  zones jsonb,                        -- [{id, name, polygon:[[x,y],...], kind}]
  homography jsonb,                   -- {src:[[x,y]*4], dst:[[x,y]*4], ref_distance_m}
  privacy jsonb,                      -- {blur_faces:bool, blur_plates:bool, method:'gaussian'|'pixelate'}
  frame_skip int, fps_cap int,
  created_at, updated_at
)
models(
  id, name, version, task,             -- task ∈ {detect, classify, attribute}
  path, format,                        -- format ∈ {onnx, engine}
  classes jsonb,                       -- label list
  input_shape jsonb,                   -- {h,w,c}
  sha256, size_bytes, license
)
detection_rules(
  id, camera_id, name, zone_id NULL,
  predicate jsonb,                     -- e.g. {class:'person', attribute:{hi_vis:false}}
  action,                              -- enum: 'count' | 'alert' | 'record_clip' | 'webhook'
  webhook_url NULL, cooldown_seconds
)

-- Time series --------------------------------------------------------
tracking_events(                       -- hypertable, chunk 1 day
  id uuid, ts timestamptz,
  camera_id, class_name,
  track_id int, confidence real,
  speed_kph real NULL, direction_deg real NULL,
  zone_id NULL,                        -- which configured zone the centroid sits in
  attributes jsonb NULL,               -- e.g. {hi_vis:true, hard_hat:false}
  bbox jsonb                           -- {x,y,w,h} in pixels
)
rule_events(                           -- hypertable: detected rule matches
  id uuid, ts timestamptz,
  camera_id, rule_id,
  event_payload jsonb,
  snapshot_url NULL
)
-- continuous aggregate: events_1m (tracking_events, per-camera per-class counts)
-- continuous aggregate: events_1h (tracking_events, per-camera per-class counts)

-- Operations ---------------------------------------------------------
incidents(id, camera_id, ts, type, payload jsonb, snapshot_url)
audit_log(id, tenant_id, actor_id, action, target, meta jsonb, ts)
```

---

## 5. Module Specifications

### 5.1 Vision pipeline (`src/argus/vision/`)

1. **Capture** (`camera.py`): hardware-aware factory.
   * Jetson Orin, MIPI-CSI: GStreamer `nvarguscamerasrc ! ... ! appsink`.
   * Jetson Orin, RTSP: `rtspsrc ! rtph264depay ! h264parse ! nvv4l2decoder ! nvvidconv ! appsink`.
   * x86: `cv2.VideoCapture(rtsp, cv2.CAP_FFMPEG)` with `FFMPEG_LOG_LEVEL=warning`.
   * Every pipeline honors `frame_skip` and `fps_cap` from the camera config.
2. **Pre-process** (`preprocess.py`): CLAHE on YUV-Y channel; optional tonemap/WDR (Drago or Reinhard) for sun-glare; optional DCP dehaze.
3. **Detect** (`detector.py`): `YOLO12` ONNX session, provider priority `TensorrtExecutionProvider → CUDAExecutionProvider → OpenVINOExecutionProvider → CoreMLExecutionProvider → CPUExecutionProvider`. Dynamic `active_classes` filter applied pre-tracker.
4. **Track** (`tracker.py`): BoT-SORT by default (configurable) via `ultralytics.trackers`. Output: list of `Track(id, class, bbox, conf, features)`.
5. **Speed** (`homography.py`): `cv2.getPerspectiveTransform(src, dst)` at camera config time, cached. Bottom-center of bbox → world plane → speed via moving-average over last N frames (configurable).
6. **Privacy** (`privacy.py`): run face + plate detectors on decoded frames / relevant crops and composite Gaussian blur or pixelate onto **any frame variant that can leave the worker**. Invariant: if privacy is required, raw passthrough is disabled and only privacy-filtered preview / annotated variants may be published. On Orin Nano this means canvas-over-passthrough is allowed only when privacy is off; privacy-on cameras switch to a filtered preview stream.
7. **Secondary classifier / attribute detection** (`attributes.py`): optional second-stage model keyed off the camera's `secondary_model_id`. For each tracked detection of configured interest (e.g. every `person`), the bbox crop is passed through the secondary ONNX model (classifier or multi-label head) to emit `attributes` such as `hi_vis: true/false`, `hard_hat: true/false`, `uniform_color: "orange"`, etc. Attributes are persisted on `tracking_events.attributes` and are consumable by `detection_rules` (e.g. *"person in zone_A without hi_vis → alert"*). Models pluggable via `models` table; V4 ships with an Ultralytics-fine-tuned PPE model as a reference. Zero code changes are required to swap in a new domain model — drop the ONNX file, register it in `models`, point a camera at it.

### 5.2 Inference engine (`src/argus/inference/engine.py`)

A single async process per camera; same binary for central and edge. Config is a Pydantic model loaded from env + API:

```python
class EngineConfig(BaseModel):
    camera_id: UUID
    mode: Literal["central", "edge", "hybrid"]
    publish: PublishConfig              # nats url, subject, tls, api key
    stream: StreamConfig                # mediamtx push target
    model: ModelRef
    tracker: TrackerConfig
    privacy: PrivacyConfig
    active_classes: list[str]           # dynamically updated via control-plane subject
```

Event flow: `capture → preprocess → detect → filter(active_classes) → track → speed → privacy → { publish(TrackingEvent) , push_frame(mediamtx) }`.

Control plane: subscribe to NATS subject `cmd.camera.<id>` for live updates to `active_classes`, `tracker_type`, `privacy`. No restart required.

Streaming policy:

* `jetson-nano` + privacy off → JSON telemetry + MediaMTX passthrough + browser canvas overlay.
* `jetson-nano` + privacy on → JSON telemetry + privacy-filtered CPU preview stream; raw passthrough disabled.
* `central-gpu` → JSON telemetry + optional privacy-safe annotated stream via NVENC.

### 5.3 API (`src/argus/api/v1/`)

```
GET    /api/v1/sites
POST   /api/v1/sites
GET    /api/v1/cameras                      ?site_id=
POST   /api/v1/cameras
PATCH  /api/v1/cameras/{id}
DELETE /api/v1/cameras/{id}
GET    /api/v1/models
POST   /api/v1/models
PATCH  /api/v1/models/{id}

POST   /api/v1/edge/register                -- edge node bootstrap (returns NATS creds + tokens)
POST   /api/v1/edge/telemetry               -- JSON fallback if NATS unreachable (batched)
POST   /api/v1/edge/heartbeat

POST   /api/v1/query                        -- LLM NL → active_classes
GET    /api/v1/history                      ?camera_id=&from=&to=&granularity=
GET    /api/v1/export                       -- CSV / Parquet
GET    /api/v1/incidents

POST   /api/v1/streams/{camera_id}/offer    -- WebRTC SDP offer (returns answer)
GET    /api/v1/streams/{camera_id}/hls.m3u8 -- LL-HLS fallback
GET    /video_feed/{camera_id}              -- MJPEG forensic fallback

WS     /ws/telemetry                        -- fan-out, subscribes to tenant's cameras
SSE    /sse/events                          -- fallback
GET    /metrics                             -- Prometheus
GET    /healthz  /readyz
```

All endpoints auth-gated except `/healthz`, `/readyz`, `/metrics` (internal). RBAC: `viewer` read-only, `operator` can issue commands (`/query`, start/stop), `admin` full CRUD, `superadmin` cross-tenant. Tenant users authenticate in tenant realms; `superadmin` authenticates in a dedicated `platform-admin` realm and assumes tenant context explicitly.

### 5.4 LLM adapter (`src/argus/llm/`)

```python
class LLMClient(Protocol):
    async def extract_classes(self, prompt: str, allowed: list[str]) -> ClassFilterResponse: ...

# Providers
providers/openai.py    # via LiteLLM
providers/anthropic.py # via LiteLLM
providers/gemini.py    # via LiteLLM
providers/ollama.py    # local HTTP /api/chat, JSON mode
providers/vllm.py      # local OpenAI-compatible server

# Selected via LLM_PROVIDER env var; local-only deployments pin to ollama/vllm.
```

`ClassFilterResponse` is a Pydantic model with JSON-Schema response format; the adapter validates the LLM reply and, on failure, retries once then falls back to a deterministic keyword matcher. Prompt and system message are versioned and stored alongside model outputs for reproducibility.

### 5.5 Streaming (`src/argus/streaming/` + MediaMTX)

Default path depends on deployment profile. For `central-gpu`, the worker may push annotated, privacy-filtered frames to **MediaMTX** via `rtsp://mediamtx:8554/cameras/<id>` using its `whip` or RTSP-push plugin. For `jetson-nano`, the default is MediaMTX passthrough plus browser canvas overlays **only when privacy is off**; if privacy is on, the worker must disable raw passthrough and publish a privacy-filtered preview stream instead. Clients pull via WebRTC (preferred), LL-HLS (iOS/fallback), or MJPEG (forensic only, and never as a privacy bypass). Overlays (bbox, class, speed) may be drawn in the worker for preview streams, and a parallel JSON telemetry stream lets the React canvas re-draw precise overlays on top of the decoded video for interactive UX.

### 5.6 Frontend (`frontend/src/`)

```
src/
├── main.tsx
├── App.tsx                     -- router + auth boundary
├── lib/
│   ├── api.ts                  -- TanStack Query client, auto-typed from OpenAPI
│   ├── ws.ts                   -- WS with exponential backoff, tenant subscription
│   └── auth.ts                 -- OIDC PKCE (via oidc-client-ts)
├── stores/
│   ├── camera-store.ts         -- Zustand: active camera grid
│   └── command-store.ts
├── components/
│   ├── VideoStream.tsx         -- WebRTC first, HLS fallback, canvas overlay for boxes
│   ├── TelemetryCanvas.tsx     -- decouples overlay from video element
│   ├── DynamicStats.tsx        -- auto stat cards from telemetry counts
│   ├── AgentInput.tsx          -- chat bar to /api/v1/query
│   ├── HomographyEditor.tsx    -- click-to-set 4 src + 4 dst points on a frame snapshot
│   └── PrivacyToggle.tsx
├── pages/
│   ├── Dashboard.tsx           -- grid, N×M, responsive
│   ├── Sites.tsx, Cameras.tsx  -- CRUD
│   ├── History.tsx             -- ECharts time-series + CSV/Parquet export
│   ├── Incidents.tsx
│   └── Settings.tsx            -- per-tenant settings, API keys, users
```

---

## 6. Folder Structure

```
traffic-monitor-v4/
├── backend/
│   ├── pyproject.toml                     # uv-managed
│   ├── uv.lock
│   ├── alembic.ini
│   ├── src/argus/
│   │   ├── main.py                        # app factory
│   │   ├── config.py                      # pydantic-settings
│   │   ├── api/v1/                        # routers
│   │   ├── core/                          # security, db, events(NATS), logging, tracing
│   │   ├── vision/                        # camera, preprocess, detector, tracker, homography, privacy
│   │   ├── inference/                     # engine.py, publisher.py
│   │   ├── streaming/                     # mediamtx client, webrtc signaling
│   │   ├── llm/                           # adapter + providers
│   │   ├── models/                        # SQLAlchemy + Pydantic
│   │   └── migrations/                    # alembic versions
│   ├── tests/
│   └── Dockerfile                         # multi-arch, distroless
├── frontend/
│   ├── package.json                       # pnpm
│   ├── vite.config.ts, tailwind.config.ts, tsconfig.json
│   ├── src/                               # see §5.6
│   └── Dockerfile
├── infra/
│   ├── docker-compose.dev.yml             # all services, hot reload
│   ├── docker-compose.edge.yml            # edge subset
│   ├── helm/traffic-monitor/              # prod chart
│   ├── mediamtx/mediamtx.yml
│   ├── nats/nats.conf
│   ├── keycloak/realm-export.json
│   ├── grafana/dashboards/*.json          # traffic, inference perf, edge health
│   ├── prometheus/prometheus.yml
│   └── otel-collector/config.yml
├── models/                                # gitignored; pulled via `make models`
│   ├── yolo12n.onnx
│   ├── face_detector.onnx
│   └── plate_detector.onnx
├── docs/
│   ├── ADR/                               # architecture decision records
│   ├── runbook.md
│   └── privacy.md
├── .github/workflows/
│   ├── ci.yml                             # lint + type + test + build multi-arch
│   └── release.yml                        # semver + helm chart publish
├── Makefile
└── README.md
```

---

## 7. Security & Privacy

* **Transport:** TLS everywhere. Edge ↔ HQ over Tailscale/WireGuard; NATS with nkey auth; MediaMTX with per-stream JWT.
* **At rest:** RTSP URLs encrypted in DB (AES-GCM with key from env/KMS). Postgres disk encryption at the infra level.
* **Auth:** OIDC via Keycloak; PKCE for SPA; short-lived access tokens (15 min) + refresh. Default topology is one tenant realm per tenant plus a dedicated `platform-admin` realm for `superadmin` users. Edge nodes use scoped API keys + rotating NATS credentials.
* **RBAC:** `viewer | operator | admin | superadmin`, enforced by a FastAPI dependency. Audit log on every state-changing call.
* **Privacy enforcement:** anonymization runs in the inference worker *before* frames hit MediaMTX. A per-tenant policy can force `blur_faces=true, blur_plates=true` and prevent an operator from disabling it. If privacy is required on an edge camera, raw passthrough is disabled and only privacy-filtered stream variants may be exposed. Retention policy on `tracking_events` is configurable per tenant (default 90 days).
* **Supply chain:** pinned deps via `uv.lock` + `pnpm-lock.yaml`, SBOM generated per release (syft), container image signing (cosign).

---

## 8. Observability

* **Metrics (Prometheus):** `inference_fps`, `inference_latency_ms`, `yolo_box_count`, `publish_queue_depth`, `edge_last_seen_seconds`, `websocket_clients`, `http_request_duration_seconds`, plus standard Python/process metrics.
* **Traces (Tempo via OTel):** every HTTP request, every `engine.run_frame` span, LLM calls.
* **Logs (Loki):** structured JSON via `structlog`, trace-id correlated.
* **Dashboards (Grafana):** "Fleet Overview", "Per-Camera Health", "Inference Perf (p50/p95/p99)", "LLM Latency & Cost", "Privacy Enforcement".
* **Alerts (Alertmanager):** edge offline > 5 min, FPS < threshold, privacy filter error rate > 0, DB write errors, WS disconnect storms.

---

## 9. Testing & CI

* Unit: `pytest` with >80% target on `vision/`, `inference/`, `llm/`, `api/`.
* Integration: `testcontainers` for Postgres + Redis + NATS; recorded RTSP clips under `tests/fixtures/` for determinism.
* Contract: generate OpenAPI client from the FastAPI schema, run a contract test against the frontend types.
* E2E: Playwright against `docker-compose.dev.yml`, scripted flows (create site → create camera → verify live feed → issue NL query → verify class switch).
* Perf: nightly job runs a 5-min synthetic load (mock RTSP via GStreamer) and records `inference_latency_ms` regressions.

---

## 10. Capabilities & Supported Use Cases

**This is not a car counter.** V4 is a general-purpose real-time vision analytics platform. A single deployment can simultaneously run traffic counting at one camera, worksite PPE compliance at another, retail dwell analytics at a third, and perimeter security at a fourth — from the same binaries, the same database, and the same dashboard. The only per-camera differences are configuration (classes, zones, rules, privacy) and, optionally, the ONNX model file.

### 10.1 What can be detected (object classes)

**Built-in out of the box (YOLO12 on COCO, 80 classes):**

- **People & animals:** person, bird, cat, dog, horse, sheep, cow, elephant, bear, zebra, giraffe.
- **Vehicles:** car, truck, bus, motorcycle, bicycle, airplane, boat, train.
- **Street furniture:** traffic light, fire hydrant, stop sign, parking meter, bench.
- **Sports & personal items:** backpack, umbrella, handbag, tie, suitcase, frisbee, skis, snowboard, sports ball, kite, baseball bat/glove, skateboard, surfboard, tennis racket.
- **Other COCO classes** (food, kitchenware, furniture, electronics, household) — detectable but rarely the use case.

**Drop-in via a custom / fine-tuned ONNX model (no code changes):**

- **Construction PPE:** hard hat (yes/no), hi-vis vest (yes/no), safety boots, gloves, goggles, respirator, harness.
- **Industrial equipment:** forklift, pallet, pallet-jack, crane, conveyor, hand-truck, scissor-lift.
- **Vehicles (extended):** emergency vehicles (ambulance / police / fire), garbage trucks, delivery vans, trailers, snowplows, farm equipment.
- **Security objects:** weapons (handgun / rifle / knife), abandoned bags, drones, ladders, unauthorized climbers on fences.
- **Anomalies:** fire, smoke, spills, fallen person, damage to infrastructure.
- **License plates (ANPR):** plate detector + OCR; plate text hashed-by-default (see §7 privacy).
- **Faces:** face detector for presence / privacy blur; never used for identification in the default build.
- **Uniforms & roles:** company-specific uniforms, hospital scrubs, warehouse vests, security guards, retail staff.
- **Retail:** shopping carts, baskets, shelves, branded packaging.
- **Livestock & wildlife:** cattle, pigs, poultry, deer, bears, specific invasive / protected species.
- **Transit:** wheelchairs, strollers, luggage, transit cards, turnstile anomalies.

The class list for any model is loaded from the `models.classes` row; the inference code has zero hard-coded labels.

### 10.2 How things can be counted / measured

| Measurement                                   | How it works in V4                                                                        |
|-----------------------------------------------|-------------------------------------------------------------------------------------------|
| **Instantaneous count** per class per zone    | Active track IDs inside the zone polygon                                                   |
| **Cumulative count** over time                | `tracking_events` aggregated via TimescaleDB continuous aggregates (1m / 1h)               |
| **Directional line-crossing count**           | Virtual line + tracker history; separate `in` / `out` tallies                             |
| **Speed (km/h or mph)**                       | Homography on bbox bottom-center + moving-average filter                                   |
| **Dwell time** (how long an object stays)     | Per-track enter/exit timestamps per zone; reported as p50 / p95 / max                     |
| **Density / occupancy**                       | Track count ÷ zone area; heatmap over sessions                                            |
| **Trajectory / path**                         | Per-track centroid history persisted to `tracking_events.bbox` time-series               |
| **Proximity** (object ↔ object distance)      | Pairwise world-plane distance (via homography) evaluated per frame                         |
| **Attribute presence / absence**              | Secondary classifier output (e.g. `hi_vis: false`) attached to each `tracking_event`      |
| **Attribute combinations**                    | Rule engine composes predicates: class + attributes + zone + time window                  |
| **Queue length / wait time**                  | Track count in queue zone + dwell time of the frontmost track                              |
| **Loitering**                                 | Person in zone > N minutes → rule fires                                                   |
| **Re-identification across cameras** (opt-in) | ByteTrack + appearance embeddings written to NATS; cross-camera re-ID in post-processing  |
| **Abandoned-object detection**                | Track with (near-)zero velocity for > N seconds and class ∈ {`backpack`, `suitcase`, …}   |

### 10.3 Rule / alert types (detection_rules engine)

Every rule is a JSON predicate evaluated per frame per tracked detection. Rules compose cleanly; any combination is legal:

- **Presence** — "any `person` appears in `zone_perimeter` outside 06:00–22:00".
- **Count threshold** — "more than 15 `person` in `zone_entrance` for > 60 s" (crowding / queue alert).
- **Class filter + zone** — "any `truck` in `zone_pedestrian_only`".
- **Attribute compliance** — "`person` in `zone_site` without `hi_vis` OR without `hard_hat`".
- **Speed threshold** — "any `car` with `speed_kph > 50` in `zone_school`".
- **Directional line crossing** — "`bicycle` crossing `line_north_south` in `southbound` direction".
- **Proximity** — "`person` within 2 m of any `forklift` in `zone_warehouse`".
- **Dwell** — "any `suitcase` stationary > 300 s in `zone_concourse`" → abandoned-object alert.
- **Wrong-way** — motion vector opposite to `zone.expected_direction`.
- **Object absence** — "no `guard` class detected in `zone_lobby` for > 15 min".
- **Attribute + time-of-day** — "any `person` in `zone_executive` without `staff_badge` between 20:00–06:00".

Each rule has an **action** (`count | alert | record_clip | webhook`) and a cooldown. Webhook payloads include the snapshot URL from MinIO and the full rule context.

### 10.4 Vertical use-case catalogue

| Vertical / domain        | Example scenarios                                                                        | Primary model       | Secondary                            |
|--------------------------|------------------------------------------------------------------------------------------|---------------------|--------------------------------------|
| **Traffic & roads**      | Vehicle counts by type, speed, red-light running, wrong-way, U-turn, truck-on-restricted | YOLO12 (COCO)       | ANPR (optional)                      |
| **Smart parking**        | Per-stall occupancy, illegally parked vehicles, EV-stall abuse                           | YOLO12              | —                                    |
| **Pedestrian & cycling** | Crosswalk counts, near-misses with vehicles, cyclist counts, micro-mobility mix          | YOLO12              | —                                    |
| **Construction sites**   | PPE compliance (hard hat / hi-vis / boots), worker head-count, forklift proximity, tool presence | YOLO12 + worker FT  | PPE multi-label classifier           |
| **Industrial / warehouse**| Forklift routes, pallet-jack activity, person-near-machine, loading-bay occupancy      | YOLO12 + forklift FT| Uniform / role classifier            |
| **Retail**               | Foot traffic by entrance, queue length, dwell per aisle, staff presence, shelf heat-map | YOLO12 (person)     | Staff-uniform classifier (optional)  |
| **Transportation hubs**  | Crowd density on platforms, abandoned luggage, turnstile jumpers, wheelchair assistance | YOLO12              | Luggage / mobility classifier        |
| **Security & perimeter** | Intrusion, loitering, climbing fence, weapon / drone detection, tailgating through doors | YOLO12 + security FT| Weapon / drone classifier            |
| **Healthcare**           | Patient-fall detection, mask compliance (when required), staff-zone coverage             | YOLO12              | Mask / posture classifier            |
| **Agriculture**          | Livestock counts, animal behavior / lameness, predator intrusion                         | YOLO12 or livestock FT | Species classifier                |
| **Environmental**        | Wildlife monitoring, invasive-species detection, illegal dumping, fire/smoke detection   | YOLO12 or wildlife FT | Species / hazard classifier        |
| **Utility / infra**      | Substation intrusion, vegetation encroachment, flare anomaly, corrosion                  | Custom FT           | Anomaly classifier                   |
| **Emergency response**   | Emergency-vehicle priority at intersections, crowd evacuation flow                       | YOLO12              | Emergency-vehicle classifier         |

### 10.5 Mixing domains on one deployment

A single site can host cameras running completely different pipelines:

- Camera A: `primary=yolo12n`, `active_classes=['car','truck','bus']`, homography enabled — **speed / count**.
- Camera B: `primary=yolo12n + worker-site FT`, `secondary=ppe-classifier`, zones + rules → **PPE compliance**.
- Camera C: `primary=yolo12n`, `active_classes=['person']`, dwell rules → **retail queue analytics**.
- Camera D: `primary=yolo12n + weapon FT`, `secondary=none`, alert webhook → **security**.

Each camera is a row in the `cameras` table. No code branch exists per vertical.

### 10.6 Stacking models on one camera

Two patterns are supported:

1. **Combined fine-tune (recommended):** one ONNX model whose class list includes everything the camera cares about (e.g. a YOLO12 fine-tuned to detect `person, car, forklift, hard_hat, hi_vis`). One inference pass, best FPS.
2. **Primary + secondary chain:** generic detector for shape localization, then a secondary classifier for attributes (e.g. COCO YOLO12 → crop every `person` → PPE multi-label head). Slightly slower but lets you swap the attribute model without retraining the detector.

Registering a new model is three steps: (1) drop the `.onnx` into `/models`, (2) POST to `/api/v1/models`, (3) PATCH the camera to reference it. The worker hot-reloads on the next `cmd.camera.<id>` message.

### 10.7 Out of scope (and why)

- **Facial recognition / identity matching** — intentionally not shipped; face detection is only used for blur. Adding identity requires additional legal review, consent flows, and a signed-dataset model; deferred to a separate product SKU.
- **Full behavioral / action recognition** (e.g. "is this person falling?") — a posture / action classifier can be plugged in as a secondary model, but V4 does not include a bundled action-recognition network out of the box.
- **Video LLM scene understanding** — the LLM adapter drives configuration (class filters, rule generation), not per-frame captioning. Scene-understanding via VLM is a roadmap item for V4.x.

---

## 11. Migration Path from V1

**There is no migration path.** V1 and V4 are separate systems.

* **Code:** nothing from V1 is reused. The AI coder is instructed explicitly (see §1.1) not to port or import V1 Python, HTML, JS, SQL, or config.
* **Data:** if the operator wants to preserve the V1 `traffic.db` historical counts for reference, a one-shot standalone script (outside the V4 repo, under `scripts/legacy/import-v1-sqlite.py`) can read `traffic.db` and insert rows into V4's `tracking_events` as `class_name='car'`, `speed_kph=NULL`, tagged to a synthetic site/camera named `Legacy V1`. This script is **not** part of the V4 runtime and should not appear in any production deploy.
* **Model:** V1 MobileNet-SSD is retired. Any retained footage is re-labeled against YOLO12 classes.
* **UI:** V1's Bootstrap/jQuery/Socket.IO page is discarded. No component-level port.

---

## 12. Resolved & Open Decisions

**Resolved via ADR (see `docs/ADR/`):**

* **ADR-0001** — Identity Provider: **Keycloak** (Authentik considered, rejected for ecosystem maturity).
* **ADR-0002** — Central GPU provisioning: start with **1× NVIDIA L4 (24 GB)** at HQ; scale path documented.

**Still open:**

* **ECharts vs Recharts:** ECharts for time-series at scale; Recharts if team prefers React-idiomatic. Default: ECharts.
* **NATS vs Kafka:** NATS for this scale (mid). Kafka deferred until true enterprise tier.
* **Secondary classifier packaging:** ship a reference PPE model in-repo vs. pull from a model registry on first boot.

---

## 13. Deliverables Checklist (for Codex / Claude Code)

The blueprint file `ai-coder-prompt-v4.md` drives step-by-step implementation. Each prompt in that file must, on completion, leave the repo in a state where:

1. `docker compose -f infra/docker-compose.dev.yml up` boots cleanly.
2. `uv run pytest` passes.
3. `pnpm test` passes.
4. `ruff check` and `mypy --strict` are clean.
5. The feature described in the prompt is demoable via the UI.

Do not proceed to the next prompt until all five gates are green.
