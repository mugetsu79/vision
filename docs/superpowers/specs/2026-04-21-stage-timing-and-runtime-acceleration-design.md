# Worker Stage Timing And Runtime Acceleration Design

## Goal

Make the inference worker measurable enough to explain high CPU usage, then add a cross-platform execution-provider policy so production inference can choose the best available runtime for the actual host instead of assuming one hardware family.

## Current State

- The worker records only total frame duration through [INFERENCE_FRAME_DURATION_SECONDS](/Users/yann.moren/vision/backend/src/argus/core/metrics.py:29).
- The hot path in [InferenceEngine.run_once(...)](/Users/yann.moren/vision/backend/src/argus/inference/engine.py:293) executes capture, preprocessing, detection, tracking, attribute classification, rules, annotation, and publish in one sequential loop.
- The detector and attribute classifier each create an ONNX Runtime session and select the first preferred provider available via [select_execution_provider(...)](/Users/yann.moren/vision/backend/src/argus/vision/runtime.py:19), but there is no explicit host-capability policy, no override surface, and no stage-level visibility.
- The current iMac validation shows a stable stream at lower browser-delivery settings, but worker CPU remains close to 8 cores. That indicates the workload is analytics-heavy rather than browser-delivery-heavy.

## Problem Statement

We currently know that the worker is expensive, but not which stages dominate frame time on each host class. We also have no stable, explicit runtime policy for heterogeneous production hardware:

- Apple Silicon macOS
- NVIDIA-backed Linux
- Intel x86 Linux
- AMD x86 Linux
- old Intel macOS dev hosts

Without stage timing, we will guess. Without an explicit provider matrix, we risk optimizing for the wrong machine or shipping fragile runtime behavior.

## Requirements

### Functional

- Record per-frame stage timings for the worker hot path.
- Expose stage timing through worker-local metrics and structured logs.
- Keep the first stage-timing slice independent of frontend/UI work.
- Introduce a runtime capability policy that can choose the inference provider separately for:
  - primary detection
  - secondary attribute classification
- Support explicit operator/developer override when auto-detection is wrong or when benchmarking requires pinning a provider.

### Platform

- Prefer NVIDIA acceleration on supported Linux NVIDIA hosts.
- Prefer Apple acceleration on supported Apple Silicon macOS hosts.
- Prefer an Intel-optimized path on supported Intel x86 Linux hosts.
- Keep a safe CPU fallback everywhere.
- Do not assume Intel-specific acceleration is valid for AMD x86 hosts.

### Operational

- The worker must continue to run if accelerated providers are unavailable.
- Provider choice must be observable in logs and testable in unit tests.
- Stage timing must not materially change the hot-path semantics or break current telemetry consumers.

## Non-Goals

- Frontend charts or operator UI for stage timings in this slice.
- Dynamic provider switching while the worker is already running.
- ROCm/AMD GPU acceleration in this first pass.
- Replacing the current worker architecture with a multi-process pipeline in this slice.
- Guaranteeing that old Intel macOS dev machines get hardware-accelerated inference.

## Approaches Considered

### Approach 1: Stage Timing Only

Instrument the current worker loop and stop there.

Pros:
- lowest immediate risk
- fastest way to replace guesswork with data

Cons:
- leaves production runtime selection implicit
- does not address cross-platform acceleration

### Approach 2: Provider Selection Only

Add runtime provider selection immediately and infer performance from anecdotal testing.

Pros:
- faster path to possible CPU relief on the right hardware

Cons:
- still no stage-level evidence
- harder to validate whether provider changes helped the real bottleneck

### Approach 3: Phased Timing First, Then Runtime Policy

Add stage timing as the first shippable checkpoint, then add provider selection and host-aware execution policy on top.

Pros:
- gives us evidence before optimization
- aligns with the repo’s existing phased browser-delivery and encoder work
- keeps the fallback path intact during rollout

Cons:
- takes two slices instead of one

## Recommendation

Choose **Approach 3**.

The first checkpoint should make worker cost measurable without changing the inference contract. The second checkpoint should add explicit runtime policy and provider overrides using the timing data to validate impact.

## Chosen Design

### Phase 1: Worker Stage Timing

Add a small timing model around the worker hot path in [InferenceEngine.run_once(...)](/Users/yann.moren/vision/backend/src/argus/inference/engine.py:293).

Tracked stages should include:

- `capture`
- `preprocess`
- `detect`
- `track`
- `speed`
- `attributes`
- `zones`
- `rules`
- `annotate`
- `publish_stream`
- `publish_telemetry`
- `persist_tracking`
- `total`

Outputs for Phase 1:

- Prometheus histograms per stage in [backend/src/argus/core/metrics.py](/Users/yann.moren/vision/backend/src/argus/core/metrics.py)
- a periodic structured worker log summary per camera with rolling averages and p95-like high-water indicators
- optional inclusion of the chosen execution provider in those logs

Phase 1 should not change the websocket telemetry contract yet. The existing [TelemetryFrame](/Users/yann.moren/vision/backend/src/argus/inference/publisher.py:24) stays stable in this slice.

### Phase 2: Runtime Capability Policy

Replace the current “first preferred available provider” behavior with an explicit runtime policy layer.

The policy should evaluate:

- operating system
- machine architecture
- CPU vendor when relevant
- available ONNX Runtime execution providers
- optional explicit override from settings

The policy should choose a provider profile for both the detector and the attribute classifier.

### Provider Matrix

Initial support tiers:

- **Linux x86_64 with NVIDIA**: prefer `TensorrtExecutionProvider`, then `CUDAExecutionProvider`, then CPU fallback.
- **macOS arm64 (Apple Silicon)**: prefer `CoreMLExecutionProvider`, then CPU fallback.
- **Linux x86_64 on Intel CPU**: prefer `OpenVINOExecutionProvider`, then CPU fallback.
- **Linux x86_64 on AMD CPU**: use `CPUExecutionProvider` in this first pass.
- **macOS x86_64 (old Intel iMac)**: treat as CPU fallback unless a validated OpenVINO/CoreML-compatible path is explicitly proven later.

This means the “Intel-optimized inference path” in production is a Linux x86 Intel path first, not a promise that the old Intel iMac becomes a representative accelerated host.

### Override Surface

Add settings for:

- inference execution provider override
- optional session-thread overrides for benchmarking and mitigation
- optional execution-profile override for testing host policy deterministically

Defaults remain automatic.

### Session Construction

Update:

- [YoloDetector](/Users/yann.moren/vision/backend/src/argus/vision/detector.py:28)
- [AttributeClassifier](/Users/yann.moren/vision/backend/src/argus/vision/attributes.py:25)

so they receive an explicit runtime session policy instead of each independently calling `select_execution_provider(...)`.

### Observability For Runtime Choice

At worker startup, log:

- chosen provider for detection
- chosen provider for attributes
- relevant host classification
- whether an override forced the final choice

This must be visible even when worker metrics are disabled.

## OTEL Collector Finding

The current local `otel-collector` failure is not a DNS problem first. It is a startup failure caused by invalid collector config.

- Local config still declares a `loki` exporter in [infra/otel-collector/config.yml](/Users/yann.moren/vision/infra/otel-collector/config.yml).
- The running collector image rejects that config with `unknown type: "loki" for id: "loki"`, so the container never becomes a healthy OTLP endpoint.
- The OpenTelemetry Collector contrib project deprecated the Loki exporter in July 2024 and planned its removal from distributions in 2024, in favor of Loki’s native OTLP ingestion ([GitHub issue #33916](https://github.com/open-telemetry/opentelemetry-collector-contrib/issues/33916)).
- Grafana’s Loki docs now recommend using the `otlphttp` exporter to Loki’s OTLP ingestion endpoint instead of the old Loki exporter ([Grafana docs](https://grafana.com/docs/enterprise-logs/latest/send-data/otel/)).

This OTEL repair is adjacent but separate from the worker runtime plan. It should be fixed independently so local traces and logs are usable again.

## Validation Plan

### Phase 1

- unit-test stage timing aggregation around `run_once()`
- verify new per-stage histograms are registered and labeled by camera
- verify periodic timing summary logs appear without changing telemetry payloads

### Phase 2

- unit-test provider selection across mocked host/provider matrices
- verify startup logs show the chosen runtime policy
- verify detector and attribute classifier both use the resolved provider
- benchmark at least:
  - Intel x86 Linux
  - Apple Silicon macOS
  - NVIDIA Linux
  - CPU fallback host

## Risks

- Stage timing can become noisy if logged every frame instead of rolled up periodically.
- OpenVINO/CoreML availability differs by packaging and OS, so the design must tolerate missing providers cleanly.
- Provider-specific behavior can diverge between detection and attribute models if one model loads and the other does not.

## Success Criteria

- We can explain worker cost using per-stage evidence instead of inference.
- Production hosts use an explicit, testable provider policy rather than implicit provider ordering.
- The worker stays stable on unsupported hosts through a CPU fallback path.
- The old iMac remains a useful stability/dev baseline without being the architecture target for production acceleration.
