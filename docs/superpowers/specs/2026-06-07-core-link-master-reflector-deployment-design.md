# Core Link Master Reflector Deployment Design

## Purpose

Make the Vezor master a real, optional packet-loss measurement target for edge sites. The master deployment should include reflector capability, but operators must choose whether it is enabled for control-link monitoring because a reflector opens a UDP listener and consumes active-measurement traffic.

The product model stays simple:

- Edge sites are the measurement sources.
- The master/control plane stores configuration and samples.
- A master-hosted reflector is deployment infrastructure, not a configurable local master link.
- Operators can choose, per edge control link, whether to use HTTPS/ICMP monitoring only or the master UDP reflector path.

## Current State

Core Link already supports:

- Edge-site link paths and monitoring targets.
- A control-plane `Vezor Master` target site.
- Edge-originated samples with `target_site_id`.
- Reserved `udp_sequence`/STAMP/TWAMP labels and metadata fields.

What is missing:

- A running authenticated UDP reflector.
- A deployment profile that exposes reflector availability/status.
- Edge-agent UDP sequence sending against that reflector.
- UI controls that make reflector monitoring an explicit choice during Vezor Master control-link setup.

## Recommended Approach

Ship the reflector as a master deployment capability, disabled by default until an admin enables it.

This gives three important properties:

1. The code and deployment shape are present everywhere, so setup is discoverable.
2. The UDP listener is not exposed silently.
3. Operators can enable reflector-based control-link monitoring exactly when they decide an edge should actively measure edge-to-master loss.

The first implementation should use Vezor's authenticated UDP sequence protocol from `docs/superpowers/specs/2026-06-07-core-link-reflector-loss-design.md`. It should not claim STAMP/TWAMP compliance yet. STAMP/TWAMP remain future packet modes behind the same profile model.

## Operator Flow

### Master reflector profile

An admin sees a read-only reflector status on the master target view:

- `Disabled`
- `Enabled, not listening`
- `Listening on <public_host>:<port>`
- `Unhealthy`

The same surface exposes an admin-only action:

- `Enable master reflector`
- `Disable master reflector`
- `Rotate reflector key`

Enabling creates or updates a deployment-level reflector profile:

```json
{
  "id": "master-reflector-default",
  "site_id": "00000000-0000-4000-8000-000000000003",
  "scope": "deployment",
  "host_role": "master",
  "enabled": true,
  "mode": "vezor_udp_sequence",
  "public_address": "vezor.example.com",
  "bind_address": "0.0.0.0",
  "udp_port": 8622,
  "key_id": "master-reflector-2026-06",
  "allowed_edge_site_ids": [],
  "allowed_source_cidrs": [],
  "rate_limit_pps_per_source": 100,
  "status": "listening"
}
```

The UI must not display raw UDP secrets in normal status panels. Secret reveal belongs only to an explicit admin setup action or edge support bundle.

### Edge control-link setup

When configuring an edge site's Vezor Master target, the operator chooses:

- `HTTPS health only`: checks control-plane reachability without UDP sequence loss measurement.
- `UDP reflector loss`: sends authenticated UDP sequence probes to the master reflector and records RTT/loss/jitter.
- `HTTPS + UDP reflector`: recommended when reflector is enabled.

If the master reflector is disabled, the UDP choices remain visible but disabled with a direct action for admins: `Enable master reflector`.

If the edge is not allowed by the reflector profile, the UI explains that the profile must allow this edge or its source network before probes will succeed.

## Deployment Model

The master deployment includes reflector support in every target:

- Compose: add a `link-reflector` service or backend sidecar/command profile with UDP port mapping.
- Helm: add reflector values, UDP service port, and optional sidecar/deployment.
- Systemd/installer: ensure master configuration can start/stop the reflector profile through the compose wrapper.

The default is safe:

```env
ARGUS_LINK_REFLECTOR_ENABLED=false
ARGUS_LINK_REFLECTOR_BIND_ADDRESS=0.0.0.0
ARGUS_LINK_REFLECTOR_PUBLIC_ADDRESS=
ARGUS_LINK_REFLECTOR_PORT=8622
ARGUS_LINK_REFLECTOR_KEY_ID=master-reflector-default
ARGUS_LINK_REFLECTOR_RATE_LIMIT_PPS=100
```

When enabled through deployment config or admin UI, the backend starts the reflector listener and advertises the profile to Link Performance.

For Docker Compose and Helm, exposing the UDP port while disabled is acceptable only if no listener is bound. The UI must still report `Disabled` until the listener is active.

## Data Model

Add `link_reflector_profiles`:

| Field | Purpose |
| --- | --- |
| `id` | Stable profile id. |
| `tenant_id` | Tenant boundary. |
| `site_id` | Control-plane target site for master reflector profiles. |
| `profile_kind` | `master` for this implementation. |
| `enabled` | Operator switch. |
| `mode` | `vezor_udp_sequence` initially. |
| `public_address` | Host/FQDN edge agents should target. |
| `bind_address` | Local bind address for the reflector process. |
| `udp_port` | UDP port, default 8622. |
| `key_id` | Non-secret key identifier carried in metadata. |
| `encrypted_secret` | Reflector HMAC secret encrypted with existing config encryption. |
| `allowed_edge_site_ids` | Empty means all tenant edge sites unless source CIDRs restrict it. |
| `allowed_source_cidrs` | Optional network allowlist. |
| `rate_limit_pps_per_source` | Abuse control. |
| `last_status` | `disabled`, `starting`, `listening`, `unhealthy`. |
| `last_error` | Last startup/health error without secrets. |
| `created_at` / `updated_at` | Audit timestamps. |

Monitoring target metadata on an edge link stores only references and non-secrets:

```json
{
  "id": "vezor-master-udp-reflector",
  "label": "Vezor Master reflector",
  "address": "vezor.example.com",
  "target_site_id": "00000000-0000-4000-8000-000000000003",
  "probe_type": "udp",
  "purpose": "vezor_control",
  "monitoring": {
    "enabled": true,
    "source_type": "edge_agent",
    "interval_seconds": 300
  },
  "loss_method": "udp_sequence",
  "loss_packet_count": 50,
  "loss_packet_spacing_ms": 100,
  "loss_timeout_ms": 1000,
  "reflector_profile_id": "master-reflector-default",
  "reflector_address": "vezor.example.com",
  "reflector_port": 8622,
  "reflector_mode": "vezor_udp_sequence",
  "reflector_key_id": "master-reflector-2026-06"
}
```

## API Surface

Add master reflector endpoints:

- `GET /api/v1/link/reflectors/master`
- `PUT /api/v1/link/reflectors/master`
- `POST /api/v1/link/reflectors/master/enable`
- `POST /api/v1/link/reflectors/master/disable`
- `POST /api/v1/link/reflectors/master/rotate-key`

Add edge control-link helper:

- `POST /api/v1/link/sites/{edge_site_id}/control-targets/master`

The helper creates or updates the edge site's Vezor Master monitoring target with one of:

- `https_only`
- `udp_reflector`
- `https_and_udp_reflector`

The route must reject master/control-plane sites as source sites.

## Edge Agent Contract

The edge agent sends UDP sequence packets to the reflector and posts summarized samples to the existing edge sample route.

The edge agent needs:

- API base URL and bearer token.
- Source edge `site_id`.
- Target id, usually `vezor-master-udp-reflector`.
- Reflector address/port.
- Key id and HMAC secret from an explicit support bundle, admin reveal action, or future edge-agent config pull.

The posted sample includes:

- `method: "udp_sequence"`
- `packet_count`
- `packets_received`
- `latency_ms`
- `jitter_ms`
- `measurement_metadata` with session id, received/lost/late/duplicate/out-of-order counts, RTT min/avg/p95/max, packet spacing, timeout, DSCP, and reflector profile id.

## Security

The reflector must:

- Reply only to packets with a valid HMAC for the configured key.
- Use truncated HMAC-SHA256 over the full packet header.
- Never use API bearer tokens as UDP secrets.
- Reply with a packet no larger than the request.
- Rate-limit by source IP and session id.
- Drop packets from disallowed source networks or disallowed edge sites where the profile can infer them.
- Avoid logging packet payloads or secrets.
- Support key rotation with old-key overlap for a short configurable grace window.

## UI Requirements

Master target view:

- Show reflector status and endpoint.
- Show whether UDP reflector monitoring is available for edge sites.
- Show latest edge-to-master UDP sequence samples with `received/sent`, loss, RTT average, variation, late, duplicate, and out-of-order counts.
- Do not show link path, budget, queue, manual sample, or throughput controls on the master site.

Edge target setup:

- Use a `Vezor Master` preset.
- Offer `HTTPS`, `UDP reflector`, and `HTTPS + UDP reflector` choices.
- Show packet count, interval, timeout, packet spacing, and optional DSCP fields for UDP reflector mode.
- Show reflector profile status before save.
- Store structured fields, not policy JSON.

## Non-Goals

- Full STAMP/TWAMP compliance.
- Continuous throughput measurement.
- Configuring link paths on the master/control-plane site.
- Running probes from the master to infer edge health.
- Exposing raw reflector secrets in normal UI panels.

## Acceptance Criteria

- A fresh master deployment has reflector capability discoverable but disabled.
- An admin can enable/disable the master reflector and see listener status.
- Edge sites can create a Vezor Master control target using HTTPS only or UDP reflector measurement.
- Master/control-plane sites cannot configure link paths, local monitoring targets, probes, budgets, policies, queues, or throughput checks.
- The edge agent can run a UDP sequence measurement against the master reflector and post a sample linked to `target_site_id` for the Vezor Master site.
- The UI distinguishes disabled, enabled/listening, and configured-but-not-measurable states.
- Packet loss is computed from sent/received sequence counts, not manually entered percentages.
