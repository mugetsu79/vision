# Core Link Install-Time Throughput Payload Design

## Status

Planned follow-up from the 2026-06-09 live smoke. Edge-agent UDP reflector
samples work, but throughput remains `0 Mbps` and the "Active connection" card
can show `unknown / unknown` when the site only has control-plane targets and no
operator-defined connection rows.

## Problem

Current Link Performance proves reachability, RTT, jitter, and packet loss via
edge-agent UDP sequence samples. It does not provide a meaningful edge-origin
throughput number unless an operator manually configures a throughput URL.
During install there is also no bounded file created for speed measurement, so
the product cannot run a first edge-origin throughput check automatically.

The UI "Active connection" section reads from configured `link_connections`.
When the only useful path is the master reflector/control target, the selected
site can be healthy while active connection still reads as `unknown / unknown`,
which is technically honest but not helpful.

## Goals

- Create a bounded throughput `.bin` payload during master installation.
- Expose that file through a master route reachable from edge nodes.
- Run one edge-origin throughput sample during edge installation after
  `vezor-edge-agent.service` is installed.
- Add a manual UI trigger for edge-origin throughput measurements.
- Record throughput samples with bytes transferred, duration, Mbps, payload
  size, payload SHA256, and source edge-agent id.
- Make Active connection meaningful when only edge-agent/control-target paths
  exist.

## Non-Goals

- Continuous bandwidth testing.
- Unauthenticated large file serving.
- Replacing UDP sequence packet-loss probes.
- Measuring internet speed; this measures edge-to-master product path
  throughput.

## Product Flow

1. Master installer creates
   `/var/lib/vezor/link-throughput/vezor-speed-test-64MiB.bin` plus a `.sha256`
   sidecar if the file is missing or the digest does not match.
2. Backend serves the payload at
   `/api/v1/link/throughput/payload.bin` to authenticated admins and authorized
   node credentials.
3. Enabling the master reflector/control target includes
   `throughput_test_url`, `throughput_test_max_bytes`, payload size, and payload
   SHA256 in edge-agent config.
4. Edge installer starts `vezor-edge-agent.service` and then runs one
   `vezor-edge-agent --once --include-throughput` sample.
5. Operators can later click **Measure edge throughput** from Link Performance;
   the backend records an edge-agent run request, the edge agent consumes it,
   downloads the bounded payload, and posts the sample.
6. Link posture shows the selected control path and latest edge-agent sample
   instead of `unknown / unknown` when no explicit connection row exists.

## Acceptance Criteria

- A fresh master install creates the `.bin` and `.sha256` files with stable
  size and digest.
- A fresh edge install records one throughput sample from the Jetson with
  `throughput_mbps > 0`.
- The sample history shows edge-agent source, payload bytes, duration, Mbps,
  RTT/loss when available, and payload hash.
- Active connection shows "Vezor Master reflector via edge agent" or an
  equivalent control path label when no explicit connection exists.
- Manual throughput trigger creates a new sample without exposing bearer tokens
  or node credentials.
