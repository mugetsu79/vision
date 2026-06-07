# Core Link Edge Agent Design

## Purpose

Operators need link monitoring that reflects the network path from the real site, not only from the Vezor backend. Backend HTTP/TCP checks can prove that a public endpoint is reachable from the backend, but they cannot measure packet loss on a MacBook, home LAN, vessel router, branch gateway, or third-party SD-WAN handoff. The edge agent is the source-side probe process for those cases.

This design adds an edge-agent measurement path to Core Link. It lets operators configure a monitoring target on a link path, run an agent near that link, and ingest packet-loss samples that include packet counts and measurement method metadata.

## Recommendation

Implemented first edge agent:

- Control plane: Core Link stores and displays edge-agent targets and samples.
- Ingestion: the backend accepts edge-agent samples for configured monitoring targets and computes packet loss from sent/received packet counts.
- Source process: a Python CLI module can run source-side ICMP packet-train checks or Vezor UDP sequence reflector checks and post samples to the backend.
- Metadata: every sample stores method, packet counts, lost packets, jitter/variation when available, duration, and agent identity.

This gives operators something useful today for targets such as `8.8.8.8` and FQDNs that respond to ICMP. It also supports authenticated Vezor UDP sequence when a cooperating reflector endpoint is available. STAMP/TWAMP/provider responder modes remain future protocol modes behind the same metadata model.

## Non-Goals

- Do not make backend synthetic checks claim real packet loss.
- Do not run throughput tests on an interval.
- Do not ship a full installer, service manager, or pairing flow for the edge agent in this step.
- Do not add unauthenticated agent access. The first CLI uses the same bearer-token style as existing local supervisor tooling. Dedicated edge-agent credentials can follow as a separate security task.
- Do not claim STAMP/TWAMP compliance yet. The operational UDP responder in this branch is Vezor UDP sequence only.

## Operator Workflow

1. In Link Performance, create or edit a link path.
2. Add a monitoring target for the thing the site should be able to reach.
3. Choose `Edge agent` as the monitoring source.
4. Choose the probe type:
   - `ICMP` for normal source-side packet loss checks to IP/FQDN targets.
   - `UDP` for authenticated Vezor UDP sequence reflector targets.
5. Run the edge agent near the site with the Vezor site id, target id, and target address.
6. Vezor records each sample, derives link posture, and shows method/source details in Monitoring.

Example:

```bash
python -m argus.link.edge_agent \
  --api-base-url http://127.0.0.1:8000 \
  --bearer-token "$TOKEN" \
  --site-id 00000000-0000-4000-8000-000000000002 \
  --target-id target-google-dns \
  --target 8.8.8.8 \
  --agent-id macbook-home \
  --agent-label "MacBook at home" \
  --packet-count 20 \
  --once
```

## Measurement Semantics

Packet loss is computed by Vezor from packet counts:

```text
loss_percent = ((packet_count - packets_received) / packet_count) * 100
```

The agent reports counts and supporting timing metadata. It does not get to send a trusted arbitrary loss percent.

The current implementation supports:

- `icmp_sequence`: OS `ping` packet train. Works without a reflector, subject to ICMP filtering and OS ping behavior.
- `udp_sequence`: authenticated Vezor packet sequence to a cooperating reflector. It reports sent/received/lost/late/duplicate/out-of-order counts and RTT statistics.

The backend/API metadata also reserves:

- `stamp`
- `twamp`

For STAMP/TWAMP, the expected future design is a cooperating responder at the far end. The source sends sequenced packets, the responder reflects or timestamps them, and Vezor records sent/received counts, RTT/latency, jitter, and loss. This follows the measurement model described by IPPM one-way packet loss and modern STAMP/TWAMP active measurement standards.

## Data Model

Extend `LinkHealthProbe` with:

- `measurement_metadata`: JSON object, nullable in the database and normalized to `{}` at the service boundary.

Extend `LinkProbeType` with:

- `udp`

The metadata object for edge samples contains:

```json
{
  "agent_id": "macbook-home",
  "agent_label": "MacBook at home",
  "method": "icmp_sequence",
  "packet_count": 20,
  "packets_received": 19,
  "packets_lost": 1,
  "jitter_ms": 1.8,
  "duration_ms": 19024,
  "dscp": null,
  "measured_at": "2026-06-07T12:00:00+00:00"
}
```

## API

Add:

```http
POST /api/v1/link/sites/{site_id}/probe-targets/{target_id}/edge-samples
```

Request body:

```json
{
  "agent_id": "macbook-home",
  "agent_label": "MacBook at home",
  "method": "icmp_sequence",
  "packet_count": 20,
  "packets_received": 19,
  "latency_ms": 24,
  "jitter_ms": 1.8,
  "duration_ms": 19024,
  "dscp": null,
  "measured_at": "2026-06-07T12:00:00+00:00"
}
```

Validation:

- `packet_count` must be greater than zero and no more than 10,000.
- `packets_received` must be between zero and `packet_count`.
- `latency_ms`, `jitter_ms`, and `duration_ms` must be non-negative.
- `method` must be one of `icmp_sequence`, `stamp`, `twamp`, or `udp_sequence`.
- `target_id` must refer to an existing monitoring target for the site.

Response:

- Existing probe payload plus `measurement_metadata`.
- `packet_loss_percent` is computed by the backend.
- `source_type` is `edge_agent`.
- `sample_kind` is `automated`.
- `source` is `edge_agent:{agent_id}`.

## Frontend

The Link Performance UI should make the source and method legible:

- `Probe type` includes `UDP`.
- Edge-agent targets can store:
  - loss method
  - packet count
  - optional DSCP
- Target cards show edge-agent method and packet train size.
- Sample history shows edge-agent source and a compact method line, for example:
  - `Edge agent from MacBook at home`
  - `ICMP sequence, 19/20 received, 1.8 ms variation`

The frontend does not start the edge agent in this step. It configures the target and displays samples that the agent posts.

## Error Handling

- Missing target returns 404.
- Malformed edge-agent payload returns 422.
- Unsupported backend synthetic target type still returns 400 for `/run`.
- Agent CLI exits non-zero when ping output cannot be parsed, the target command fails without usable packet statistics, or the API rejects the sample.

## Testing

Backend:

- Service stores and returns measurement metadata.
- API ingests edge-agent packet counts, computes loss, and returns structured metadata.
- API rejects `packets_received > packet_count`.
- Probe type constraints include `udp`.

Agent:

- Parse Linux and macOS ping output.
- Build the edge-agent API payload from parsed packet statistics.
- Post the payload to the correct endpoint with bearer auth.

Frontend:

- Link target form preserves edge-agent loss settings.
- Monitoring panel renders edge-agent targets and sample metadata.

## Rollout Notes

This is a foundation step. Production rollout should later add:

- Edge-agent pairing credentials scoped to a tenant/site.
- A service artifact for running the agent continuously.
- UDP reflector/STAMP/TWAMP endpoint support for controlled networks.
- A UI copyable command that fills site id, target id, API URL, and recommended packet count.
