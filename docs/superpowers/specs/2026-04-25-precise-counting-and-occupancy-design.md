# Precise Counting, Occupancy, and Count Events Design

> **Status:** Draft for review
>
> **Date:** 2026-04-25
>
> **Goal:** Replace ambiguous frame-based counting with a clear split between live occupancy and precise count events, while preserving multi-object tracking, speed measurement, and historical analytics.

---

## 1. Context

The current repo already supports:

- multi-object detection and tracking per frame
- concurrent tracking of multiple people, cars, or other classes
- live telemetry overlays
- history and series queries backed by `tracking_events`
- speed estimation derived from homography plus per-track history

Recent fixes removed the worst inflation bug where the same visible object could accumulate every frame into the live sparkline and history series. That mitigation is necessary, but it does not fully solve precise counting because it still depends on tracker identity durability.

The root issue is semantic, not just algorithmic:

- `tracking_events` describes **observations** of tracked objects over time
- operators sometimes need **occupancy**
- operators sometimes need **precise cumulative counts**

These are different metrics and should not be derived from one overloaded number.

---

## 2. Problem Statement

The current product mixes three different questions:

1. How many objects are visible right now?
2. How many unique tracked objects were observed during a window?
3. How many objects crossed an operational boundary such as a road line or zone boundary?

Only the third question is the right answer for precise traffic-style counting.

Examples:

- A child sitting in one room for 10 minutes should remain `1` in live occupancy.
- Three cars crossing a driveway line should count as `3` pass-by events even if each car is visible for many frames.
- Two parked cars visible for 20 minutes should contribute to occupancy, not inflate cumulative traffic count.

Using free-running `track_id` aggregation alone is not sufficient for precise counts because track IDs can churn under occlusion, low FPS, partial exits, or confidence drops.

---

## 3. Design Goals

1. Make live numbers stable and intuitive.
2. Make pass-by counts operationally meaningful for cars, people, and other supported classes.
3. Preserve support for multiple simultaneous tracked objects.
4. Keep speed estimation intact.
5. Preserve `tracking_events` for trajectory, dwell, attributes, and debugging.
6. Avoid a giant redesign of the whole vision stack.

### Non-goals

- Perfect long-horizon identity persistence across arbitrary occlusion
- Cross-camera re-identification in this change
- Replacing the existing tracker implementation
- Removing `tracking_events`

---

## 4. Metric Model

The system should explicitly support three metrics.

### 4.1 Occupancy

**Definition:** the number of active tracked objects currently present in the scene or in a zone.

Use cases:

- live wall
- queue length
- room occupancy
- loading bay occupancy
- “how many vehicles are visible now?”

**Backend metric name:** `occupancy`

This is still the right technical name even for cars, because it means “currently present.” However, the UI should not always expose that raw term.

**UI labeling rule:**

- generic live tile label: `visible now`
- vehicle-only views: `active vehicles`
- mixed-class views: `visible objects`

This keeps the backend/API vocabulary consistent while making operator language natural.

### 4.2 Count Events

**Definition:** discrete operational events generated when an object crosses or transitions through a configured boundary.

Supported event types in this design:

- `line_cross`
- `zone_enter`
- `zone_exit`

Use cases:

- cars passing a road marker
- people entering or leaving a room
- forklifts entering a restricted area
- retail entrance footfall

**Backend metric name:** `count_events`

This is the primary metric for precise cumulative counting.

### 4.3 Observations

**Definition:** raw or near-raw track observations over time, derived from `tracking_events`.

Use cases:

- debugging tracker behavior
- trajectory analysis
- dwell analytics
- attribute analytics
- speed analytics

**Backend metric name:** `observations`

This metric remains important, but it is not the source of truth for precise pass-by counting.

---

## 5. Product Semantics

### 5.1 Live

The live page should be occupancy-first.

- Tile subtitle continues to show worker/profile state.
- The existing “visible detections” label should become occupancy-oriented.
- The per-camera sparkline should represent occupancy over the last 30 minutes, not cumulative detections.
- Right-edge sparkline totals should show a meaningful occupancy-derived value:
  - either latest bucket occupancy
  - or max occupancy in the 30-minute window

Recommended choice: **latest bucket occupancy**, because it aligns with “visible now.”

### 5.2 History

History must let the operator select which metric they are viewing.

Recommended modes:

- `Count events`
- `Occupancy`
- `Observations` (advanced/debug)

Recommended default:

- if the selected camera set includes at least one configured count boundary, default the History view to `Count events`
- otherwise default to `Occupancy`

This keeps the product intuitive for traffic-style cameras without removing general-purpose analytics.

### 5.3 Speed

Speed measurement stays enabled.

- The worker still computes speed from homography plus track history.
- `tracking_events.speed_kph` remains available.
- `count_events` should copy the current event-time speed into the event row when available.

This means traffic cameras can still answer:

- how many cars passed
- how fast they were going
- how many exceeded a threshold

Count precision and speed measurement are related operationally, but they must be stored separately.

---

## 6. Backend Design

### 6.1 Existing Tables

Keep `tracking_events` as the time-series table for object observations.

Do not reinterpret it again as the precise count source.

### 6.2 New Table: `count_events`

Add a new durable event table.

Proposed logical schema:

```sql
count_events(
  id uuid primary key,
  ts timestamptz not null,
  camera_id uuid not null references cameras(id),
  class_name text not null,
  track_id integer,
  event_type text not null,          -- line_cross | zone_enter | zone_exit
  boundary_id text not null,         -- line id or zone id
  direction text,                    -- null for non-line events
  from_zone_id text,
  to_zone_id text,
  speed_kph double precision,
  confidence double precision,
  attributes jsonb,
  payload jsonb not null default '{}'
)
```

Notes:

- `track_id` is kept for debugging and correlation, not as the event identity.
- `boundary_id` is required so counts can be segmented by line or zone.
- `payload` holds future-compatible metadata without forcing schema churn.

### 6.3 Aggregates

Add Timescale continuous aggregates for `count_events` analogous to history aggregates:

- `count_events_1m`
- `count_events_1h`

These support fast `/history` and `/history/series` queries for count-event mode.

`tracking_events` aggregates remain for occupancy/observation-oriented analytics.

---

## 7. Worker Pipeline Design

### 7.1 Current Order

Current worker order is effectively:

1. capture
2. preprocess
3. detect
4. track
5. speed
6. attributes
7. zones
8. rules / incidents
9. stream publish
10. telemetry publish
11. tracking persistence

### 7.2 New Count Event Stage

Insert a generic count-event processor after zone assignment and before persistence.

Updated order:

1. capture
2. preprocess
3. detect
4. track
5. speed
6. attributes
7. zones
8. **count events**
9. rules / incidents
10. stream publish
11. telemetry publish
12. tracking persistence
13. count-event persistence

### 7.3 Generic Count Event Processor

Create a worker-side processor responsible for:

- line crossing detection
- zone entry detection
- zone exit detection
- duplicate suppression for immediate churn

This processor should keep a bounded in-memory state keyed by:

- `track_id`
- current/previous zone
- current/previous side of each configured line

### 7.4 Line Crossing Logic

For a configured line:

- evaluate the tracked bottom-center point each frame
- compute which side of the line the point is on
- when the sign changes, emit a `line_cross` event
- include direction:
  - `positive_to_negative`
  - `negative_to_positive`

This is the right primitive for precise road traffic counting.

### 7.5 Zone Entry / Exit Logic

For polygon zones:

- compare the object’s previous zone assignment with the current one
- when `None -> zone`, emit `zone_enter`
- when `zone -> None`, emit `zone_exit`
- when `zone_a -> zone_b`, emit:
  - `zone_exit` for `zone_a`
  - `zone_enter` for `zone_b`

### 7.6 Churn Suppression

Track churn near a boundary can still cause false double counts if a new track ID is created immediately after a crossing.

This design includes a pragmatic suppression rule:

- per camera + boundary + class + approximate position + direction
- short cooldown window, e.g. 1-3 seconds

If a new event appears nearly identical to a just-emitted event, suppress it.

This is not a substitute for a better tracker, but it materially improves operational precision.

### 7.7 Relationship to ANPR

The current ANPR line-cross implementation should be refactored to build on top of the generic line-cross primitive rather than maintaining a separate crossing algorithm.

Recommended shape:

- generic line-cross processor emits a standard count event
- ANPR enrichment attaches plate-specific metadata where available

---

## 8. Configuration Model

Use existing `camera.zones` / line definitions instead of inventing a second configuration system.

### 8.1 Line Definitions

Extend line definitions to support counting explicitly:

```json
{
  "id": "road-westbound",
  "type": "line",
  "points": [[100, 300], [900, 300]],
  "class_names": ["car", "truck", "bus", "motorcycle"],
  "count_events": ["line_cross"]
}
```

Optional directional filtering may be added later, but it is not required for this phase.

### 8.2 Zone Definitions

Extend polygon zone definitions with entry/exit counting flags:

```json
{
  "id": "yard-a",
  "type": "polygon",
  "polygon": [[0,0], [100,0], [100,100], [0,100]],
  "class_names": ["person", "car"],
  "count_events": ["zone_enter", "zone_exit"]
}
```

This preserves the current JSON-driven configuration model.

---

## 9. API Design

### 9.1 History Metric Parameter

Add a `metric` query parameter to history endpoints.

Supported values:

- `occupancy`
- `count_events`
- `observations`

Affected endpoints:

- `GET /api/v1/history`
- `GET /api/v1/history/series`
- `GET /api/v1/history/classes`
- export route for history

### 9.2 Endpoint Semantics

#### `metric=occupancy`

- series values describe active visible objects per bucket
- optimized for live-adjacent analysis

#### `metric=count_events`

- series values describe durable crossing / entry / exit events per bucket
- optimized for precise pass-by counts

#### `metric=observations`

- series values describe track observation density
- advanced/debug mode

### 9.3 Backward Compatibility

To avoid breaking current clients abruptly:

- default backend metric remains `occupancy` during the transition
- frontend History UI explicitly selects its preferred metric
- docs and labels make the distinction visible

---

## 10. Frontend Design

### 10.1 Live Tile

Current live tile language should move from “detections” toward presence.

Recommended text:

- `1 visible now`
- `3 active vehicles`
- `5 visible objects`

### 10.2 Live Sparkline

The sparkline becomes an occupancy chart, not a cumulative detector counter.

Rules:

- one object visible for 30 minutes should not create an ever-rising line
- simultaneous objects should raise occupancy appropriately
- the current-minute live merge should dedupe by `track_id` within the bucket

### 10.3 History Controls

Add a metric selector near the existing class/date controls:

- `Count events`
- `Occupancy`
- `Observations`

When the operator is on a traffic-style camera with lines configured, the default selection should be `Count events`.

### 10.4 Labels

Recommended chart labels:

- `Count events` for cumulative road/entry analytics
- `Visible now` or `Active vehicles` for occupancy
- `Observations` for advanced/debug mode

---

## 11. Speed Semantics

Speed remains independent from counting mode.

Worker behavior remains:

- maintain short per-track history
- compute speed from homography and elapsed motion

Storage behavior becomes:

- `tracking_events.speed_kph` remains the detailed time-series source
- `count_events.speed_kph` stores the event-time speed snapshot when available

This supports future traffic queries such as:

- count vehicles crossing a line
- show median and p95 speed for those crossing events
- count speeding events above threshold

---

## 12. Testing Strategy

### 12.1 Worker / Domain Tests

- line crossing emits exactly one event for one crossing
- zone enter emits once on boundary entry
- zone exit emits once on boundary exit
- two objects crossing simultaneously both produce events
- churn suppression prevents immediate duplicate boundary events
- speed is copied into count events when available

### 12.2 History Service Tests

- `metric=count_events` reads from `count_events` aggregates
- `metric=occupancy` reads occupancy-oriented aggregation path
- `metric=observations` reads observation path
- classes endpoint respects metric selection

### 12.3 Frontend Tests

- live sparkline remains flat for one stationary object
- live occupancy increases when multiple objects are visible concurrently
- history metric selector drives the right API param
- traffic cameras default to `Count events`

### 12.4 Real-Camera Validation

Validate at least these scenes:

- stationary person in room
- two people moving independently
- multiple cars crossing a configured line
- car pauses near boundary without being double-counted
- temporary occlusion near boundary

---

## 13. Rollout Plan

Phase 1:

- keep current overcount fix in place
- introduce `metric` semantics
- implement occupancy-oriented live behavior

Phase 2:

- add `count_events` table, persistence, and APIs
- add generic line and zone count events

Phase 3:

- wire History UI to metric selector
- make traffic-style cameras default to `Count events`
- update docs and operator language

Phase 4:

- expose tracker stability tuning
- evaluate stronger ReID-backed suppression as follow-on work if boundary churn remains materially visible after phases 1-3

---

## 14. Key Decisions

1. **Use `occupancy` as the backend metric name**, but prefer clearer operator-facing labels in the UI.
2. **Keep speed measurement enabled** and separate from counting semantics.
3. **Use `count_events` as the precise cumulative counting source** for cars, people, and other classes.
4. **Keep `tracking_events` as an observation table**, not the precise counting source.
5. **Support multiple simultaneous objects as a first-class scenario** in both occupancy and count events.

---

## 15. Expected User Outcomes

After this design is implemented:

- one child sitting still should remain `1 visible now`
- one parked car should remain occupancy, not inflate traffic count
- three cars passing a configured line should count as `3`
- multiple cars, people, or objects can be tracked simultaneously
- speed is still measured and can be attached to crossing events

This gives the product a consistent and explainable model:

- **Live answers presence**
- **Count events answer movement through boundaries**
- **Observations answer analytics/debugging**
