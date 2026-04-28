# Evidence Desk Review Queue Design

**Date:** 2026-04-28
**Status:** Implemented on `codex/source-aware-delivery-calibration-fixes`
**Scope:** Task 8 refinement for the open-vocab hybrid detector track. This spec replaces the narrow UI-only Task 8 interpretation with an evidence review queue that matches the current incident capture implementation.

## 0. Implementation Checkpoint

The Evidence Desk review queue has landed:

- `/incidents` defaults to pending incidents.
- operators can filter by camera, incident type, and review status.
- the UI shows a queue, selected evidence area, and Incident facts panel.
- clip-only incidents render an intentional evidence state when `snapshot_url` is null.
- operators can mark incidents reviewed and reopen reviewed incidents.
- review state persists in the database.
- review changes are audited in the same transaction as the review update.
- viewer users can read incidents; operator or higher is required to change review state.

Still not implemented by this task:

- new recording behavior
- still snapshot generation
- arbitrary forensic search over incident payload criteria
- assignments, comments, escalation, and case management

## 1. Goal

Redesign `/incidents` into an Evidence Desk that helps operators review captured incident records.

The page is not a new matching engine and does not create incidents. Matching and evidence capture already happen in the worker pipeline. The Evidence Desk is the operator workspace for reviewing the records that were already persisted.

## 2. Current Product Reality

The current backend captures incidents in the worker/inference path:

- `run_engine_for_camera` creates `IncidentClipCaptureService`.
- each processed frame is buffered for possible incident clips.
- rule events and ANPR line-crossing events can publish `incident.triggered.<camera_id>`.
- `IncidentClipCaptureService` collects pre/post frames, encodes an MJPEG clip, uploads it to object storage, and writes an `incidents` row.

The real evidence artifact today is primarily `clip_url`.

The schema and frontend already include `snapshot_url`, but `SQLIncidentRepository.create_incident` currently stores `snapshot_url=None`. Task 8 must therefore treat snapshots as optional. Snapshot generation is out of scope for this task.

## 3. Product Behavior

The Evidence Desk represents a captured incident review queue.

Default operator workflow:

1. The operator opens `/incidents`.
2. The page defaults to pending incidents.
3. The operator filters by camera, incident type, or review status.
4. The operator selects an incident from the queue.
5. The center panel shows the selected evidence artifact:
   - signed snapshot preview when `snapshot_url` exists
   - clip-only evidence state when no snapshot exists
6. The operator opens the signed clip when `clip_url` exists.
7. The operator marks the incident reviewed.
8. The persisted review state updates the queue and survives reloads.

The page should clearly communicate:

- "these are incidents Vezor already matched and captured"
- "review the evidence, open the signed clip, and clear the queue"

## 4. Non-Goals

Task 8 must not add:

- new live recording behavior
- new snapshot capture behavior
- forensic search over arbitrary payload criteria
- assignments, comments, escalation, or case management
- new rule authoring or incident matching UI
- broad documentation rewrites already completed in earlier operations/product docs work

Advanced filtering over payload fields can be a later feature once the incident review loop is honest and persisted.

## 5. Backend Design

Add lean persisted review state to incidents.

### 5.1 Schema

Add columns to `incidents`:

- `review_status`: `IncidentReviewStatus` enum, default `pending`
- `reviewed_at`: nullable timestamp
- `reviewed_by_subject`: nullable text

Allowed statuses:

- `pending`
- `reviewed`

Use `reviewed_by_subject` rather than a user foreign key for this first pass because request identity is already available as OIDC subject on `TenantContext.user`, while existing audit logging does not yet resolve actor IDs consistently.

Implement the enum consistently with existing model enums, using a database enum such as `incident_review_status_enum`.

### 5.2 API Contracts

Extend `IncidentResponse` with:

- `review_status`
- `reviewed_at`
- `reviewed_by_subject`

Extend `GET /api/v1/incidents` with optional `review_status`.

Add:

`PATCH /api/v1/incidents/{incident_id}/review`

Request:

```json
{
  "review_status": "reviewed"
}
```

The same endpoint can reopen an incident by setting:

```json
{
  "review_status": "pending"
}
```

Response: updated `IncidentResponse`.

Setting `review_status` to `reviewed` sets `reviewed_at` and `reviewed_by_subject`. Setting it to `pending` clears both fields. Submitting the current state is idempotent and returns the current incident without creating a duplicate audit entry.

### 5.3 Permissions And Tenant Safety

- `GET /api/v1/incidents` remains available to viewers and above.
- `PATCH /api/v1/incidents/{incident_id}/review` requires operator or above.
- Review updates must load the incident through camera/site tenant joins so one tenant cannot modify another tenant's incidents.

### 5.4 Audit

When review state changes, write an audit entry:

- action: `incident.review`
- target: `incident:<incident_id>`
- meta:
  - `review_status`
  - `previous_review_status`
  - `camera_id`
  - `incident_type`
  - `user_subject`

## 6. Frontend Design

Implement the approved triage-first layout:

- left rail: `Queue`
- center: selected evidence hero
- right rail: `Incident facts`

### 6.1 Filters

Keep the current camera and incident type filters, and add review status:

- Pending
- Reviewed
- All

The UI defaults to Pending.

### 6.2 Queue

The queue lists incidents using compact, scannable rows:

- camera name
- incident type
- relative or localized timestamp
- review status
- selected state

Selecting a row updates the hero and facts panel. When filters change, the selected incident should remain selected if still present, otherwise fall back to the first returned incident.

### 6.3 Evidence Hero

The hero panel prioritizes evidence:

- if `snapshot_url` exists, render the image with accessible alt text
- if no `snapshot_url` exists, render a clip-only evidence state explaining that this incident has recorded clip evidence but no still preview
- show `Open clip` when `clip_url` exists
- show a storage/quota status derived from `storage_bytes` and payload flags
- show `Review` for pending incidents and `Reopen` for reviewed incidents

The visual hierarchy should make `Open clip` feel like the real current evidence action.

### 6.4 Incident Facts

The facts panel shows:

- camera
- incident type
- timestamp
- review status
- reviewed at / reviewed by when available
- storage secured
- payload key/value facts

Payload rendering remains generic because open-vocab and rule-driven incidents may include different fields.

## 7. Error Handling

- Loading state: keep a stable desk shell with a concise loading message.
- Empty state: explain that no incidents match the selected filters.
- Missing snapshot: show clip-only evidence state, not a broken preview.
- Missing clip: show that no clip is available, using payload/storage quota details when present.
- Review mutation failure: keep the selected incident in place and show an inline error near the action.
- Permission failure: if the API returns 403, keep the incident readable and explain that operator access is required to change review state.

## 8. Testing

Backend tests:

- incident response includes review fields
- list filter supports `review_status`
- review endpoint persists `reviewed` state
- review endpoint can reopen to `pending`
- endpoint enforces tenant scoping
- endpoint requires operator or above
- audit entry is written when state changes

Frontend tests:

- renders queue, evidence hero, `Incident facts`, and `Open clip`
- renders clip-only state when `snapshot_url` is null
- defaults to pending review status
- changing filters refetches incidents with expected query params
- clicking Review calls the review endpoint and refreshes the queue
- reviewed incidents show Reopen when selected

Playwright:

- `/incidents` shows Queue, Incident facts, and Open clip
- selecting/reviewing an incident updates the visible state
- the route continues to work alongside the existing history assertions in `prompt9-history-and-incidents.spec.ts`

## 9. Implementation Plan Notes

The existing open-vocab implementation plan's Task 8 should be revised before implementation:

- keep the approved triage-first Evidence Desk layout
- add the persisted review state described here
- update the incident test data to cover clip-only evidence
- do not add snapshot capture
- do not redo completed README/design/product/runbook/playbook/lab guide docs unless a narrow contract note is needed for the new review endpoint

## 10. Open Questions

None for this task. The user approved:

- solution A triage-first layout
- Evidence Desk as a captured incident review queue
- persisted review state
- no new recording or snapshot capture in Task 8
