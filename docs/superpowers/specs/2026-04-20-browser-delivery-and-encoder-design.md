# Browser Delivery And Encoder Design

## Goal

Turn camera `browser_delivery` presets like `720p10` into real operator-facing stream behavior, then add production-grade encoder selection so HQ nodes can use hardware encode when available.

## Current State

- Camera CRUD and UI already store `browser_delivery` profiles such as `native`, `1080p15`, `720p10`, and `540p5`.
- Worker config does not yet carry any resolved stream delivery settings; [WorkerStreamSettings](/Users/yann.moren/vision/backend/src/argus/api/contracts.py) is empty and [_camera_to_worker_config(...)](/Users/yann.moren/vision/backend/src/argus/services/app.py) does not pass `browser_delivery` through.
- The new central/preview publisher now sends real frames into MediaMTX, but:
  - it publishes at the worker frame size
  - it uses the worker FPS cap
  - it always encodes with `libx264`

## Product Requirement

For real product behavior, analytics ingest and browser delivery must be separate concerns:

- inference should keep using the configured camera ingest settings
- browser delivery should choose the operator-facing resolution / frame rate independently
- encoder selection should adapt to host capability without changing the browser contract

## Chosen Rollout

### Step 1: Real Browser Delivery Presets

Make `browser_delivery` drive the actual worker output stream.

- Resolve the selected `browser_delivery.default_profile` in the backend control plane.
- Include a resolved stream policy in worker config:
  - `profile_id`
  - `kind`
  - `width`
  - `height`
  - `fps`
- Update the worker publisher path to:
  - resize frames when the selected profile is a transcode profile
  - cadence-limit outgoing frames to the selected browser FPS
  - preserve `native` as full-size/full-rate output

This makes `720p10` mean “publish a 1280x720 stream at 10 fps,” not just “display this label in the UI.”

### Step 2: Encoder Capability Selection

Keep the same publish path and stream policy, but choose the encoder according to runtime capability.

- Prefer `h264_nvenc` on Linux/NVIDIA HQ nodes
- Prefer `h264_videotoolbox` on macOS when available for local dev realism
- Fall back to `libx264` everywhere else

This keeps the browser-facing streaming architecture unchanged while making the central publisher closer to production performance.

## Why This Order

- Step 1 is what makes the browser delivery product feature real.
- Step 2 is an optimization and deployment-hardening layer on top of Step 1.
- Stopping after Step 1 lets the operator validate that the stream shape and cadence are correct before adding encoder complexity.

## Scope

### In scope

- worker config schema changes for resolved stream delivery policy
- backend control-plane mapping from `browser_delivery` to worker stream settings
- worker-side resizing and FPS throttling for outgoing published streams
- encoder selection logic and tests

### Out of scope

- changing MediaMTX read-side URLs or browser player logic
- changing inference ingest quality based on browser delivery
- full bitrate / GOP / advanced transcode tuning UI in this slice

## Validation Plan

### After Step 1

- confirm that `720p10` produces a lower-resolution, lower-FPS live stream
- confirm that `native` preserves the worker’s full output size/rate
- validate on the iMac with the real camera before proceeding

### After Step 2

- confirm that the chosen encoder matches host capability
- confirm fallback behavior is stable when hardware encode is not available
- confirm MediaMTX/browser playback behavior is unchanged
