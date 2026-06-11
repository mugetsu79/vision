# Jetson Live Overlay Stability Design

## Goal

Make Jetson Live browser overlays and processed video annotations stable and spatially correct across low-resolution renditions, while making scene vision modes materially affect tracking behavior.

## Current Findings

- The Jetson worker is detecting the person class with high confidence in the current scene; recent samples show a stable person track near 0.91 confidence.
- The browser overlay can still flap between active and held because a single backend coasting frame is rendered immediately as `last seen`.
- Edge telemetry is published through a constrained path and can drop stale frames under load; the UI must tolerate sparse telemetry without visually implying tracker failure.
- Telemetry coordinates are rendered against `camera.source_capability`. If that metadata is stale or differs from the actual worker frame after a source/profile change, low-resolution renditions can project boxes onto the wrong part of the video.
- The moving dot is the browser overlay trail endpoint. It is useful for motion trails, but it is distracting in the operator video tile and should not be part of the default overlay.
- `resolve_scene_vision_profile` computes stronger tracking posture for `maximum_accuracy` and `edge_advanced_jetson`, but the worker does not currently apply the resolved tracker/lifecycle values.

## Design

### Overlay Geometry

Telemetry frames will carry an optional `source_size` field describing the exact frame coordinate space used for bounding boxes. The worker will set it from the processed frame dimensions used by detection/tracking. The Live page will prefer `frame.source_size`, then fall back to `camera.source_capability`, then fall back to bbox extents.

This keeps browser overlay projection tied to the worker’s real coordinate system instead of the selected rendition size. A 240p stream can still use 1280x720 telemetry coordinates correctly because the canvas maps the source coordinate space into the rendered video rectangle.

### Overlay Visual Stability

The frontend will treat short coasting updates as visually live. A backend coasting track under a small grace window remains labeled as `person`, not `person last seen`. It only becomes held after the grace window. Missing telemetry frames continue to use the existing hold window.

The worker-side processed stream annotation will mirror this behavior: short coasts keep the active box style and label; only longer coasts switch to dashed held styling. This makes a single missed detector frame invisible to operators while still reporting genuinely stale tracks truthfully.

The browser overlay will stop drawing the center endpoint dot by default. The box remains, and the label remains. Trails can be reintroduced later behind an explicit motion/debug overlay mode.

Browser-drawn boxes are only for native/passthrough streams. Worker-rendered streams suppress browser boxes: both `annotated-whip` and `filtered-preview` carry processed video from the worker, so the browser overlay toggle must not add a second tracking layer in either mode.

### Vision Mode Wiring

The worker will apply the resolved scene vision profile to:

- tracker scene profile (`efficient` vs `difficult`) for maximum-accuracy advanced edge / central GPU posture;
- lifecycle tentative hits from `resolved.tracker.new_track_min_hits`;
- lifecycle coast duration from `resolved.candidate_quality.memory_frames`, scaled against the existing 24-frame/default-TTL baseline with sensible min/max bounds.

When the camera vision profile changes at runtime, the worker will rebuild the candidate quality gate, tracker, and lifecycle manager from the resolved profile and reset track state so the new mode takes effect cleanly.

## Non-Goals

- No DeepStream work.
- No model replacement.
- No registry publishing.
- No Dockerized central GPU claims.
- No raw RTSP or token logging.

## Validation

- Add failing frontend tests for source-size preference, short coasting grace, and no center-dot drawing.
- Add failing backend tests that telemetry includes source size and maximum-accuracy advanced edge changes tracker/lifecycle config.
- Run targeted frontend and backend tests.
- Run a live Jetson smoke after deployment to confirm:
  - selected rendition can be 240p while overlay remains spatially aligned;
  - active/held label no longer flaps on single missed frames;
  - runtime reports remain fresh and Jetson FPS is not materially harmed.
