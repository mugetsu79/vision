# Core Link Performance Guide

Date: 2026-06-07
Status: current for branch `codex/sceneops-pack-registry`

Core Link is Vezor's domain-neutral network posture layer. It is not FleetOps
or maritime-specific. FleetOps can deep-link into Core Link by site id, but the
Link Performance workspace at `/links` works for any edge site.

## Product Model

- Edge sites own link paths, budgets, policies, monitoring targets, queue
  posture, and manual samples.
- The Vezor master/control plane is a target-only Link Performance site. It can
  receive edge-originated samples and can host an optional reflector endpoint,
  but operators cannot configure local link paths, budgets, probes, queues, or
  throughput checks on the master site.
- A link path is logical operator inventory: ISP circuit, SD-WAN overlay,
  satellite path, LTE backup, Wi-Fi, ethernet handoff, or provider-managed
  transport. Vezor does not need to know every third-party SD-WAN internal hop.
- Monitoring targets are the real IPs/FQDNs/services the edge should be able to
  reach. The target belongs to an edge link path.

## Link Path Setup

Use **Add link path** on an edge site only.

Recommended fields:

- `Link path label`: operator label such as `Home uplink`, `Primary fiber`, or
  `Managed SD-WAN overlay`.
- `Link model`: `Direct`, `Provider managed`, `Logical overlay`, or
  `Inventory only`.
- `Visibility`: `Full visibility`, `Handoff only`, `Overlay only`, or
  `No visibility`.
- `Provider`: ISP, MSP, SD-WAN provider, or carrier name when known.
- `External reference`: circuit id, tenant id, tunnel id, provider ticket, or
  other real-world anchor.
- `Transport visible to Vezor`: choose the physical bearer if known. Use
  `other` when the path is a provider abstraction or Vezor only sees the
  handoff.

For a single handoff into a third-party SD-WAN platform, use:

- `Link model`: `Provider managed` or `Logical overlay`
- `Visibility`: `Handoff only` or `Overlay only`
- `Transport visible to Vezor`: the bearer visible at the edge, or `other`
- `Provider`: the SD-WAN or MSP/provider name
- `External reference`: tenant/tunnel/circuit id

## Monitoring Targets

### Backend Synthetic

Backend synthetic checks run from the Vezor backend network, not from the edge
site. Use them for backend-to-service reachability checks such as HTTP, HTTPS,
or TCP endpoints.

They do not prove the edge site's ISP, SD-WAN, LTE, satellite, or Wi-Fi path.
Backend synthetic samples intentionally show throughput and packet loss as
unmeasured unless an operator runs the explicit manual throughput action.

### Edge Agent ICMP Sequence

Use this for real source-side packet-loss checks from a MacBook, branch host,
router-adjacent machine, vessel LAN host, or other edge vantage point.

Example target for Google DNS:

- `Target label`: `Google DNS`
- `Target address`: `8.8.8.8`
- `Probe type`: `ICMP`
- `Monitoring source`: `Edge agent`
- `Loss method`: `ICMP sequence`
- `Loss packet count`: for example `20`

Example one-shot agent command:

```bash
python -m argus.link.edge_agent \
  --api-base-url https://vezor.example.com \
  --bearer-token "$TOKEN" \
  --site-id "$EDGE_SITE_ID" \
  --target-id target-google-dns \
  --target 8.8.8.8 \
  --agent-id macbook-home \
  --agent-label "MacBook at home" \
  --packet-count 20 \
  --once
```

ICMP can be filtered or deprioritized by networks. Treat it as useful
source-side evidence, not a universal proof of application-path loss.

### Edge Agent UDP Sequence With Reflector

Use UDP sequence when there is a cooperating reflector at the far end. This is
the current state-of-the-art path in Vezor because loss is computed from
sequenced packets sent by the edge agent and replied to by the reflector.

The first operational protocol is Vezor UDP sequence:

- HMAC-SHA256 protected packets
- per-session sequence numbers
- packet spacing and reply timeout
- received/lost/late/duplicate/out-of-order counters
- RTT min/avg/p95/max and RTT variation

It is not STAMP/TWAMP-compliant yet. STAMP/TWAMP/provider modes remain future
responder modes behind the same model.

Example custom reflector target:

- `Target label`: `OpenWISP reflector`
- `Target address`: `openwisp.mugetsu.tech`
- `Probe type`: `UDP`
- `Monitoring source`: `Edge agent`
- `Loss method`: `UDP sequence`
- `Reflector address`: `openwisp.mugetsu.tech`
- `Reflector UDP port`: `8622`
- `Packet count`: `50`
- `Packet spacing ms`: `100`
- `Reply timeout ms`: `1000`
- `Reflector key ID`: the non-secret key id for the reflector secret

Example one-shot agent command:

```bash
python -m argus.link.edge_agent \
  --api-base-url https://vezor.example.com \
  --bearer-token "$TOKEN" \
  --site-id "$EDGE_SITE_ID" \
  --target-id target-openwisp-reflector \
  --target openwisp.mugetsu.tech \
  --agent-id macbook-home \
  --agent-label "MacBook at home" \
  --method udp_sequence \
  --reflector openwisp.mugetsu.tech \
  --reflector-port 8622 \
  --reflector-key-id "$REFLECTOR_KEY_ID" \
  --reflector-secret "$REFLECTOR_SECRET" \
  --packet-count 50 \
  --packet-spacing-ms 100 \
  --loss-timeout-ms 1000 \
  --once
```

## Master Reflector

The master deployment includes reflector capability, disabled by default.

Configuration defaults:

```env
ARGUS_LINK_REFLECTOR_ENABLED=false
ARGUS_LINK_REFLECTOR_BIND_ADDRESS=0.0.0.0
ARGUS_LINK_REFLECTOR_PUBLIC_ADDRESS=
ARGUS_LINK_REFLECTOR_PORT=8622
ARGUS_LINK_REFLECTOR_KEY_ID=master-reflector-default
ARGUS_LINK_REFLECTOR_RATE_LIMIT_PPS=100
```

To actually bind a UDP listener at backend startup, the deployment must set:

```env
ARGUS_LINK_REFLECTOR_ENABLED=true
ARGUS_LINK_REFLECTOR_SECRET=<shared-hmac-secret>
ARGUS_LINK_REFLECTOR_PUBLIC_ADDRESS=<host-or-ip-reachable-from-edges>
```

The Link Performance master target panel exposes the persisted master reflector
profile with enable, disable, and rotate-key actions. The current
implementation stores profile intent and key metadata in Vezor; the backend
UDP listener itself is still started from deployment settings at process
startup. A future reconciliation task should hot-apply profile changes to the
running listener and provide a safe secret-distribution flow for paired edge
agents.

For an edge-to-master measurement, select the edge site, add a link path, use
the `Vezor Master` preset, choose UDP sequence fields, and run the edge agent
against the master reflector endpoint.

## Throughput

Throughput measurement is manual only. Vezor does not run throughput tests at
the monitoring interval because that would waste bandwidth. Operators must use
the explicit **Measure throughput** action on a backend synthetic HTTP/HTTPS
target with a configured throughput URL and byte cap.

## Packet Loss Semantics

Packet loss is never trusted as an arbitrary operator-entered percentage for
edge-agent samples. Vezor computes it from counts:

```text
loss_percent = ((packet_count - packets_received) / packet_count) * 100
```

UDP sequence samples also preserve:

- `packets_lost`
- `packets_late`
- `packets_duplicate`
- `packets_out_of_order`
- `rtt_avg_ms`
- `rtt_variation_ms`
- reflector address, port, and profile/key ids

## Current Gaps

- Edge-agent pairing credentials and service installation are not packaged yet.
- Reflector secrets are not distributed through a polished admin UI.
- Master reflector profile changes are not hot-reconciled into an already
  running backend listener.
- STAMP/TWAMP/provider SD-WAN responder modes are not operational yet.
- Continuous throughput measurement is intentionally out of scope.
