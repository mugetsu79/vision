# Core Link Probe Monitoring Design

Status: implemented as the first monitoring-model slice on branch
`codex/sceneops-pack-registry`; later work added source-side edge-agent ICMP
sequence and authenticated Vezor UDP sequence measurement.

## Purpose

The current Link workspace lets an operator add a logical link path and a monitoring target, but the adjacent **Record probe** action reads like it starts monitoring. It does not. It only saves manually entered probe metrics. That creates the wrong mental model for real networking, especially when a site has an opaque third-party SD-WAN path and Vezor can only observe a handoff or endpoint.

This design makes the process explicit:

1. Define a **Link path**.
2. Add one or more **Monitoring targets** to that path.
3. Choose the **Probe source** or vantage point for each target.
4. Let automated probe sources write samples when available.
5. Allow operators to add or delete manual samples without pretending they are automated monitoring.

Core Link remains packless and domain-neutral. The design does not add maritime, traffic, camera, evidence, detection, carrier SDK, payment, or SD-WAN-specific semantics.

## Terms

**Link path**

A logical network path for a site. It may represent a direct physical handoff, a provider-managed SD-WAN path, a logical overlay, or inventory-only knowledge.

**Monitoring target**

An endpoint Vezor can try to observe or use as a reference for link health. Examples:

- `ingest.example.vezor`
- `203.0.113.10`
- `https://provider.example.net/health`
- provider edge gateway address

**Probe source**

The vantage point that produced a probe sample. This is not a free-form note. It answers: "Where was this measurement taken from?"

Allowed source types:

- `manual`: an operator entered an observed sample.
- `backend_synthetic`: the central Vezor backend checked a target it can reach.
- `edge_agent`: a Vezor edge/site agent checked from the site's network.
- `provider_api`: a provider or SD-WAN platform supplied the measurement.
- `import`: another external system supplied the measurement.

**Probe sample**

A recorded measurement for a target or path. It contains latency, throughput if available, packet loss if available, reachability, source type, source label, and recorded time.

## Operator Flow

The Link workspace should guide operators through this sequence:

1. Operator selects a site.
2. Operator adds or edits a **Link path**.
3. Operator adds monitoring targets inside the link path.
4. Operator chooses monitoring behavior for each target:
   - **Manual samples only**
   - **Backend synthetic check**
   - **Edge agent check**
   - **Provider/API import**
5. The monitoring panel shows target cards, not only a flat probe history.
6. Operators use:
   - **Run check now** when a backend synthetic check is available for the target.
   - **Add manual sample** when they are entering an observed result.
   - **Delete sample** for bad or accidental manual entries.

The operator should not need to guess whether adding a target starts monitoring. The target row should show a status such as:

- `Manual samples only`
- `Backend synthetic every 5 minutes`
- `Awaiting edge agent`
- `Provider/API import`

## Monitoring Targets

The existing link path metadata should grow stable target IDs and monitoring configuration. This avoids a new target table while keeping the current connection metadata approach.

Monitoring target shape:

```json
{
  "id": "target-7f3b25c8",
  "label": "Vezor ingest",
  "address": "ingest.example.vezor",
  "probe_type": "https",
  "port": 443,
  "purpose": "vezor_control",
  "expected_latency_ms": 80,
  "monitoring": {
    "enabled": true,
    "source_type": "backend_synthetic",
    "interval_seconds": 300
  }
}
```

Validation:

- `id` is required for every target persisted by the UI.
- Existing targets without IDs should be assigned stable IDs on edit/save.
- `label`, `address`, `probe_type`, and `purpose` are required.
- `probe_type` supports `icmp | tcp | http | https | udp | manual` in current
  Core Link samples. Monitoring target UI still exposes only methods that are
  operational for the selected source.
- `port` is required for `tcp`, `http`, and `https`, and omitted for `icmp`.
- `port` must be 1-65535.
- `monitoring.enabled` defaults to `false`.
- `monitoring.source_type` defaults to `manual`.
- `monitoring.interval_seconds` defaults to `300` when enabled for an automated source.

## Probe Source Semantics

The previous single `source` text field is ambiguous. Keep it for compatibility, but expose structured fields in API responses and UI.

Probe sample fields:

- `target_id`: optional monitoring target ID.
- `target_label`: target label at sample time.
- `target_address`: target address at sample time.
- `probe_type`: `icmp | tcp | http | https | manual`.
- `source_type`: `manual | backend_synthetic | edge_agent | provider_api | import`.
- `source_label`: human-readable source label, for example `operator:yann`, `backend:primary`, `edge-agent:zrh-site-01`, or `provider:acme-sdwan`.
- `source`: compatibility string derived from source type and label.
- `sample_kind`: `manual | automated | imported`.
- `deleted_at`: nullable timestamp. Deleted samples are hidden from history and ignored for latest posture.

Display rules:

- Manual samples display as `Manual sample from <source_label>`.
- Backend samples display as `Backend synthetic from <source_label>`.
- Edge samples display as `Edge agent from <source_label>`.
- Provider/API samples display as `Provider/API from <source_label>`.
- Unknown old samples display with the legacy `source` text.

## Starting Probes

Adding a link path or monitoring target does not silently start a probe from the browser. Browsers are the wrong vantage point and cannot reliably measure site link health.

Backend synthetic checks can be started in two ways:

- **Run check now**: API request runs one supported check from the backend.
- **Scheduled runner**: a server-side runner checks due targets whose metadata enables `backend_synthetic` monitoring.

Supported backend synthetic checks:

- `tcp`: open a TCP connection to host and port.
- `http`: send a HTTP request and measure response time.
- `https`: send a HTTPS request and measure response time.

Unsupported from central backend in this slice:

- Raw ICMP ping. It often needs elevated permissions and does not prove site-side reachability. ICMP targets can still receive manual, edge agent, provider, or imported samples.

Edge-agent ICMP sequence and Vezor UDP sequence samples are now operational
through the edge-agent sample API. Provider/API sources remain contract-ready
but are not implemented as live collectors yet.

## Deleting Probe Samples

Operators need a way to remove accidental manual samples. The system should use soft delete:

- `DELETE /api/v1/link/sites/{site_id}/probes/{probe_id}` sets `deleted_at`.
- Deleted samples disappear from history.
- Deleted samples are excluded from latest probe and derived link posture.
- The API returns 404 if the probe does not belong to the selected site/tenant.

Deletion should be allowed for all samples initially because the system does not yet have audit-grade telemetry retention requirements. The UI copy should call this **Delete sample**, not **Delete probe monitor**.

## UI Changes

Rename **Probe history** to **Monitoring**.

Panel layout:

1. Target cards
   - Path label
   - Target label and address
   - Probe type and port
   - Monitoring source and cadence
   - Last sample summary
   - Actions: `Run check now`, `Add manual sample`

2. Sample history
   - Shows recent samples grouped or filtered by target.
   - Each row shows metrics, source type, source label, recorded time, and delete action.
   - Empty state should say `No probe samples recorded. Add a manual sample or enable a supported monitor target.`

Dialog changes:

- Rename **Record probe** to **Add manual sample**.
- Rename **Probe source** to **Sample source label**.
- Add **Sample source type** select, defaulting to `manual`.
- Prefer selecting a target over selecting a connection. The connection/path can be inferred from target ownership.
- Allow `No target` only for a site-level manual sample.

## Backend Changes

Add structured probe fields to `link_health_probes` with a migration:

- `target_id`
- `target_label`
- `target_address`
- `probe_type`
- `source_type`
- `source_label`
- `sample_kind`
- `deleted_at`

Keep existing `source` for compatibility.

Service changes:

- `record_probe` and `arecord_probe` accept the new structured fields with safe defaults.
- `list_probes`, `alist_probes`, `latest_probe`, and `alatest_probe` exclude soft-deleted samples.
- Add `delete_probe` and `adelete_probe`.
- Add backend synthetic probe helpers for TCP, HTTP, and HTTPS.
- Add `run_probe_target_now` for a target in link path metadata.

API changes:

- Extend `LinkProbeCreate`.
- Extend probe payload responses.
- Add `DELETE /sites/{site_id}/probes/{probe_id}`.
- Add `POST /sites/{site_id}/probe-targets/{target_id}/run`.

Frontend hook changes:

- Add `useDeleteLinkProbe`.
- Add `useRunLinkProbeTarget`.
- Extend probe response helpers through existing loose OpenAPI generated types.

## Testing

Use TDD.

Backend tests:

- recording a manual sample stores `source_type`, `source_label`, `sample_kind`, and target fields.
- deleting a sample hides it from `list_probes` and `latest_probe`.
- the delete route returns 404 for a probe from another site.
- backend synthetic HTTP/HTTPS/TCP runner records reachable and unreachable outcomes.
- ICMP run-now returns a clear unsupported error for backend synthetic source.

Frontend tests:

- Monitoring panel renders target cards from link path metadata.
- Add manual sample creates a probe with target/source fields.
- Delete sample calls the delete hook and removes the row after success.
- Run check now calls the run-target hook for backend synthetic targets.
- The old **Record probe** label is not rendered.

Verification:

- targeted backend link tests and API route tests
- new backend probe runner tests
- targeted frontend Link page tests
- frontend lint and build

## Scope Boundaries

In scope:

- Clear UI wording and process.
- Structured probe source/vantage point.
- Soft delete for probe samples.
- Backend synthetic run-now and runner helper for TCP/HTTP/HTTPS.
- Target-level monitoring configuration in existing link path metadata.

Out of scope:

- A full edge agent implementation.
- Provider-specific SD-WAN SDK integrations.
- Raw ICMP from the central backend.
- Browser-based network probing.
- Audit-grade immutable telemetry retention.
- New passport hash semantics beyond naturally using non-deleted latest samples.

## Spec Self-Review

- No placeholders remain.
- The design answers how probes start, what probe source means, how deletion works, and the intended operator process.
- The design keeps Core Link packless and domain-neutral.
- The plan is narrow enough for one implementation pass with a real but minimal backend synthetic runner.
