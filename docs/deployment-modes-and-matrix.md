# Vezor Deployment Modes And Matrix

This document explains how to choose between `central`, `edge`, and `hybrid` camera processing in Vezor, then maps those choices onto practical deployment shapes.

It is the short decision document.

For step-by-step rollout instructions, use [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md).

## Core Terms

- `master node` / `HQ node`: the central Vezor control plane and primary services node. It runs the API, PostgreSQL/TimescaleDB, Keycloak, NATS JetStream, MediaMTX, the frontend, and central workers.
- `edge node`: a site-local compute box that can run a Vezor inference worker, local MediaMTX, a NATS leaf node, and an OTEL collector.
- `camera native ingest`: the stream the analytics pipeline uses internally.
- `browser delivery`: the stream variant operators watch in the UI. This can be lower resolution or lower FPS than native ingest.

## Processing Modes

### `central`

In `central` mode, the heavy lifting happens on the HQ/master side.

- The edge can be just a camera, or a very thin site with almost no local compute.
- The master node pulls the camera stream and runs inference centrally.
- This is the simplest operating model when network connectivity to HQ is strong and stable.

Use `central` when:

- the camera can reliably reach the HQ/master node
- you want the lowest site complexity
- privacy policy does not require keeping inference local
- the WAN or LAN path can tolerate native or near-native upstream video

### `edge`

In `edge` mode, the heavy lifting happens at the site.

- The edge node runs the inference worker locally.
- It sends tracking events, telemetry, heartbeats, incident clips, and optional preview streams back to HQ.
- This is the preferred pattern when bandwidth is constrained or privacy must be enforced before frames leave the site.

Use `edge` when:

- uplink bandwidth is limited or expensive
- privacy filtering should happen locally
- the site must keep operating even if HQ connectivity degrades
- you have a capable edge box such as a Jetson Orin Nano

### `hybrid`

In `hybrid` mode, both the edge and HQ participate.

- The intended architecture is that the edge performs primary detection and tracking.
- HQ then performs heavier downstream analytics such as cross-camera correlation, re-identification, or longer-horizon analysis.

Use `hybrid` when:

- you want local responsiveness at the site
- you also want heavier central analytics or fleet-wide reasoning
- you are willing to operate both local compute and HQ compute for the same camera path

Important implementation note:

- `hybrid` is architecturally first-class in the spec and schema.
- Today, the most mature and operationally straightforward paths are still `central` and `edge`.
- Treat `hybrid` as the right strategic mode for advanced deployments, but expect more integration validation than the other two.

## Hardware Guidance

### First-class targets today

- HQ/master: Linux `amd64` server or workstation
- Central inference GPU: NVIDIA L4 24 GB is the reference target
- Edge inference: NVIDIA Jetson Orin Nano Super 8 GB is the hardened edge reference

### Practical portability

The software architecture is designed to be portable across `linux/amd64` and `linux/arm64`, and the worker stack is intended to remain portable across Jetson-class and other compute environments.

Operationally, though:

- Jetson is the most explicitly packaged and validated edge target today
- generic `x86` edge nodes are plausible, especially with NVIDIA GPUs
- generic `arm64` edge nodes other than Jetson are possible in principle, but are not as production-hardened in this repo yet

## Browser Delivery Model

Vezor separates analytics ingest from operator viewing:

- analytics can keep using the native stream
- browsers can receive a lower-bitrate rendition such as `1080p15`, `720p10`, or `540p5`
- privacy-safe preview/transcode paths can be used even when passthrough is allowed

This means the system can reduce bandwidth for operator viewing without necessarily lowering inference quality.

## Mode Selection Table

| Mode | Edge requirement | Where inference runs | What goes to HQ | Best fit |
|---|---|---|---|---|
| `central` | none, or very thin edge | HQ/master | raw video is pulled centrally; all analytics happen at HQ | labs, simple sites, strong connectivity |
| `edge` | capable edge compute | edge node | telemetry, events, clips, optional preview streams | bandwidth-sensitive or privacy-sensitive sites |
| `hybrid` | capable edge plus HQ compute | split between edge and HQ | edge outputs plus heavier central processing | advanced sites needing both local responsiveness and central intelligence |

## Deployment Matrix

| Scenario | HQ/master | Edge | Camera pattern | Recommended mode mix | Why |
|---|---|---|---|---|---|
| Lab and development | one developer machine or one small Linux box | none | test cameras, recorded loops | mostly `central` | easiest bring-up |
| Small single site with strong uplink | one central Linux `amd64` node | none or very thin edge | 5-20 cameras | mostly `central` | lowest operating complexity |
| Small single site with weak uplink | one central Linux `amd64` node | one Jetson or similar edge node | 5-20 cameras | mostly `edge` | reduces bandwidth and keeps privacy local |
| Multi-site production | one stronger central node with GPU | one or more edge nodes per site | 25-250 cameras | mix of `edge`, `central`, selective `hybrid` | best balance of scale, resilience, and site autonomy |
| Central-heavy analytics deployment | one larger HQ node with L4 or better | optional edge | dense HQ-connected camera groups | more `central`, selective `hybrid` | central GPU economics are favorable |

## Recommended Decision Rules

Choose `central` if:

- the site has reliable, high-bandwidth connectivity to HQ
- you want to minimize site hardware and maintenance
- privacy rules allow central inference

Choose `edge` if:

- bandwidth reduction is a top goal
- privacy should be enforced before frames leave the site
- the site must keep local intelligence during HQ connectivity issues

Choose `hybrid` if:

- you need local site responsiveness and central higher-order analytics
- you are comfortable with a more advanced deployment pattern
- you specifically need fleet-level or cross-camera intelligence layered on top of local inference

## Recommended Starting Point

For most real deployments:

1. start with `central` in the lab
2. move bandwidth-sensitive or privacy-sensitive cameras to `edge`
3. introduce `hybrid` only when the central second-stage analytics justify the added complexity

## Related Documents

- [operator-deployment-playbook.md](/Users/yann.moren/vision/docs/operator-deployment-playbook.md)
- [runbook.md](/Users/yann.moren/vision/docs/runbook.md)
- [argus_v4_spec.md](/Users/yann.moren/vision/argus_v4_spec.md)
