# Browser Delivery Contract Design

## Goal

Make browser delivery semantics honest across central and edge deployments:

- `native` means true camera passthrough.
- non-native profiles mean worker-published processed video.
- telemetry and inference continue independently of browser video delivery.

## Problem

Today, browser delivery profiles combine three different ideas:

- the camera ingest stream used by inference
- the stream variant watched in the browser
- the place where a bandwidth reduction can actually happen

That created confusion during iMac and Jetson validation. A central camera can show a `720p10` profile even though central inference still has to ingest the native camera feed. Conversely, an edge camera can request `720p10` while the Jetson stack falls back to passthrough, so the selected profile does not describe the delivered video.

The current `native` profile is also overloaded. In some central paths, `native` is resolved to a clean processed stream on `cameras/<id>/annotated` instead of the real `cameras/<id>/passthrough` path. That makes the Live page and worker config harder to reason about.

## Delivery Contract

### All Modes

`native` is a hard contract:

- It resolves to `StreamMode.PASSTHROUGH`.
- It reads `cameras/<camera_id>/passthrough`.
- The inference worker does not publish video frames for the browser path.
- It is clean video with no drawn boxes, no privacy blur, no resize, and no browser FPS cap.

If privacy blur is enabled, `native` is unavailable because it cannot both be true passthrough and apply privacy filtering. The system must resolve to a processed profile instead of silently treating native as processed.

Telemetry, tracking, counts, speed, zones, incidents, and history remain independent of this choice. Inference always uses its configured camera ingest path.

### Central Cameras

Central processing means the master node already ingests the native camera stream for inference. Reduced browser profiles do not reduce camera-to-master bandwidth.

Central browser delivery options are:

- `native`: direct camera passthrough through master MediaMTX.
- `annotated`: full-rate processed stream with drawn boxes from the central worker.
- `1080p15`, `720p10`, `540p5`: viewer preview streams from the central worker.

The UI label for reduced central profiles must make the scope explicit. These profiles reduce master-to-browser bandwidth and browser decode load only. They do not reduce central inference ingest bandwidth.

### Edge Cameras

Edge processing means the edge node performs inference near the camera and exposes browser streams from edge MediaMTX, relayed through master MediaMTX when needed.

Edge browser delivery options are:

- `native`: edge MediaMTX passthrough relayed to the master/browser.
- `annotated`: full-rate processed stream from the edge worker.
- `1080p15`, `720p10`, `540p5`: edge-built processed preview streams.

The UI label for reduced edge profiles must make the scope explicit. These profiles reduce edge-to-master/browser video bandwidth because the downscale and FPS cap happen on the edge node before the browser stream is consumed remotely.

### Hybrid Cameras

`hybrid` remains an experimental schema value for future two-stage analytics: edge primary detection/tracking plus heavier central second-stage analysis. It is not part of this delivery cleanup.

For this work:

- Do not add new hybrid delivery behavior.
- Do not remove the enum or database support.
- Treat hybrid as central-like wherever existing scheduling currently treats it as central.
- Prefer hiding or de-emphasizing hybrid in new operator-facing camera setup once a separate product decision is made.

## Stream Profiles

The browser profile catalog should include:

| Profile | Kind | Dimensions | FPS | Meaning |
| --- | --- | --- | --- | --- |
| `native` | passthrough | source | source | true clean camera stream |
| `annotated` | transcode | source | camera FPS cap | processed stream with drawn boxes |
| `1080p15` | transcode | 1920x1080 | 15 | processed viewer preview |
| `720p10` | transcode | 1280x720 | 10 | processed viewer preview |
| `540p5` | transcode | 960x540 | 5 | processed viewer preview |

`annotated` uses `kind="transcode"` even when it does not resize, because it is a worker-published processed stream. A `transcode` profile with no width, height, or FPS means "publish processed video at the camera FPS cap and source dimensions."

## Backend Behavior

### Worker Config

Worker stream settings must be derived from the resolved browser delivery settings:

- `native` -> `kind="passthrough"`, no dimensions, `fps=fps_cap`.
- `annotated` -> `kind="transcode"`, no dimensions, `fps=fps_cap`.
- reduced profiles -> `kind="transcode"`, width/height from the profile, `fps=min(camera.fps_cap, profile.fps)`.

The old central-only "processed native" branch should be removed. It is the source of the current ambiguity.

### Stream Access

Stream access should follow the resolved worker stream kind:

- central + `passthrough` + no privacy -> master `passthrough`
- central + `transcode` -> master `annotated`
- edge + `passthrough` + no privacy -> master relay to edge `passthrough`
- edge + `transcode` -> master relay to edge `annotated`
- privacy-enabled delivery -> processed path only

The master backend already has an edge relay mechanism for passthrough. It should be generalized so any edge stream access path can be relayed from the configured edge MediaMTX base URL.

### MediaMTX Registration

MediaMTX registration should no longer fall back to passthrough for Jetson when the requested stream kind is `transcode`.

Expected registration behavior:

- requested passthrough with no privacy -> register/read passthrough
- requested transcode on central -> register passthrough ingest plus annotated publisher path
- requested transcode on edge -> register passthrough ingest plus annotated publisher path on edge MediaMTX
- privacy required -> use a processed stream and never return `StreamMode.PASSTHROUGH`

For non-native profiles, the inference worker should publish frames. For native passthrough, `publish_stream` should stay near zero because video frames are not pushed.

## Frontend Behavior

### Camera Setup

The browser delivery selector should show labels that explain scope:

- central native: `Native camera`
- central annotated: `Annotated`
- central reduced: `720p10 viewer preview`
- edge native: `Native edge passthrough`
- edge annotated: `Annotated edge stream`
- edge reduced: `720p10 edge bandwidth saver`

The profile `value` remains the stable profile id. Only labels and helper copy change.

Hybrid should not be expanded by this work. If hybrid remains selectable, it should use central-style labels until a separate hybrid workflow exists.

### Live Page

The Live page should not hide the actual stream mode.

It should show:

- the selected delivery profile label
- the actual frame `stream_mode` when telemetry is available

Examples:

- `central processing - Native camera - passthrough`
- `central processing - 720p10 viewer preview - annotated-whip`
- `edge processing - 720p10 edge bandwidth saver - annotated-whip`

The current special case that shows `native clean` when the selected profile is native and privacy is off should be removed or narrowed to real passthrough telemetry.

## Compatibility

Existing cameras with `default_profile="720p10"` remain valid. This work changes labels and behavior consistency, not stored IDs.

Existing cameras with `default_profile="native"` and privacy enabled should resolve away from native at runtime because true passthrough cannot apply blur. The stored configuration can be cleaned up on the next camera edit, but runtime behavior should stay safe.

Generated frontend API types must be refreshed after backend schema changes.

## Out Of Scope

- Jetson GPU acceleration and TensorRT provider work.
- New hybrid two-stage analytics.
- Removing the `hybrid` enum from the database.
- Changing camera ingest or inference quality based on browser delivery.
- Supervisor lifecycle automation.

## Acceptance Criteria

- Central native resolves to `StreamMode.PASSTHROUGH` through service-level stream access.
- Edge native resolves to `StreamMode.PASSTHROUGH` and master MediaMTX relays the edge passthrough path when configured.
- Central reduced profiles resolve to processed `annotated` delivery and are labeled as master-to-browser viewer previews.
- Edge reduced profiles resolve to processed `annotated` delivery and are labeled as edge-built bandwidth savers.
- Worker config for native is passthrough in central and edge.
- Worker config for `annotated` is transcode with no resize and FPS equal to camera FPS cap.
- Worker config for reduced profiles is transcode with profile dimensions and capped FPS.
- Live page displays actual stream mode instead of masking annotated delivery as native.
- Existing telemetry, history, incidents, and tracking behavior do not depend on browser delivery profile.
