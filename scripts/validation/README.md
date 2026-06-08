# Validation Scripts

`start_detection_fixture.sh` publishes a deterministic RTSP stream from the Ultralytics `bus.jpg` sample image. It expects an authenticated MediaMTX publish URL in `VEZOR_SMOKE_FIXTURE_PUBLISH_URL` and redacts the URL in logs.

`VEZOR_SMOKE_FIXTURE_PUBLISH_URL` is also local-only and sensitive. Never commit it.

Real camera validation is optional and uses local-only env vars:
- `VEZOR_SMOKE_REAL_RTSP_720P_URL`
- `VEZOR_SMOKE_REAL_RTSP_1296P_URL`

Never commit those values.
