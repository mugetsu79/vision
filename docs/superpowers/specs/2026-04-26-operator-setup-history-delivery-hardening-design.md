# Operator Setup, History, Delivery, and Fleet Hardening Design

> **Status:** Partially implemented; setup hardening, source-aware delivery, History review, Fleet / Operations phase 1, Evidence Desk review queue, model catalog registration, and experimental open-vocab runtime support have landed
>
> **Date:** 2026-04-26
>
> **Goal:** Make camera setup, history review, browser delivery, and worker operations operator-grade by replacing raw implementation concepts with clear product workflows.

---

## 1. Context

The current repo has the underlying technical pieces for:

- camera setup and calibration
- live occupancy and count-event metrics
- MediaMTX-backed browser delivery
- edge registration and worker configuration
- history queries with multiple metrics
- persisted incident review state
- detector capability metadata, model catalog presets, and runtime vocabulary state

But several operator-facing surfaces still expose backend truth too directly:

- count boundaries are configured by typing raw coordinates
- history renders only populated buckets, which makes "no detections" ambiguous
- history has filters, but no real search workflow
- browser delivery options are hardcoded instead of derived from source capabilities
- the `Settings` page originally started as a placeholder while real operational concerns were scattered across docs and terminal flows
- manual worker startup in dev remains a bridge, but the Operations page now makes the desired production model explicit: UI desired state and lifecycle requests are reconciled by central or edge supervisors

These are no longer isolated bugs. Together they form one product hardening problem: the product needs stronger operator models for setup, historical review, browser delivery, and fleet operations.

---

## 2. Problem Statement

Today the product makes operators reason about concepts they should not need to hold in their heads:

1. pixel coordinates in the analytics frame
2. browser stream profiles versus analytics ingest
3. whether native/passthrough is actually valid for a camera
4. whether a history chart means "zero detections" or "missing bucket"
5. how to bootstrap and run workers outside a developer terminal

The result is confusion even when the underlying math or data is technically correct.

Examples from the current product behavior:

- A user can configure a line boundary only by typing `x1/y1/x2/y2`, without seeing what frame those values belong to.
- Hourly history is technically correct but can feel stale because the UI does not clearly explain bucket semantics.
- When there are no detections, the current series payload can simply omit buckets rather than showing explicit zeros.
- The browser delivery picker offers `1080p15` even when the native camera stream is only `1280x720`.
- The current `Settings` route does not help an operator understand or manage workers at all.
- In development, worker startup is still a shell-owned process, but the Operations page now emits copy/paste-safe commands that fetch the local dev token. This remains acceptable for debugging but is not the production control model.
- The Evidence Desk now reviews captured incidents with persisted pending/reviewed state. It does not record new footage by itself; incident clips are still captured in the worker pipeline.

---

## 3. Design Goals

1. Make boundary authoring visual, intuitive, and resilient to display size changes.
2. Make history windows feel alive and understandable, including explicit zero-detection periods.
3. Add real search affordances to history filters.
4. Make browser delivery options source-aware and truthful.
5. Restore a clear product story for native versus transcode delivery.
6. Keep the real fleet/operations surface current as the Settings route evolves.
7. Make production worker startup and runtime management an operator workflow through supervisor-backed desired state, not a terminal ritual.

### Non-goals

- Replacing the current vision pipeline architecture wholesale
- Building full infrastructure orchestration into the browser
- Replacing Helm, Compose, or host-level service managers
- Solving the true target-runtime open-vocabulary model backend in this design; that later landed in the model catalog/open-vocab runtime stream

---

## 4. Design Overview

This design should be implemented as one umbrella initiative with four tightly related tracks:

1. **Boundary Authoring UX**
2. **History Follow-Now, Zero-Bucket, and Search UX**
3. **Browser Delivery Capability and Native Truthfulness**
4. **Fleet Operations and Settings UX**

These are separate implementation tracks, but they should share one operator model:

- the product should present **stable concepts** such as analytics frame, live window, valid stream options, and worker health
- the product should stop leaking low-level implementation details such as raw pixel entry, hardcoded rendition catalogs, and ad-hoc shell commands
- production should be described as a Linux master plus supervisor-managed central/edge workers, with the iMac + Jetson path treated as lab/pilot validation

---

## 5. Boundary Authoring UX

### 5.1 Product Direction

Operators should not start by typing coordinates.

Boundary setup should be performed on a **frozen analytics frame** with direct manipulation:

- click-drag to create a line
- click vertices to create a polygon
- drag handles to refine
- rename boundaries inline
- choose class scope and direction in the form alongside the drawing surface

Raw numeric coordinates should still exist, but only in an `Advanced` disclosure.

### 5.2 Coordinate Model

The product should distinguish three coordinate spaces:

- **analytics frame**
- **browser stream**
- **browser tile**

Boundary meaning should be defined against the **analytics frame** only.

However, boundaries should not be persisted as naked absolute pixels. They should be stored as **normalized coordinates** relative to the analytics frame dimensions.

Benefits:

- robust rendering at any browser size
- clearer migration when browser stream profiles change
- safer re-projection when the source remains the same aspect ratio

When aspect ratio changes, the UI should not silently trust old boundaries. It should show a review state such as:

- `Boundary alignment needs review after source aspect change`

### 5.3 Setup Experience

The setup panel should show:

- `Analytics frame: 1280×720`
- `Browser stream: 960×540`
- `Source aspect: 16:9`

The wording matters. This is where the product explains why a drawn boundary stays stable even if the browser stream changes.

### 5.4 Test Mode

Boundary setup should include a `Test boundary` mode:

- for lines:
  - current side
  - configured direction mode
  - last crossing direction
  - event count in the last 60 seconds
- for polygons:
  - inside/outside state
  - last enter/exit event
  - event count in the last 60 seconds

This is the fastest way for operators to validate whether a boundary is behaving correctly.

### 5.5 Direction And Scope

Lines should support:

- `both directions`
- `A → B only`
- `B → A only`

Polygons should support class scope in the UI, not just implicitly count all tracked classes.

This is especially important for rooms or mixed scenes where `person` is the only desired class for testing.

---

## 6. History Follow-Now, Zero-Bucket, and Search UX

### 6.1 Time Window Modes

History should support two explicit time modes:

- **Relative live window**
  - examples: `Last 15m`, `Last 1h`, `Last 24h`, `Last 7d`
  - auto-following
  - auto-refreshing
- **Absolute window**
  - explicit from/to timestamps
  - no auto-follow

When in relative mode, the UI should show:

- `Following now`

When in absolute mode, the UI should show:

- `Absolute window`
- `Resume live window`

### 6.2 Bucket Semantics

The UI should explain coarse buckets clearly.

For example, when granularity is `1 hour`, the chart should make it obvious that:

- the displayed timestamp is the bucket start
- the active bucket spans a full hour

Recommended helper copy:

- `Hourly buckets`
- `Current bucket: 14:00–14:59`

This removes false interpretations that the chart is frozen when it is merely coarsely bucketed.

### 6.3 Explicit Zero Buckets

The backend should materialize the requested bucket range even when there are no detections.

Today the result rows are built only from populated buckets. That makes a silent hole ambiguous:

- no detections
- no worker
- no data

The product should distinguish these cases by returning explicit zero rows for the requested window when the query is valid but no events exist.

That means:

- occupancy with an empty room should render a flat zero line
- count-events with no crossings should render a flat zero line
- observations with no worker data should still render zeros for the bucket range if the requested range is valid and data absence is expected

If the system truly lacks coverage for the window, that should be a separate status, not inferred from sparse rows.

### 6.4 Empty-State Semantics

History should support three distinct visual states:

1. **Zero detections**
   - valid query
   - explicit zero buckets
   - chart visible, flat at zero
2. **No configured scope**
   - no camera/class selection where required
3. **No data available / ingestion gap**
   - worker offline, source unavailable, or telemetry gap

These should not collapse into one generic empty state.

### 6.5 Search

History should gain a real search affordance.

Recommended scope:

- search cameras by name
- search classes by label
- search count boundaries by boundary id when viewing `count_events`

Recommended UX:

- one omnibox with typeahead
- filter chips for selected matches
- sidebar lists narrow live as the user types

This is much faster than manually scanning long multi-selects.

---

## 7. Browser Delivery Capability and Native Truthfulness

### 7.1 Source-Aware Delivery

Browser delivery options should not be hardcoded independently of source capability.

The system should probe and persist source facts such as:

- source width
- source height
- source fps
- source codec
- source aspect ratio

From those facts, the UI should derive valid delivery profiles.

### 7.2 Valid Profile Rules

The UI should never offer a transcode profile that upscales above the source as if it were a meaningful choice.

Example:

- if source is `1280×720`
- `1080p15` should not be shown as an available browser profile

The profile picker should separate:

- **native browser path**
- **valid renditions**
- **unsupported renditions**

If unsupported profiles are shown at all, they should be disabled with a reason.

### 7.3 Native Versus Browser Delivery

The product should explain the difference between:

- analytics ingest
- browser native stream
- browser transcode stream

The current language around `native` is too overloaded.

Recommended operator framing:

- `Analytics ingest`
  - what the worker actually reads
- `Browser native`
  - raw passthrough surface when allowed
- `Browser rendition`
  - derived stream for viewing efficiency

### 7.4 Native Availability

The UI should show why native is or is not currently available:

- privacy filtering disables raw passthrough
- source capability incompatible
- relay/native path degraded
- worker mode currently processed-only

This becomes particularly important because the repo has already seen regressions where the native path drifted from its intended behavior.

---

## 8. Fleet Operations and Settings UX

### 8.1 Replace the Placeholder

The `Settings` route has stopped being a placeholder and is now the home of operator-visible runtime and fleet concerns.

This should not be a junk drawer. It should be a deliberate **Fleet / Operations** surface.

### 8.2 Product Model

The UI should manage:

- desired worker assignment
- bootstrap actions
- health visibility
- capability reporting
- delivery/runtime diagnostics

The UI should not directly become a shell runner.

For local development, the UI may show copyable commands because no local supervisor owns worker processes yet. Those commands are a development bridge. They should not become the production lifecycle model.

### 8.3 Central And Edge Story

In production, workers should be managed by infrastructure:

- systemd
- container runtime
- Kubernetes
- edge service manager

The UI’s role is:

- create bootstrap material
- establish desired state
- show actual state
- expose safe administrative actions

It should not ask operators to mint a bearer token and run a long shell command by hand.

The Operations page now emits copy/paste-safe local dev commands that fetch a local development token automatically. Those commands remain a developer/lab fallback only.

The intended production flow is:

```text
UI lifecycle button
  -> backend desired-state or lifecycle request
  -> central or edge supervisor reconciles the worker process
  -> worker reports heartbeat, metrics, and last error
  -> UI shows desired state versus actual runtime state
```

The backend API must not directly shell out to the host. That would couple lifecycle to the backend container, bypass edge placement, and create a remote-command-execution surface.

### 8.4 Edge Bootstrap

For edge nodes, the UI should support:

- generate short-lived bootstrap token / install command
- register node
- show heartbeat and runtime profile
- show assigned cameras
- show health and last-seen status

The underlying edge registration flow already exists in the backend. The product surface needs to expose it coherently.

### 8.5 Central Worker Operations

For central workers, the product should expose:

- running / degraded / offline state
- assigned cameras
- current runtime profile
- current stream mode
- recent worker errors
- restart / drain / reassign actions when applicable

This becomes the real operator answer to "how does the worker start in prod?"

The product answer should be:

- workers are managed services
- the UI manages intent, bootstrap, assignment, and health

### 8.6 Settings Information Architecture

Recommended top-level sections:

- `Fleet`
  - central nodes
  - edge nodes
  - health and heartbeat
- `Workers`
  - assignments
  - runtime capabilities
  - status
- `Delivery`
  - source capability
  - native availability
  - valid browser profiles
- `Platform`
  - actual configuration settings that belong in settings

This gives the route a real product purpose.

---

## 9. Data And API Implications

### 9.1 Boundaries

Persist normalized boundary coordinates plus the analytics-frame dimensions they were authored against.

The backend should still be able to materialize worker-ready analytics-frame coordinates, but the product contract should no longer require the operator to think in raw pixels.

### 9.2 History Series

`HistorySeriesResponse` should be able to represent complete bucket ranges, not just sparse populated rows.

That means the backend service should materialize missing buckets with zeros before returning the response.

The response may also need lightweight metadata such as:

- window mode
- bucket start/end semantics
- coverage status

### 9.3 Source Capability

Camera/domain contracts should include discovered source capability metadata that can be used by:

- camera setup UI
- delivery picker
- fleet diagnostics

### 9.4 Worker/Fleet State

The settings/fleet UI will need operator-facing state for:

- node registration status
- worker heartbeats
- runtime profile
- camera assignment
- bootstrap/install metadata

This should build on existing edge and worker-config contracts rather than inventing a parallel control plane.

---

## 10. Success Criteria

The initiative is successful when all of the following are true:

- Operators configure lines and polygons visually on a frozen analytics frame instead of typing raw pixels by default.
- Boundaries stay aligned across browser display sizes and profile changes.
- History can clearly show zero detections instead of silently omitting buckets.
- Relative history windows visibly follow now and explain coarse-bucket semantics.
- History has a real search affordance for cameras, classes, and count boundaries.
- Browser delivery profiles are constrained by real source capability, so `1080p15` is not offered above a `720p` source.
- The product clearly explains native versus transcode versus analytics ingest.
- The `Settings` route remains a real fleet/operations surface.
- Operators can bootstrap and inspect workers from the UI now, with production lifecycle management moving toward supervisor-backed Start/Stop/Restart/Drain controls.
- Local dev worker commands are copy/paste-safe and fetch the local dev token, but they remain a lab fallback rather than the primary production workflow.

---

## 11. Recommended Delivery Sequence

Although this is one umbrella design, implementation should be split into tracks:

1. Boundary authoring UX and normalized boundary model
2. History follow-now, zero-bucket rendering, and search
3. Source capability discovery and truthful browser delivery options
4. Fleet/operations surface replacing the placeholder settings page

This sequence reduces risk because each track produces a user-visible improvement without waiting for the full umbrella to land.
