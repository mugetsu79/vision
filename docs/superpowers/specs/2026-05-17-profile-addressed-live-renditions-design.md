# Profile Addressed Live Renditions Design

Date: 2026-05-17
Status: Deferred after May 2026 field validation.

## Goal

Make Live tile resolution and frame-rate profile changes enforceable. When an operator applies `540p5`, the browser must consume the `540p5` processed stream path, not whatever processed stream is currently available at the generic annotated path.

This design keeps profile changes global per camera. It does not introduce per-viewer transcoding, multiple simultaneous processed renditions per camera, WebGL, DeepStream, or a new streaming server.

## Root Cause

The existing profile control updates `camera.browser_delivery.default_profile` and publishes an async worker command with the selected width, height, and FPS. The worker can resize and FPS-gate frames after it receives that command.

The unreliable part is the stream contract:

- HLS, MJPEG, and WebRTC requests do not include the selected profile id.
- Backend stream access resolves all transcode profiles to the same path, normally `cameras/{camera_id}/annotated`.
- MediaMTX worker registration also publishes all transcode profiles to that same generic path.
- The Live tile reconnects immediately after the camera PATCH succeeds, before it can know whether the worker has re-registered the new rendition.

Native to annotated appears to work because it changes stream kind and path. `720p10` to `540p5` stays on the same path, so the browser can continue showing the old processed output.

## Product Semantics

Profile selection remains a scene-level operator setting:

- Applying a Live rendition updates the camera's active browser delivery profile.
- Only one processed profile is active for a camera at a time.
- Another operator viewing the same camera should converge to the same active profile after the camera refreshes.
- Native passthrough remains source-native and does not promise output resize or FPS enforcement.

The browser should request the active profile explicitly. If the worker has not published that profile-specific path yet, the tile should show an applying/retrying state instead of silently consuming an older profile.

## Stream Path Contract

Processed dimensioned profiles get profile-specific paths:

| Profile | Kind | Path |
| --- | --- | --- |
| `native` | passthrough | `cameras/{camera_id}/passthrough` |
| `annotated` | transcode legacy/default | `cameras/{camera_id}/annotated` |
| `720p10` | transcode | `cameras/{camera_id}/annotated-720p10` |
| `540p5` | transcode | `cameras/{camera_id}/annotated-540p5` |
| privacy preview for `540p5` | filtered preview | `cameras/{camera_id}/preview-540p5` |

The generic `annotated` and `preview` paths remain for compatibility and for non-dimensioned fallback profiles. Dimensioned profiles use profile-specific suffixes so tests and operators can tell exactly which rendition is being consumed.

Profile ids must be sanitized before they become path segments. The accepted segment grammar is:

```text
[a-zA-Z0-9_.-]+
```

Unknown or unsafe requested profile ids are rejected at the API layer with `422` rather than being interpolated into a MediaMTX path.

## API Contract

The stream APIs accept an optional requested profile id:

- WebRTC offer body:

```json
{
  "sdp_offer": "v=0...",
  "profile_id": "540p5"
}
```

- HLS playlist query:

```text
/api/v1/streams/{camera_id}/hls.m3u8?profile_id=540p5
```

- HLS segment and nested playlist proxy requests preserve the profile id while rewriting playlist resources.

- MJPEG query:

```text
/video_feed/{camera_id}?profile_id=540p5
```

If `profile_id` is omitted, backend behavior falls back to the camera's current `browser_delivery.default_profile`. This keeps older clients working.

The generated frontend OpenAPI client should be regenerated after the contract changes.

## Backend Resolution

`StreamService._resolve_stream_access` accepts `requested_profile_id`.

Resolution steps:

1. Load the camera and its source-aware browser delivery settings.
2. Validate that `requested_profile_id`, when provided, exists in `browser_delivery.profiles`.
3. If omitted, use `browser_delivery.default_profile`.
4. Build `WorkerStreamSettings` for the selected profile.
5. Pass both `stream_kind` and `profile_id` into `resolve_stream_access`.
6. Return stream URLs whose path includes the profile-specific suffix for dimensioned transcode profiles.

The worker command path continues to use `browser_delivery.default_profile`. The stream request path does not mutate camera state.

## Worker And MediaMTX

`WorkerStreamSettings.profile_id` must be passed into `stream_client.register_stream`.

`MediaMTXClient.register_stream` accepts `profile_id` and uses it to build the publish/read path. Publisher restart behavior remains shape/FPS-aware:

- A resolution profile change should create a new registration path.
- The existing publisher should close when the registration path changes.
- Resizing remains in `_prepare_frame_for_publish`.
- FPS enforcement remains in `_should_publish_frame`.

The worker publishes only the active profile path. It does not pre-publish every available rendition.

## Frontend UX

`VideoStream` receives `defaultProfile` from the camera and includes it in all stream requests.

When the profile changes:

- The stream session key changes.
- WebRTC offer body includes the new `profile_id`.
- HLS URL includes the new `profile_id`.
- MJPEG URL includes the new `profile_id`.
- The badge displays the profile id or formatted profile label, not only the delivery transport.

The tile should show an applying/retrying state while a profile-specific path is not ready. Existing `StreamNotReadyError` handling can be reused; the important change is that "not ready" now means the requested profile path is not published yet, not that the camera is globally unavailable.

## Compatibility

Backward compatibility requirements:

- Existing clients that omit `profile_id` keep using the camera default profile.
- The `annotated` profile keeps the legacy `cameras/{camera_id}/annotated` path.
- `native` keeps the legacy `cameras/{camera_id}/passthrough` path.
- MediaMTX read tokens remain path-scoped to the resolved profile path.
- Installer and portable demo do not need new services or GPU features.

## Testing Strategy

Backend tests must prove:

- `resolve_stream_access` returns different paths for `720p10` and `540p5`.
- `native` and legacy `annotated` keep their current paths.
- stream routes pass requested profile ids through to the service.
- invalid or unsupported profile ids fail.
- MediaMTX registers dimensioned transcode profiles on profile-specific paths.
- worker re-registration includes `profile_id`.

Frontend tests must prove:

- `VideoStream` includes `profile_id` in HLS and MJPEG URLs.
- WebRTC offer body includes `profile_id`.
- changing `defaultProfile` restarts the session and requests the new profile.
- the visible badge identifies the profile even when `deliveryMode` is `hls`.

Manual validation should use the portable demo with WebGL off:

1. Start Live with a camera on `720p10`.
2. Apply `540p5`.
3. Confirm the browser requests `profile_id=540p5`.
4. Confirm the MediaMTX path is `cameras/{camera_id}/annotated-540p5`.
5. Confirm the video element reports approximately 960x540.
6. Confirm the observed frame cadence drops near 5 FPS.
