# Scene Vision Profile Configuration Guide

This guide explains how to configure OmniSight scenes with the current scene
vision profile, tracking stability, speed, calibration, event boundary, and
detection region settings.

It is written for operators and implementers. The first half focuses on the UI
workflow and field choices. The second half explains backend behavior, API
payloads, advanced tuning, and troubleshooting.

## What These Settings Control

A scene configuration answers five questions:

1. What source stream and model should the worker use?
2. What tracking posture should the scene use: fast, balanced, maximum accuracy,
   or open vocabulary?
3. Which compute tier should the system assume: low CPU, standard edge,
   advanced Jetson edge, or central GPU?
4. Should the scene compute calibrated speed, and therefore require homography?
5. Where should detection happen, and where should events be counted?

The important split is:

| Concept | Field | Purpose |
|---|---|---|
| Vision profile | `vision_profile` | Accuracy, compute, object domain, speed, and future verifier/tracker policy |
| Detection regions | `detection_regions` | Include or exclude detector candidates before tracking |
| Event boundaries | `zones` | Produce line crossing and zone enter/exit events |
| Homography | `homography` | Map image motion into real-world distance for speed |
| Browser delivery | `browser_delivery` | Choose operator-facing stream profile, independent of clean ingest |

The backend owns track truth. The frontend displays backend state; it should not
invent identity, visible counts, or speed. The worker uses the same stabilized
track state for telemetry and annotated overlays.

## Current UI Workflow

Scene setup has five steps.

### 1. Identity

Use this step to set:

- camera or scene name
- site
- processing mode
- RTSP URL

Processing mode describes where inference is expected to run:

| Mode | Use When |
|---|---|
| `central` | The master gateway has enough CPU/GPU and is reachable from the camera |
| `edge` | The camera is close to a capable edge node and bandwidth/privacy matter |
| `hybrid` | You want edge assistance with central coordination |

The RTSP URL is masked after save. In edit mode, leave the field empty to keep
the stored stream address.

### 2. Models And Tracking

Use this step to choose:

- primary model
- optional secondary model
- active classes
- tracker type
- runtime vocabulary for open-vocabulary models

For fixed-vocabulary models, active classes narrow the model inventory. If no
classes are checked, the scene keeps the full primary model inventory active.

For open-vocabulary models, active classes are cleared and runtime vocabulary is
used instead. Runtime vocabulary terms should be short, concrete labels such as
`forklift`, `pallet jack`, or `delivery van`.

Tracker type remains available as a field, but the current scene vision resolver
normalizes resolved profile tracking to BoT-SORT-ready behavior. Future runtime
work can map advanced edge and central GPU profiles to ReID or DeepStream/NvDCF
without changing the scene contract.

### 3. Privacy, Processing And Delivery

Use this step to configure:

- privacy blur settings
- frame skip and FPS cap
- vision profile
- compute target
- speed metrics
- browser delivery profile

The profile controls are compact by design. They choose the high-level posture;
the backend resolves the concrete tracking and candidate quality policy.

#### Vision Profile

| UI Label | API Value | Best For | Tradeoff |
|---|---|---|---|
| Fast | `fast` | constrained CPU, old iMac, low-end edge | Lowest latency, least extra stability work |
| Balanced | `balanced` | normal people/vehicle scenes | Default posture, good quality per compute |
| Maximum Accuracy | `maximum_accuracy` | occlusion, crowds, split bodies, traffic | More conservative, more compute |
| Open Vocabulary | `open_vocabulary` | custom text classes or discovery | More false-positive risk, needs careful terms |

#### Compute Target

| UI Label | API Value | Best For |
|---|---|---|
| Low CPU | `cpu_low` | old iMac, CPU-only mini PC, low power boxes |
| Standard Edge | `edge_standard` | good edge device, normal deployment default |
| Advanced Edge | `edge_advanced_jetson` | Jetson Orin Nano Super / Orin-class devices |
| Central GPU | `central_gpu` | master gateway GPU, multi-stage verification, heavier models |

The Jetson Orin Nano Super belongs in `edge_advanced_jetson`, not `cpu_low`.
The current implementation only stores and resolves this tier; it does not
reopen TensorRT, DeepStream, or RTSP runtime work.

#### Speed Metrics Toggle

Speed is explicit.

| Speed Toggle | Homography Requirement | Telemetry Behavior |
|---|---|---|
| Off | Not required | `speed_kph` remains `null` |
| On | Required | Worker computes `speed_kph` from calibrated track motion |

If speed is off, a scene can be created with no homography. If speed is on, the
wizard and backend require:

- four source points
- four destination points
- reference distance greater than zero

Note: `fast` on `cpu_low` may resolve speed off internally to protect latency.

### 4. Calibration

Calibration has three separate jobs:

1. Homography source/destination points for speed.
2. Event boundaries for event counting.
3. Detection regions for detector gating.

These must not be confused.

#### Homography

Homography maps image pixels into a real-world plane. Use it when you need
speed or other calibrated motion metrics.

Configure:

- four source points on the camera image
- four destination points on a top-down reference plane
- reference distance in meters

Guidance:

- Put source points on the same physical ground plane when possible.
- Use corners of a floor tile, lane markings, doorway, parking bay, or measured
  rectangle.
- Avoid points on walls, beds, screens, or furniture unless those are the
  actual movement plane.
- Recheck calibration when camera angle, lens, or stream resolution changes.

Speed is only meaningful when the moving object anchor stays on the calibrated
plane. For people and vehicles, the worker uses the bottom-center/footpoint
style anchor.

#### Event Boundaries

Event boundaries are stored in `zones`.

| Boundary Type | Use For | Emits |
|---|---|---|
| Line boundary | doorway crossings, lane crossing, entry/exit line | line crossing events |
| Polygon zone | room area, work cell, loading bay, restricted zone | zone enter/exit events |

Event boundaries do not decide whether a detection exists. They label and count
tracks after detection and tracking.

#### Detection Regions

Detection regions are stored in `detection_regions`. They gate candidates before
the tracker.

| Mode | Meaning | Use When |
|---|---|---|
| Include | Only candidates inside matching include regions are allowed | Road lane, walkway, doorway, shelf, loading bay |
| Exclude | Candidates inside matching exclusion regions are rejected | Bed/pillow false positives, mirrors, screens, vegetation, static clutter |

Detection regions may be scoped by class. Empty class scope means all active
classes.

Recommended pattern:

- Use include regions when the valid detection area is naturally bounded.
- Use exclusion regions when the whole frame is useful except for known bad
  islands.
- Use both when a bounded area has small false-positive pockets.

Detection region anchors:

| Object Family | Anchor |
|---|---|
| `person`, `car`, `truck`, `bus`, `motorcycle`, `bicycle`, `forklift` | bottom center |
| other classes | bounding-box center |

If at least one include region applies to a class, candidates for that class
must land inside one include region. Exclusion regions override inclusion.

### 5. Review

Review verifies the scene before save. The scene list also shows a compact
vision summary after save:

- accuracy mode, such as `Balanced` or `Max accuracy`
- compute tier, such as `Standard edge` or `Advanced edge`
- speed state, `Speed off` or `Speed on`

## Choosing The Right Profile

### Quick Decision Tree

Use this fast path first:

1. Is this running on an old CPU-only machine or overloaded edge node?
   Use `Fast` + `Low CPU`.
2. Is this a normal scene with one or a few people/vehicles?
   Use `Balanced` + `Standard Edge`.
3. Are there occlusions, crowds, seated people, laptop/body splits, or traffic?
   Use `Maximum Accuracy` + `Advanced Edge` or `Central GPU`.
4. Are you searching for custom classes not in the model inventory?
   Use `Open Vocabulary` and keep terms narrow.
5. Do you need speed?
   Turn speed on and complete homography. Otherwise leave speed off.

### Common Presets

#### Home/Lab Single Person

Use when testing in a room with one person, a bed, desk, chair, laptop, and
possible false-positive clutter.

Recommended:

```json
{
  "compute_tier": "edge_standard",
  "accuracy_mode": "balanced",
  "scene_difficulty": "cluttered",
  "object_domain": "people",
  "motion_metrics": { "speed_enabled": false }
}
```

Add:

- exclusion region over bed/pillow or static person-like shapes
- optional include region over the walkable floor
- event boundaries only if you need crossing or enter/exit events

If the detector splits a seated body because a laptop blocks the torso:

- try `Maximum Accuracy`
- keep duplicate suppression enabled
- add an exclusion region for known static false-positive surfaces
- avoid using open vocabulary for normal `person` tracking

#### Crowded Or Occluded People Scene

Use for shops, corridors, entrances, or workspaces with multiple people and
partial occlusion.

Recommended:

```json
{
  "compute_tier": "central_gpu",
  "accuracy_mode": "maximum_accuracy",
  "scene_difficulty": "crowded",
  "object_domain": "people",
  "motion_metrics": { "speed_enabled": false }
}
```

Add:

- include regions for walkways or active floor areas
- exclusion regions for posters, mirrors, screens, mannequins, vegetation, or
  person-like static objects
- line boundaries for entrance/exit counting

Use speed only when the floor plane is visible and calibrated.

#### Traffic Or Vehicle Scene

Use for roads, yards, parking areas, gates, and loading docks.

Recommended without speed:

```json
{
  "compute_tier": "edge_advanced_jetson",
  "accuracy_mode": "maximum_accuracy",
  "scene_difficulty": "traffic",
  "object_domain": "vehicles",
  "motion_metrics": { "speed_enabled": false }
}
```

Recommended with speed:

```json
{
  "compute_tier": "edge_advanced_jetson",
  "accuracy_mode": "maximum_accuracy",
  "scene_difficulty": "traffic",
  "object_domain": "vehicles",
  "motion_metrics": { "speed_enabled": true }
}
```

Add:

- include regions around lanes, driveway, or gate approach
- exclusion regions for parked vehicles if they trigger false positives
- homography from lane markings or measured ground points if speed is enabled
- line boundaries at gates or counting points

#### Warehouse Forklift / Loading Bay

Use for forklifts, pallet jacks, people, and vehicles in a warehouse.

Recommended:

```json
{
  "compute_tier": "edge_advanced_jetson",
  "accuracy_mode": "maximum_accuracy",
  "scene_difficulty": "occluded",
  "object_domain": "mixed",
  "motion_metrics": { "speed_enabled": false }
}
```

Add:

- class-scoped include regions for forklift paths
- exclusion regions for racks, reflective signs, static machinery
- line boundaries across bay doors or safety thresholds

If using an open-vocabulary model for `forklift` or `pallet jack`, use
`Open Vocabulary`, keep terms few, and consider stricter candidate confidence.

#### Old iMac Or CPU-Limited Edge

Use when average inference is already near the frame budget and stability must
not add much cost.

Recommended:

```json
{
  "compute_tier": "cpu_low",
  "accuracy_mode": "fast",
  "scene_difficulty": "open",
  "object_domain": "mixed",
  "motion_metrics": { "speed_enabled": false }
}
```

Add:

- include regions to reduce candidate load
- exclusion regions for obvious false-positive zones
- lower FPS cap or higher frame skip if needed

Avoid:

- speed unless absolutely required
- open vocabulary
- broad full-frame detection in cluttered scenes

#### Open Vocabulary Discovery

Use when the target is not part of the fixed model class list.

Recommended:

```json
{
  "compute_tier": "central_gpu",
  "accuracy_mode": "open_vocabulary",
  "scene_difficulty": "custom",
  "object_domain": "open_vocab",
  "motion_metrics": { "speed_enabled": false }
}
```

Guidance:

- use concrete nouns, not long phrases
- start with one to five terms
- use include regions to constrain where discoveries should happen
- expect more candidate noise than a fixed-vocabulary detector
- review telemetry before enabling count events

## Candidate Quality Gate

The candidate quality gate runs after visible class filtering and detection
region filtering, but before tracker update.

It is designed to avoid the common mistake of raising the detector threshold
globally. Low-score detections are still useful when they are near an existing
track, especially for slow motion, occlusion, and frame skips.

The gate can:

- reject low-confidence new candidates far from known tracks
- pass low-confidence detections that plausibly continue an active, tentative,
  or coasting same-class track
- suppress duplicate fragments near a stable same-class track
- keep detection regions and candidate decisions observable through metrics

Current important reasons:

| Reason | Meaning |
|---|---|
| `new_track_high_confidence` | Candidate is strong enough to start a new track |
| `new_track_low_confidence` | Candidate is too weak and not near an existing track |
| `existing_track_continuation` | Low-score candidate may continue a known track |
| `duplicate_fragment` | Candidate looks like a split fragment of an existing object |

### Advanced Candidate Quality JSON

Most operators should use the UI profile only. Advanced users can tune
`candidate_quality` through API payloads. The UI preserves these values in edit
mode.

Example:

```json
{
  "candidate_quality": {
    "new_track_min_confidence": {
      "person": 0.55,
      "car": 0.45,
      "default": 0.50
    },
    "duplicate_suppression_enabled": true,
    "memory_frames": 36
  }
}
```

Use cases:

- raise `person` confidence when pillows, posters, or furniture become people
- lower vehicle confidence only when the camera angle is stable and region
  gating is strong
- disable duplicate suppression only for testing, not for production

## Track Lifecycle And Visible Counts

The worker publishes stabilized tracks, not raw detections.

Track states:

| State | Meaning |
|---|---|
| `tentative` | Candidate is being observed but is not yet visible |
| `active` | Track is visible and counted |
| `coasting` | Track was recently active and is being held through a miss |
| `lost` | Track exceeded the TTL and is removed |

Visible count is based on backend lifecycle state. It includes active tracks and
short coasting tracks, not just raw detector hits. This prevents `1 visible now`
from flipping to `0` because of a single missed detection.

Current lifecycle defaults include:

- coasting TTL around 2.5 seconds
- two hits for normal tentative activation
- immediate activation for high-confidence candidates
- spatial reassociation for tracks that lose source tracker ID

Annotated stream and telemetry should come from the same lifecycle truth:

- active tracks draw as normal solid boxes
- coasting tracks draw as subtle/faded/dashed boxes
- telemetry sends the same state and counts

## Speed And Homography

Speed is not a detector feature. It is a calibrated motion metric.

Enable speed when:

- you need `speed_kph`
- the movement plane is visible
- the camera is fixed
- you can mark four reliable source points and four destination points

Leave speed off when:

- the scene only needs presence, counts, or events
- the plane is not visible
- people move on stairs, beds, platforms, or uneven terrain
- the camera moves or auto-zooms
- compute budget is tight

When speed is off:

- homography can be `null`
- worker does not compute speed
- telemetry speed is `null`
- `argus_motion_speed_disabled_total` records skipped speed work

When speed is on:

- homography is required
- worker computes speed after tracking
- speed samples are counted only when a non-null speed is produced

## Detection Regions In Detail

Detection regions are detector input policy. They run before tracking and before
event zones.

### Include Regions

Use include regions to say: "Only detect this class here."

Good examples:

- walkable floor in a room
- sidewalk or road lane
- loading dock rectangle
- shelf face
- gate approach

Risk:

- if the include region is too small, real objects disappear at the edge
- if the bottom-center anchor leaves the polygon, people or vehicles may be
  filtered even if their upper body is visible

### Exclusion Regions

Use exclusion regions to say: "Ignore this false-positive island."

Good examples:

- pillow or blanket that looks like a person
- mirror or TV reflection
- poster or mannequin
- vegetation patch
- parked object that should not be tracked

Risk:

- if the exclusion region covers a valid path, real tracks will vanish inside it
- if it is class-scoped incorrectly, it may suppress the wrong target

### Class Scope

Empty `class_names` means all active classes.

Examples:

```json
{ "class_names": ["person"] }
```

Only applies to people.

```json
{ "class_names": ["car", "truck", "bus"] }
```

Applies to vehicle classes.

```json
{ "class_names": [] }
```

Applies to everything.

### Region Coordinates

Regions store:

- `polygon`: pixel coordinates in the authoring frame
- `frame_size`: the frame dimensions used while authoring
- `points_normalized`: backend-normalized coordinates from 0 to 1

This lets the backend map regions back to worker frame size.

## Event Boundaries Versus Detection Regions

Use this distinction every time:

| Need | Use |
|---|---|
| Count a doorway crossing | Event boundary line |
| Count entry/exit from an area | Event polygon zone |
| Stop a pillow from becoming a person | Detection exclusion region |
| Only detect vehicles in a lane | Detection include region |
| Label tracks by zone | Event polygon zone |
| Reduce detector false positives before tracking | Detection regions |

Do not use event zones as a substitute for detection gating. Event zones run
after detection and tracking. A false track can still exist unless a detection
region or candidate gate rejects it.

## API Examples

### Create A Balanced Detection-Only Scene

```json
{
  "site_id": "site-1",
  "name": "Lab Camera",
  "rtsp_url": "rtsp://camera.local/live",
  "processing_mode": "central",
  "primary_model_id": "model-person-vehicle",
  "secondary_model_id": null,
  "tracker_type": "botsort",
  "active_classes": ["person"],
  "attribute_rules": [],
  "zones": [],
  "vision_profile": {
    "compute_tier": "edge_standard",
    "accuracy_mode": "balanced",
    "scene_difficulty": "cluttered",
    "object_domain": "people",
    "motion_metrics": { "speed_enabled": false },
    "candidate_quality": {},
    "tracker_profile": {},
    "verifier_profile": {}
  },
  "detection_regions": [
    {
      "id": "bed-ignore",
      "mode": "exclude",
      "polygon": [[850, 360], [1280, 360], [1280, 720], [850, 720]],
      "class_names": ["person"],
      "frame_size": { "width": 1280, "height": 720 }
    }
  ],
  "homography": null,
  "privacy": {
    "blur_faces": true,
    "blur_plates": true,
    "method": "gaussian",
    "strength": 7
  },
  "browser_delivery": {
    "default_profile": "720p10",
    "allow_native_on_demand": true,
    "profiles": []
  },
  "frame_skip": 1,
  "fps_cap": 25
}
```

### Enable Speed For A Vehicle Gate

```json
{
  "vision_profile": {
    "compute_tier": "edge_advanced_jetson",
    "accuracy_mode": "maximum_accuracy",
    "scene_difficulty": "traffic",
    "object_domain": "vehicles",
    "motion_metrics": { "speed_enabled": true },
    "candidate_quality": {},
    "tracker_profile": {},
    "verifier_profile": {}
  },
  "homography": {
    "src": [[120, 420], [900, 420], [1120, 690], [60, 690]],
    "dst": [[0, 0], [10, 0], [10, 20], [0, 20]],
    "ref_distance_m": 20.0
  }
}
```

### Advanced Candidate Tuning

```json
{
  "vision_profile": {
    "compute_tier": "central_gpu",
    "accuracy_mode": "maximum_accuracy",
    "scene_difficulty": "occluded",
    "object_domain": "people",
    "motion_metrics": { "speed_enabled": false },
    "candidate_quality": {
      "new_track_min_confidence": {
        "person": 0.6,
        "default": 0.5
      },
      "duplicate_suppression_enabled": true,
      "memory_frames": 36
    },
    "tracker_profile": {
      "new_track_min_hits": 3
    },
    "verifier_profile": {
      "mode": "suspicious_only"
    }
  }
}
```

## Metrics And Observability

Use these Prometheus counters to understand behavior:

| Metric | Meaning |
|---|---|
| `argus_candidate_rejected_total` | Candidate quality gate rejected a detection |
| `argus_candidate_passed_total` | Candidate quality gate accepted a detection |
| `argus_detection_region_filtered_total` | Region policy removed a detection |
| `argus_motion_speed_samples_total` | A non-null speed sample was produced |
| `argus_motion_speed_disabled_total` | Speed work was skipped or unavailable |

Useful labels include:

- `camera_id`
- `class_name`
- `reason`
- `mode`

Open-vocabulary class labels are bounded as `open_vocab` to avoid unbounded
metric cardinality.

Common interpretations:

| Observation | Likely Meaning |
|---|---|
| high `new_track_low_confidence` | detector is seeing weak new objects; consider regions or better lighting |
| high `duplicate_fragment` | split-body or split-object suppression is working |
| high `inside_exclusion_region` | exclusion regions are actively suppressing known false positives |
| speed disabled with reason `profile_disabled` | speed toggle is off |
| speed disabled with reason `missing_homography` | speed was requested without usable calibration at runtime |

## Troubleshooting

### Pillow, Bed, Poster, Or Static Object Detected As Person

Recommended order:

1. Add an exclusion region around the false-positive island.
2. Scope it to `person`.
3. Keep `Balanced` if the rest of the scene is simple.
4. Move to `Maximum Accuracy` if the false positive survives.
5. Raise `candidate_quality.new_track_min_confidence.person` through the API
   only if regions are not enough.

### One Person Splits Into Two Tracks

This often happens when a laptop, chair, desk, or doorway divides the body.

Recommended order:

1. Use `Maximum Accuracy` on `edge_advanced_jetson` or `central_gpu`.
2. Keep duplicate suppression enabled.
3. Add exclusion regions only for static false-positive surfaces, not over the
   person path.
4. Improve camera angle if the lower body is constantly occluded.
5. Avoid too aggressive include regions that crop the footpoint.

### Visible Count Flickers Between 1 And 0

Expected behavior after stabilization is that short misses coast instead of
dropping immediately.

Check:

- worker is actually running and publishing fresh telemetry
- the same camera is selected in the live view
- candidate gate is not rejecting every continuation
- detection regions do not exclude the object's footpoint
- model confidence is not chronically below threshold
- lighting and exposure are stable
- frame skip and FPS cap are not too aggressive for the motion

### Real Object Disappears Inside A Region

Check:

- include region covers the object's anchor point, not just its upper body
- exclusion region is not overlapping the valid path
- class scope is correct
- region was authored on the correct frame size

### Speed Is Null

Check:

- speed metrics are enabled in the vision profile
- homography is present
- the object has at least two timed positions
- the track is active long enough to compute motion
- the track is moving on the calibrated plane

### Speed Looks Wrong

Check:

- source and destination points are ordered consistently
- reference distance is measured correctly
- points lie on the movement plane
- camera did not move after calibration
- stream resolution did not change without re-authoring calibration

## Validation Rules

The current implementation enforces:

- `homography` may be `null` when speed is disabled.
- `homography` is required when `motion_metrics.speed_enabled=true`.
- detection regions must have at least three polygon points.
- detection region normalized points must be between 0 and 1.
- detection region pixel points must fall inside declared `frame_size`.
- `detection_regions` cannot be set to `null` on update; use `[]` to clear.
- advanced profile subfields are preserved by the wizard when editing.

## Recommended Operating Procedure

For each new scene:

1. Start with `Balanced` + `Standard Edge` and speed off.
2. Select only the classes you need.
3. Save the scene without homography unless speed is required.
4. Observe live telemetry and annotated overlay.
5. Add exclusion regions for obvious false positives.
6. Add include regions if the valid detection area is bounded.
7. Add event boundaries only after tracks are stable.
8. Enable speed only after the camera view and calibration plane are reliable.
9. Move to `Maximum Accuracy` for occlusion, crowds, or split tracks.
10. Use API-level candidate tuning only after regions and profile choice are not
    enough.

For production changes:

- change one setting group at a time
- watch telemetry and metrics for several minutes
- verify annotated overlay and telemetry agree
- keep screenshots of region authoring when diagnosing false positives
- prefer class-scoped regions over broad all-class masks when possible

## Current Limitations And Future Hooks

Current implementation includes:

- persisted scene vision profile
- explicit speed enablement
- optional homography for speed-off scenes
- candidate quality gate
- include/exclusion detection regions
- compact scene-list vision summary
- metrics for candidate and region behavior

Current implementation does not yet include:

- UI controls for `scene_difficulty` and `object_domain`
- UI controls for raw `candidate_quality`, `tracker_profile`, or
  `verifier_profile`
- ReID execution
- verifier model execution
- TensorRT/DeepStream runtime mapping for `edge_advanced_jetson`

Those fields are intentionally part of the API now so advanced runtime work can
arrive without another camera contract redesign.
