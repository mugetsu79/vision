# Production Configuration Hardening Design

Date: 2026-06-01
Status: Implemented locally; awaiting MacBook/Jetson smoke validation

## Product Goal

Make Control Plane -> Configuration production-grade: every visible option must
either change runtime behavior, be validated before use, or be visibly blocked
with a precise reason. Operators should be able to create, duplicate, bind,
unbind, test, delete, and inspect configuration profiles without guessing which
parts are real and which parts are still advisory.

The target operator promise is:

1. A saved profile is syntactically valid.
2. A tested profile has proved its required dependencies.
3. A bound profile resolves predictably by scope.
4. A runtime worker reports which profile hash it actually applied.
5. The UI explains mismatches, fallbacks, missing secrets, and unsupported
   services before the operator discovers them in Live or Operations.

## Current State

The existing shared configuration model is a strong foundation:

- `GET/POST/PATCH/DELETE /api/v1/configuration/profiles` manages profiles.
- `POST /api/v1/configuration/profiles/{profile_id}/test` validates profiles.
- `POST /api/v1/configuration/bindings` binds a profile to tenant, site,
  edge-node, or camera scope.
- `GET /api/v1/configuration/resolved` resolves every profile kind for a
  target using camera, edge-node, site, then tenant default precedence.
- Evidence storage, stream delivery, runtime selection, privacy policy, LLM
  provider, and operations mode all have schemas and UI controls.

The current risk is not persistence. The risk is operator trust:

- Evidence storage is close to end-to-end, but recording policy and privacy
  residency mismatches can still surprise operators.
- Transport profile settings resolve into stream metadata and base URLs, but
  protocol selection is not enforced consistently enough for every visible
  mode.
- Runtime selection affects passports and model admission, but selected artifact
  and fallback behavior are not explicit enough in the UI.
- Privacy policy affects capture/manifests, but retention needs a scheduled
  per-camera enforcement path.
- LLM provider resolves profile metadata and secrets, but policy drafting still
  relies on deterministic logic rather than real provider-backed assistance.
- Operations mode affects fleet lifecycle controls, but `push` mode must become
  a real supervisor delivery path or be blocked until the supporting service is
  available.

## Scope

In scope:

- Backend capability metadata for every configuration kind and field.
- Stronger profile validation, binding validation, delete impact previews, and
  unbinding.
- Worker/runtime contracts that include applied profile IDs, hashes, selection
  reasons, fallback reasons, and blocking errors.
- End-to-end enforcement for Evidence storage, Transport profile, Runtime
  selection, Privacy policy, LLM provider, and Operations mode.
- Configuration UI improvements for templates, inline validation, runtime
  impact, effective configuration, delete impact, and operator diagnostics.
- Tests that prove visible controls change runtime behavior.
- Documentation for operator setup, profile semantics, and known service
  prerequisites.

Out of scope:

- DeepStream runtime implementation.
- Kubernetes operator implementation.
- Replacing Keycloak.
- Generic remote shell features.
- Browser-driven arbitrary host command execution.
- Cloud multi-tenant billing or marketplace profile templates.

## Product Rules

### 1. No Silent Controls

No visible control may be a no-op. If a control is shown as editable, the
backend must accept it, validate it, and expose how it affects runtime. If the
runtime cannot support it, the UI must render it disabled with a specific
reason returned by the backend capability catalog.

### 2. Validation Before Binding

Profiles can be saved in `unvalidated` state, but binding a profile to a runtime
scope must require:

- `enabled: true`
- `validation_status: valid`
- required secrets present
- service prerequisites satisfied
- kind-specific compatibility checks satisfied

The backend remains the source of this rule. The frontend mirrors it for
responsiveness but does not own the rule.

### 3. Defaults Stay Safe

Each profile kind must always have exactly one enabled tenant default after
bootstrap. Deleting the active default is blocked unless the request names a
replacement default profile for the same kind.

### 4. Resolution Is Explainable

Effective configuration must show:

- winning scope
- winning target key
- profile name, slug, validation status, and config hash
- whether the profile is active, advisory, unsupported, or requires a service
- operator message for unresolved or blocked states
- runtime-applied hash when a worker has reported it

### 5. Runtime Reports Beat UI Optimism

The UI may show desired configuration, but it must distinguish desired from
applied. A worker is considered aligned only when its latest runtime report or
scene contract includes the same profile hash as the current resolved profile.

## Backend Design

### Configuration Capability Catalog

Extend `GET /api/v1/configuration/catalog` to return a capability model for each
configuration kind:

```json
{
  "kind": "operations_mode",
  "label": "Operations mode",
  "runtime_support": "active",
  "fields": [
    {
      "name": "supervisor_mode",
      "label": "Supervisor mode",
      "support": "active",
      "values": [
        { "value": "disabled", "support": "active" },
        { "value": "polling", "support": "active" },
        { "value": "push", "support": "requires_service", "requires": ["nats"] }
      ]
    }
  ]
}
```

Allowed support states:

- `active`: enforced by runtime now.
- `advisory`: recorded and reported, but cannot force runtime behavior alone.
- `requires_service`: enforced when named service prerequisites are healthy.
- `unsupported`: blocked for new profiles and bindings.

The catalog must be generated from backend runtime capability constants, not
hard-coded in the frontend.

### Profile CRUD And Impact

Add first-class impact and unbind behavior:

- `GET /api/v1/configuration/profiles/{profile_id}/impact`
  - returns direct bindings, targets affected by default fallback, secret
    presence, and whether the profile is a default.
- `DELETE /api/v1/configuration/profiles/{profile_id}`
  - blocks deleting the last enabled default for a kind unless a replacement is
    supplied.
  - deletes direct bindings only after returning an impact-aware confirmation
    path to the UI.
- `GET /api/v1/configuration/bindings`
  - lists bindings by kind, scope, and target.
- `DELETE /api/v1/configuration/bindings/{binding_id}`
  - removes one binding and causes normal fallback resolution.

All profile and binding changes must continue to audit:

- action
- actor
- profile kind
- profile ID
- target scope
- previous profile ID when replacing a binding
- replacement default when deleting a default

### Binding Validation

Binding must fail with precise messages when:

- the target does not exist or belongs to another tenant
- the profile kind does not match the binding kind
- the profile is disabled, invalid, missing secrets, or unsupported
- evidence storage and privacy residency conflict for the same resolved target
- operations mode selects an edge supervisor without an edge node assignment
- operations mode selects central supervisor when central supervisor service is
  not installed or unhealthy
- transport mode requires a stream service URL that is missing
- runtime selection disallows fallback and no compatible artifact exists
- LLM provider requires an API key but none is stored

### Applied Configuration Reporting

Worker config, scene contract snapshots, runtime passports, and runtime reports
must carry applied configuration summaries:

```json
{
  "configuration": {
    "evidence_storage": { "profile_id": "...", "profile_hash": "..." },
    "stream_delivery": { "profile_id": "...", "profile_hash": "..." },
    "runtime_selection": {
      "profile_id": "...",
      "profile_hash": "...",
      "selected_backend": "tensorrt_engine",
      "selected_artifact_id": "...",
      "fallback_reason": null
    },
    "privacy_policy": { "profile_id": "...", "profile_hash": "..." },
    "operations_mode": { "profile_id": "...", "profile_hash": "..." }
  }
}
```

This gives Operations and Live enough data to show desired/applied alignment.

## Configuration Kind Design

### Evidence Storage

Evidence storage remains a real runtime profile and becomes stricter:

- `local_filesystem`, `minio`, `s3_compatible`, and `local_first` remain
  supported.
- Testing local storage checks path writability from the responsible node.
- Testing MinIO/S3 performs bucket access with stored credentials.
- Binding validates compatibility with the target camera recording policy.
- Recording policy UI must show the resolved evidence profile and block storage
  profile combinations that would fail at runtime.
- Local-first profiles expose local path, remote profile, sync status, and last
  failed sync reason.

Acceptance evidence:

- Worker config includes resolved evidence profile ID/hash.
- Incident capture stores artifacts through the resolved route.
- Mismatched recording policy and storage profile fail before worker start.

### Transport Profile

Transport profile becomes a stream route profile, not a mixed route/rendition
control.

Visible route modes:

- `native`: use the best source-aware browser route exposed by the backend.
- `webrtc`: force WebRTC/WHEP route and require WebRTC service readiness.
- `hls`: force HLS route and require playlist/resource readiness.
- `mjpeg`: force MJPEG proxy route and require proxy readiness.

The existing `transcode` delivery mode is migrated out of the route selector.
Transcoding belongs to camera live rendition profiles, such as `1080p25`,
`720p10`, `540p5`, or `annotated`. The backend continues reading historical
`delivery_mode: "transcode"` values by normalizing them to:

- route mode: `native`
- rendition requirement: transcode profile selected by camera browser delivery

New profiles cannot save `delivery_mode: "transcode"` as a route mode. The UI
shows a migration note for old profiles and offers one-click normalization.

Acceptance evidence:

- Live stream URLs and player choice follow resolved route mode.
- HLS and MJPEG modes fail validation when required backend settings are absent.
- Rendition changes continue to affect output resolution/fps independently of
  route mode.

### Runtime Selection

Runtime selection becomes enforceable selection policy:

- `preferred_backend` constrains backend ranking.
- `artifact_preference` chooses artifact ranking:
  - `tensorrt_first`
  - `onnx_first`
  - `dynamic_first`
- `fallback_allowed: false` blocks worker config when no compatible artifact or
  backend is available.
- Runtime passports report selected backend, selected artifact, target profile,
  precision, and fallback reason.
- Model admission uses the selected backend and returns a blocking status when
  fallback is disabled and the selected path is unavailable.

Acceptance evidence:

- Worker config changes when profile backend preference changes.
- Operations shows selected backend/artifact and fallback reason.
- A no-fallback profile blocks unsupported targets before worker start.

### Privacy Policy

Privacy policy becomes fully enforced:

- Residency is validated against resolved evidence storage and recording
  policy.
- Plaintext plate storage controls incident payload behavior and privacy
  manifest content.
- Storage quota controls capture acceptance per policy, not only tenant default.
- Retention is enforced by a backend retention job that resolves privacy policy
  per artifact camera and expires artifacts in bounded batches.

Retention job behavior:

- runs on startup-enabled backend service interval
- groups candidate artifacts by tenant and camera
- resolves privacy policy for each camera
- marks artifacts older than that camera policy as expired
- writes evidence ledger entries
- exposes metrics for scanned, expired, skipped, and failed artifacts

Acceptance evidence:

- Artifacts expire according to the camera-resolved privacy policy.
- Different cameras in the same tenant can have different retention periods.
- The UI shows last retention run and any errors in Configuration diagnostics.

### LLM Provider

LLM provider becomes real provider-backed policy assistance while retaining the
deterministic compiler as a safety layer.

Backend service design:

- `LLMProviderClient` interface with an OpenAI-compatible HTTP adapter.
- Provider profile supplies provider name, model, base URL, API key requirement,
  and stored API key.
- Profile test performs a lightweight model/API authentication check when
  secrets are present.
- Policy draft creation calls the provider when `use_llm: true`.
- Provider output must be parsed into the existing structured draft shape and
  validated before it can affect a policy.
- If provider output is malformed, the request returns a warning and falls back
  to deterministic drafting only when the operator allows fallback.

The UI must label the result:

- `provider_assisted`
- `deterministic_fallback`
- `provider_unavailable`
- `provider_rejected`

Acceptance evidence:

- Mock provider tests prove the LLM profile is used for policy drafting.
- Missing API key blocks provider-assisted draft requests.
- Malformed provider output cannot apply unvalidated policy changes.

### Operations Mode

Operations mode becomes a true lifecycle policy:

- `manual`
  - no API lifecycle actions
  - UI shows manual run instructions only for development targets
- `central_supervisor`
  - actions are enabled only when central supervisor service is healthy
  - requests are routed to central supervisor
- `edge_supervisor`
  - actions are enabled only when the scene has an assigned edge node and that
    edge supervisor is healthy
  - requests are routed to the assigned edge supervisor

Supervisor mode semantics:

- `disabled`: no lifecycle requests are accepted.
- `polling`: supervisor polls the API for lifecycle requests.
- `push`: backend publishes lifecycle requests over NATS to the supervisor
  subject and requires supervisor acknowledgements.

Restart policy semantics:

- `never`: supervisor does not restart stopped workers automatically.
- `on_failure`: supervisor restarts failed workers within configured retry
  limits.
- `always`: supervisor reconciles desired workers after supervisor restart and
  after unexpected worker exit.

Profile test validates required services:

- `polling` requires API reachability from supervisor.
- `push` requires NATS enabled, supervisor subscription health, and an
  acknowledgement timeout setting.
- `edge_supervisor` requires the selected target to have an edge node.

Acceptance evidence:

- Push mode creates a NATS lifecycle message and records acknowledgement.
- Polling mode continues to work without NATS push.
- Restart policy differences are covered by supervisor tests.
- Operations shows why lifecycle buttons are disabled.

## UX Design

### Configuration Overview

Keep the existing tabbed configuration workspace, but add compact readiness
signals per tab:

- total profiles
- valid profiles
- invalid profiles
- default profile
- bindings count
- unsupported fields count

Each tab starts with a short operational summary:

- what this profile kind controls
- what service prerequisites it has
- where the setting is applied

This text must be compact and operational, not marketing copy.

### Profile List

The left rail becomes a profile inventory:

- profile name
- slug
- default badge
- validation badge
- enabled/disabled state
- binding count
- last tested timestamp
- applied drift count when known

Actions:

- create from template
- duplicate
- make default
- test
- delete

Delete opens an impact dialog that lists direct bindings, default fallback
impact, and replacement-default requirement.

### Profile Editor

The editor uses progressive disclosure:

- identity fields first
- kind-specific controls second
- secrets third
- runtime impact side panel last

Every input has:

- visible label
- inline validation on blur
- required indication when applicable
- helper text only when it prevents a mistake
- loading/success/error state for save and test

The runtime impact panel shows:

- affected runtime contract fields
- service prerequisites
- secrets state
- known target incompatibilities
- whether the profile can be bound now

### Binding Manager

Bindings get their own clear table instead of only a one-row form:

- kind
- scope
- target
- profile
- validation state
- winner status for selected effective target
- unbind action

The bind form remains available, but it previews the resolution impact before
submitting:

- "This camera will use profile X directly."
- "This site binding will affect N cameras unless overridden."
- "This tenant default will affect targets without camera/site/edge overrides."

### Effective Configuration

Effective configuration becomes the trust center:

- target selector grouped by tenant, site, edge node, camera
- row per profile kind
- desired profile
- winning scope
- validation state
- runtime support state
- applied profile hash when reported
- drift or aligned status
- fallback and operator message

Rows include quick actions:

- open profile
- test profile
- bind replacement
- copy diagnostic JSON

### Operations Mode UX

Operations mode gets templates:

- Manual development
- Edge supervisor polling
- Central supervisor polling
- Edge supervisor push
- Central supervisor push

Push templates are disabled until backend capability catalog reports NATS push
support as available. Disabled templates explain the missing service.

Operators can create multiple operation modes. The UI must never imply there is
only one operation profile per tenant. Binding decides which scene, site, edge,
or tenant uses each profile.

## Data And Migration

Migration steps:

1. Backfill missing tenant defaults per profile kind.
2. Add binding list/delete support without changing existing binding rows.
3. Add capability catalog fields without breaking old frontend clients.
4. Normalize historical stream profiles with `delivery_mode: "transcode"` by
   keeping them readable and marking them `requires_normalization`.
5. Add applied configuration payloads to worker reports while accepting older
   reports that do not include them.
6. Add retention job tables or metrics fields without changing existing evidence
   artifact identity.

No operator data is hard-deleted by migration.

## Testing Strategy

Backend tests:

- profile create/update/delete/default protection
- binding create/list/delete and scope precedence
- profile impact responses
- evidence storage route validation
- transport route validation and legacy transcode normalization
- runtime backend/artifact selection and no-fallback blocking
- privacy retention per camera
- LLM provider client success, missing secret, malformed response, fallback
- operations polling, push, restart policies, and disabled action reasons

Frontend tests:

- profile templates and duplicate flow
- inline validation and async save/test feedback
- binding table, unbind, and impact preview
- effective configuration aligned/drift/unresolved states
- delete impact dialog and replacement default requirement
- disabled unsupported controls from capability catalog
- operations mode multi-profile creation and binding

End-to-end checks:

- create profile, test it, bind it, observe effective configuration
- start worker and confirm applied hash alignment
- switch runtime selection and observe fallback/no-fallback behavior
- set privacy retention to a short interval and confirm expiration
- configure HLS/MJPEG/WebRTC route modes and verify player route selection
- configure LLM provider with mocked provider and confirm assisted policy draft
- configure push operations mode and confirm NATS acknowledgement

## Rollout Plan

### Phase 1: Truth Model And UX Backbone

Add capability catalog, binding list/delete, impact preview, default deletion
protection, and effective configuration desired/applied states.

### Phase 2: Evidence And Privacy Hardening

Tighten evidence/recording/privacy compatibility and add per-camera retention
enforcement.

### Phase 3: Transport Enforcement

Make route modes drive stream access, normalize legacy transcode route profiles,
and keep live rendition separate from route mode.

### Phase 4: Runtime Selection Enforcement

Make backend/artifact selection deterministic, expose fallback reasons, and
block no-fallback profiles before worker start.

### Phase 5: LLM Provider Runtime

Add provider-backed policy assistance through a safe structured-output adapter.

### Phase 6: Operations Lifecycle Modes

Implement push supervisor delivery, acknowledgement tracking, and restart policy
tests; keep polling as the default production-safe mode.

### Phase 7: Visual QA, Documentation, And Operator Runbook

Polish layout, focus states, empty states, and diagnostics copy. Update the
operator deployment and MacBook test-build docs with configuration validation
steps.

## Execution Recommendation

Use a hybrid execution model:

- Phase 1 should be sequential because it changes shared contracts used by all
  tabs.
- Phases 2 through 6 can use subagents with disjoint ownership after Phase 1 is
  merged in the working branch.
- Each phase should land with backend tests, frontend tests, generated API types
  when schemas change, and one focused manual verification note.

Recommended phase ownership:

- Shared contracts and UX shell: one engineer.
- Evidence/privacy: one backend-focused engineer plus frontend follow-up.
- Transport: one backend/streaming engineer plus Live UI verification.
- Runtime selection: one backend/runtime engineer.
- LLM provider: one backend policy engineer.
- Operations modes: one supervisor/backend engineer plus Operations UI
  verification.

## Success Criteria

The work is complete when:

- every visible field in Configuration has a backend capability state
- invalid or unsupported profiles cannot be bound
- every profile kind has tests proving runtime effect or explicit blocking
- effective configuration distinguishes desired and applied profile hashes
- transport route mode changes stream route behavior
- privacy retention runs automatically per camera policy
- LLM provider can perform provider-backed policy assistance through a safe
  validated adapter
- operations push mode has real delivery and acknowledgement behavior
- operators can delete, duplicate, bind, unbind, and inspect profiles without
  terminal checks
