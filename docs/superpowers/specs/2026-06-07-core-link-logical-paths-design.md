# Core Link Logical Paths And Policy Controls Design

## Purpose

Operators need the Link workspace to describe what Vezor can actually observe, not imply direct control over physical networking. A site may have a direct fiber/LTE/satellite path, an opaque third-party SD-WAN or managed WAN service, or only a logical overlay that Vezor can probe. The UI should make that distinction clear and let operators attach monitoring targets such as FQDNs, IPs, URLs, or gateway references.

This design keeps Core Link packless and domain-neutral. It does not add maritime, traffic, carrier SDK, payment, detector, runtime, evidence hash, or passport semantic changes.

## Product Model

Rename the operator-facing concept from **Connection** to **Link path**. The backend can continue using the existing `LinkConnection` route/table names for now, but UI copy, tests, and helper names should speak in link paths.

A Link path is a logical description of how a site reaches Vezor-relevant destinations. It is not necessarily a physical interface or carrier circuit.

Required fields:

- `label`: operator label, for example `Managed SD-WAN overlay`.
- `link_model`: one of `direct`, `provider_managed`, `logical_overlay`, `inventory_only`.
- `transport_kind`: existing core enum, used for the visible or best-known handoff. For provider-managed SD-WAN, default to `other` unless the Vezor edge sees a concrete Ethernet/fiber/etc handoff.
- `provider`: optional provider or MSP name.
- `status`: existing status enum.
- `priority_rank`, `availability_scope`, `metered`, budget and expected performance fields: keep existing behavior.

Metadata fields:

- `link_model`: `direct | provider_managed | logical_overlay | inventory_only`.
- `visibility`: `full | handoff_only | overlay_only | none`.
- `external_reference`: free text for SD-WAN edge name, MSP ticket reference, circuit ID, tunnel name, or controller label.
- `monitoring_targets`: array of target objects.

Monitoring target object:

```json
{
  "label": "Vezor ingest",
  "address": "ingest.example.vezor",
  "probe_type": "https",
  "port": 443,
  "purpose": "vesor_control",
  "expected_latency_ms": 80
}
```

Allowed `probe_type` values: `icmp`, `tcp`, `http`, `https`.

Allowed `purpose` values: `vezor_control`, `gateway`, `provider_edge`, `partner_endpoint`, `custom`.

Validation:

- `label`, `link_model`, `visibility`, `transport_kind`, and `status` are required.
- A target is optional, but if present it must have `label`, `address`, and `probe_type`.
- `port` is required for `tcp`, `http`, and `https`; omitted for `icmp`.
- `port` must be 1-65535.
- `expected_latency_ms`, if present, must be non-negative.

## Operator UX

The Add/Edit dialog becomes **Add link path** / **Edit link path**.

Dialog sections:

1. **What this represents**
   - Link path label
   - Link model segmented/select control
   - Provider/MSP
   - External reference

2. **What Vezor can observe**
   - Visibility select
   - Transport visible to Vezor
   - Status
   - Availability scope

3. **Monitoring targets**
   - A compact target editor with rows.
   - Add target button.
   - Each row has label, address/FQDN/IP/URL, probe type, port, purpose, expected latency.
   - Empty target list is allowed and explicitly means inventory-only or awaiting probes.

4. **Capacity and cost**
   - Metered checkbox
   - Monthly bytes
   - Bulk daily bytes
   - Expected downlink/uplink Mbps
   - Expected latency ms
   - Packet loss percent

5. **Advanced routing**
   - Priority rank

The connection inventory panel should be titled **Link paths**. Each row should show:

- label
- model and visibility
- provider/reference if present
- transport/status/metered
- monitoring target count

## Policy UX

Remove the raw policy JSON editor from the operator UI.

Keep the backend storage as JSON for now, but add frontend parse/build helpers and render the policy as structured controls:

- Lane priority order: four fixed lanes displayed in order with Move up / Move down controls.
- Degraded or recovering behavior:
  - checkboxes for lanes to pause.
- Dark or offline behavior:
  - checkboxes for lanes to allow.
- Budget behavior:
  - `pause_bulk_when_daily_budget_exhausted`
  - `avoid_metered_for_bulk_when_budget_exhausted`

Generated policy shape:

```json
{
  "priority_order": ["safety", "evidence", "telemetry", "bulk"],
  "backpressure": {
    "degraded_pauses": ["telemetry", "bulk"],
    "dark_allows": ["safety"],
    "pause_bulk_when_daily_budget_exhausted": true,
    "avoid_metered_for_bulk_when_budget_exhausted": true
  }
}
```

If the backend returns missing or malformed policy fields, the UI should normalize to safe defaults before rendering. Operators should not see JSON syntax errors because they are not editing JSON.

## Architecture

This is a frontend-first refinement that uses existing backend DTOs:

- Store new link-path fields inside existing connection `metadata`.
- Keep OpenAPI route contracts stable.
- Add frontend helpers in `frontend/src/components/link/types.ts` to avoid duplicating API DTOs.
- Keep backend validation minimal and core-neutral by validating policy shape in `LinkService.put_policy` / `aput_policy`.
- Do not add migrations in this iteration.

Future integrations can add provider/controller adapters later by writing target/probe/status data through existing core link APIs.

## Testing

Use TDD.

Backend tests:

- default policy includes the new budget behavior flags.
- `put_policy` rejects invalid priority lane names and invalid backpressure lanes.
- valid policy persists unchanged.

Frontend tests:

- Add link path can save a provider-managed SD-WAN overlay with provider, external reference, visibility, and one HTTPS monitoring target.
- Add link path can save inventory-only with no targets.
- Existing link paths render model, visibility, provider/reference, and target count.
- Policy controls save a generated policy object without exposing a JSON editor.
- Lane priority move controls update the saved order.

Verification:

- targeted backend link tests
- targeted frontend Link page tests
- frontend lint and build

## Scope Boundaries

In scope:

- UI copy and controls for logical link paths.
- Metadata-backed monitoring target rows.
- Field-based policy controls.
- Backend policy shape validation.

Out of scope:

- Real network probing runtime.
- SD-WAN/controller API integrations.
- Secrets/credentials for network devices.
- Automatic discovery of underlay paths.
- New tables or migrations.
- Changing passport hash semantics beyond naturally including existing connection metadata if already serialized.

## Spec Self-Review

- No placeholders remain.
- The UI model is packless and does not introduce maritime or traffic nouns.
- The plan is narrow enough for one implementation pass.
- The distinction between logical path and real network integration is explicit.
