# Live Dashboard Refresh and Detection Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land five detection/telemetry bug fixes, consolidate Dashboard and Live into one "Live" page, and add a 30-minute detection-rate sparkline inside each camera tile.

**Architecture:** Backend work is in three independent areas: detector bbox rescale, history service count path, and MediaMTX always-relay registration. Frontend consolidates two redundant pages, introduces an app-level Zustand telemetry store so the WebSocket survives navigation, and adds a per-camera sparkline hydrated from `/api/v1/history/series` plus live WS updates.

**Tech Stack:** FastAPI + SQLAlchemy async + TimescaleDB; React 19 + Zustand 5 + TanStack Query v5 + ECharts 6 + React Router v6 + Playwright + vitest.

---

## File Structure

**Backend — modify:**
- `backend/src/argus/vision/detector.py` — rewrite `_rescale_bbox`.
- `backend/src/argus/services/app.py` — rename existing `_fetch_series_rows` to `_fetch_series_rows_aggregate`; add `_fetch_series_rows_from_events`; update `HistoryService.query_series` dispatch.
- `backend/src/argus/streaming/mediamtx.py` — add `ingest_path` field to `StreamRegistration`; rewrite `_build_registration` for always-relay; ensure `cameras/<id>/passthrough` is always pulled from the camera; register `cameras/<id>/annotated` as publisher-receive when mode is not passthrough or privacy is active.
- `backend/src/argus/inference/engine.py` — reorder worker bootstrap so `stream_client.register_stream` runs before `create_camera_source`, then create the frame source from `registration.ingest_path`.

**Backend — create:**
- `backend/tests/vision/test_detector_rescale.py` — focused tests for `_rescale_bbox`.

**Backend — extend existing tests:**
- `backend/tests/services/test_history_service.py` — add count-path tests for `_fetch_series_rows_from_events`.
- `backend/tests/streaming/test_mediamtx.py` — cover always-relay registration + `ingest_path`.
- `backend/tests/inference/test_engine.py` — cover bootstrap reorder + ingest_path usage.

**Frontend — modify:**
- `frontend/src/app/router.tsx` — redirect `/dashboard` → `/live`; point `/live` at the renamed page.
- `frontend/src/components/layout/TopNav.tsx` — remove "Dashboard" Operations entry.
- `frontend/src/hooks/use-live-telemetry.ts` — rewrite as a thin selector over the new store, preserve the existing return shape so call sites don't need touching.

**Frontend — delete:**
- `frontend/src/pages/Live.tsx` — the six-line wrapper (deleted before the rename so the path is free).
- `frontend/src/pages/Dashboard.tsx` — moved via `git mv` to `pages/Live.tsx`.

**Frontend — rename:**
- `frontend/src/pages/Dashboard.tsx` → `frontend/src/pages/Live.tsx` via `git mv` (after the wrapper above is deleted).

**Frontend — create:**
- `frontend/src/stores/telemetry-store.ts` — app-level Zustand store with ref-counted WS subscription and per-camera ring buffer.
- `frontend/src/stores/telemetry-store.test.ts` — vitest coverage of the store lifecycle.
- `frontend/src/hooks/use-live-sparkline.ts` — hybrid hydration (history seed + live from store) + minute rollover.
- `frontend/src/components/live/LiveSparkline.tsx` — the per-tile sparkline component.
- `frontend/src/components/live/LiveSparkline.test.tsx` — vitest for the component.

**Frontend — extend:**
- `frontend/e2e/prompt8-live-dashboard.spec.ts` (or nearest equivalent) — add IA redirect + sparkline scenarios.

**No database migrations.**

---

## Task 1: Rewrite `_rescale_bbox` (Bug 1)

**Files:**
- Modify: `backend/src/argus/vision/detector.py:196-218`
- Create: `backend/tests/vision/test_detector_rescale.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/vision/test_detector_rescale.py`:

```python
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from argus.vision.detector import YoloDetector


def _make_detector(model_input: tuple[int, int]) -> YoloDetector:
    detector = YoloDetector.__new__(YoloDetector)
    detector.model_config = MagicMock()
    detector.model_config.input_shape = {"width": model_input[0], "height": model_input[1]}
    return detector


def test_rescale_bbox_scales_model_input_to_frame() -> None:
    detector = _make_detector((640, 640))
    bbox = (100.0, 100.0, 500.0, 500.0)
    result = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert result == pytest.approx((200.0, 112.5, 1000.0, 562.5), rel=1e-6)


def test_rescale_bbox_clips_to_frame_bounds() -> None:
    detector = _make_detector((640, 640))
    bbox = (-50.0, -50.0, 700.0, 700.0)
    x1, y1, x2, y2 = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert x1 == 0.0
    assert y1 == 0.0
    assert x2 == pytest.approx(1280.0)
    assert y2 == pytest.approx(720.0)


def test_rescale_bbox_returns_unchanged_on_invalid_dimensions() -> None:
    detector = _make_detector((0, 640))
    bbox = (10.0, 20.0, 30.0, 40.0)
    result = detector._rescale_bbox(bbox, frame_width=1280, frame_height=720)
    assert result == (10.0, 20.0, 30.0, 40.0)
```

- [ ] **Step 2: Run tests — expect failure**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision/test_detector_rescale.py -q`
Expected: the first test fails (current code returns `(100, 100, 500, 500)` unchanged because `max(bbox) = 500 <= 1280`). Confirms the bug.

- [ ] **Step 3: Rewrite `_rescale_bbox`**

Replace lines 196–218 of `backend/src/argus/vision/detector.py`:

```python
    def _rescale_bbox(
        self,
        bbox: tuple[float, float, float, float],
        frame_width: int,
        frame_height: int,
    ) -> tuple[float, float, float, float]:
        input_width = float(self.model_config.input_shape["width"])
        input_height = float(self.model_config.input_shape["height"])
        if (
            input_width <= 0.0
            or input_height <= 0.0
            or frame_width <= 0
            or frame_height <= 0
        ):
            LOGGER.warning(
                "Invalid input/frame dimensions, returning bbox unchanged: "
                "input=%sx%s frame=%sx%s",
                input_width,
                input_height,
                frame_width,
                frame_height,
            )
            x1, y1, x2, y2 = bbox
            return (float(x1), float(y1), float(x2), float(y2))
        scale_x = frame_width / input_width
        scale_y = frame_height / input_height
        x1, y1, x2, y2 = bbox
        return (
            float(np.clip(x1 * scale_x, 0.0, frame_width)),
            float(np.clip(y1 * scale_y, 0.0, frame_height)),
            float(np.clip(x2 * scale_x, 0.0, frame_width)),
            float(np.clip(y2 * scale_y, 0.0, frame_height)),
        )
```

At the top of `detector.py`, ensure `LOGGER = getLogger(__name__)` exists. Check with `grep "LOGGER = " backend/src/argus/vision/detector.py`. If absent, add `from logging import getLogger` to imports and `LOGGER = getLogger(__name__)` after imports.

- [ ] **Step 4: Run tests — expect pass**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision/test_detector_rescale.py -q`
Expected: 3 passed.

- [ ] **Step 5: Run full vision + inference suite for regression check**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision tests/inference -q`
Expected: all existing tests continue to pass. If `tests/vision/test_detector.py` has any test that relied on the old heuristic, report back with the failure rather than silently adjusting.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/vision/detector.py backend/tests/vision/test_detector_rescale.py
git commit -m "fix(detector): always rescale bbox from model input space to frame space"
```

---

## Task 2: History count path reads `tracking_events` (Bug 3)

**Files:**
- Modify: `backend/src/argus/services/app.py` (the `HistoryService` region around lines 707–893)
- Modify: `backend/tests/services/test_history_service.py`

- [ ] **Step 1: Rename the existing aggregate helper**

In `backend/src/argus/services/app.py`, rename the existing `_fetch_series_rows` method on `HistoryService` (currently at approximately line 850) to `_fetch_series_rows_aggregate`. Update the `query_series` dispatch call-site that currently reads `await self._fetch_series_rows(...)` to use the new name. This preserves the aggregate path for possible future re-introduction.

- [ ] **Step 2: Add the new from-events helper**

Place this new method on `HistoryService`, immediately after `_fetch_series_rows_aggregate`:

```python
    async def _fetch_series_rows_from_events(
        self,
        *,
        camera_ids: list[UUID] | None,
        class_names: list[str] | None,
        granularity: str,
        starts_at: datetime,
        ends_at: datetime,
    ) -> list[dict[str, Any]]:
        interval = _GRANULARITY_INTERVAL[granularity]
        parameters: dict[str, Any] = {
            "starts_at": starts_at,
            "ends_at": ends_at,
        }
        filters: list[str] = []
        if camera_ids:
            filters.append("AND camera_id IN :camera_ids")
            parameters["camera_ids"] = camera_ids
        if class_names:
            filters.append("AND class_name IN :class_names")
            parameters["class_names"] = class_names

        statement = text(
            f"""
            SELECT
              time_bucket(INTERVAL '{interval}', ts) AS bucket,
              class_name,
              count(*)::bigint AS event_count
            FROM tracking_events
            WHERE ts >= :starts_at
              AND ts <= :ends_at
              {' '.join(filters)}
            GROUP BY 1, 2
            ORDER BY 1 ASC, 2 ASC
            """
        )
        if camera_ids:
            statement = statement.bindparams(bindparam("camera_ids", expanding=True))
        if class_names:
            statement = statement.bindparams(bindparam("class_names", expanding=True))

        async with self.session_factory() as session:
            rows = (await session.execute(statement, parameters)).mappings().all()
        return [dict(row) for row in rows]
```

- [ ] **Step 3: Change `query_series` dispatch**

Inside `HistoryService.query_series` (around line 707), find the else-branch that currently reads `rows = await self._fetch_series_rows(...)` (now renamed to `_fetch_series_rows_aggregate`) and replace it with:

```python
        else:
            rows = await self._fetch_series_rows_from_events(
                camera_ids=camera_ids,
                class_names=class_names,
                granularity=effective_granularity,
                starts_at=starts_at,
                ends_at=ends_at,
            )
```

Both speed and count paths now read `tracking_events`. The aggregate helper (`_fetch_series_rows_aggregate`) is unused but preserved.

- [ ] **Step 4: Write the test**

Append to `backend/tests/services/test_history_service.py`:

```python
@pytest.mark.asyncio
async def test_query_series_count_only_reads_tracking_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()

    fresh_rows = [
        {
            "bucket": datetime(2026, 4, 24, 14, 0, tzinfo=UTC),
            "class_name": "person",
            "event_count": 42,
        },
    ]
    from_events = AsyncMock(return_value=fresh_rows)
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", from_events)
    aggregate = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "_fetch_series_rows_aggregate", aggregate)

    starts = datetime(2026, 4, 24, 14, 0, tzinfo=UTC)
    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1m",
        starts_at=starts,
        ends_at=starts + timedelta(minutes=30),
    )

    from_events.assert_awaited_once()
    aggregate.assert_not_awaited()
    assert response.rows[0].values == {"person": 42}
    assert response.rows[0].total_count == 42
```

- [ ] **Step 5: Run tests**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/services/test_history_service.py -q`
Expected: all previous tests + the new one pass.

- [ ] **Step 6: Regression check + lint**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/services tests/api -q && python3 -m uv run ruff check src/argus/services/app.py tests/services/test_history_service.py && python3 -m uv run mypy src/argus/services/app.py`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/services/app.py backend/tests/services/test_history_service.py
git commit -m "fix(history): count-only path reads tracking_events for real-time freshness"
```

---

## Task 3: `StreamRegistration.ingest_path` field

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py` (dataclass around lines 52–62 plus the four registration return sites)
- Modify: `backend/tests/streaming/test_mediamtx.py` (constructor assertions)

- [ ] **Step 1: Add the field to the dataclass**

Find `StreamRegistration` at approximately line 52 and add `ingest_path: str = ""`:

```python
@dataclass(slots=True, frozen=True)
class StreamRegistration:
    camera_id: UUID
    mode: StreamMode
    read_path: str
    publish_path: str | None = None
    path_name: str | None = None
    managed_path_config: bool = False
    target_fps: int = 25
    target_width: int | None = None
    target_height: int | None = None
    ingest_path: str = ""
```

Default `""` keeps existing `StreamRegistration(...)` construction calls in tests working without each test being updated this round. Task 4 populates it properly in the production code path.

- [ ] **Step 2: Run existing tests for regression**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/streaming/test_mediamtx.py -q`
Expected: all previously-passing tests continue to pass. Any constructor-literal `StreamRegistration(...)` in tests that now fails because of a different reason should be flagged, not silently patched.

- [ ] **Step 3: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/streaming/mediamtx.py
git commit -m "feat(mediamtx): add ingest_path field to StreamRegistration"
```

---

## Task 4: Always-relay in `_build_registration` (Bug 5)

**Files:**
- Modify: `backend/src/argus/streaming/mediamtx.py` — `_build_registration` (~lines 423–501)
- Modify: `backend/tests/streaming/test_mediamtx.py`

- [ ] **Step 1: Rewrite `_build_registration`**

Replace the entire method (the current conditional tree from lines 423 to 501) with:

```python
    async def _build_registration(
        self,
        *,
        camera_id: UUID,
        rtsp_url: str,
        profile: PublishProfile,
        stream_kind: str,
        privacy: PrivacyPolicy,
        target_fps: int,
        target_width: int | None,
        target_height: int | None,
    ) -> StreamRegistration:
        passthrough_name = f"cameras/{camera_id}/passthrough"
        passthrough_read = f"{self.rtsp_base_url}/{passthrough_name}"
        await self._ensure_path(
            passthrough_name,
            source=rtsp_url,
            source_on_demand=True,
        )

        requested_passthrough = stream_kind == StreamMode.PASSTHROUGH.value
        if requested_passthrough and privacy.requires_filtering:
            LOGGER.warning(
                (
                    "Passthrough stream requested, but privacy filtering is enabled; "
                    "using a processed stream instead."
                ),
                extra={
                    "camera_id": str(camera_id),
                    "profile": profile.value,
                    "requested_stream_kind": stream_kind,
                },
            )

        effective_passthrough = requested_passthrough and not privacy.requires_filtering

        if effective_passthrough:
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.PASSTHROUGH,
                path_name=passthrough_name,
                read_path=passthrough_read,
                managed_path_config=True,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=passthrough_read,
            )

        if profile is PublishProfile.CENTRAL_GPU:
            annotated_name = f"cameras/{camera_id}/annotated"
            annotated_path = f"{self.rtsp_base_url}/{annotated_name}"
            await self._ensure_path(
                annotated_name,
                source="publisher",
                source_on_demand=False,
            )
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.ANNOTATED_WHIP,
                path_name=annotated_name,
                read_path=annotated_path,
                publish_path=annotated_path,
                managed_path_config=True,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=passthrough_read,
            )

        if privacy.requires_filtering:
            preview_name = f"cameras/{camera_id}/preview"
            preview_path = f"{self.rtsp_base_url}/{preview_name}"
            return StreamRegistration(
                camera_id=camera_id,
                mode=StreamMode.FILTERED_PREVIEW,
                path_name=preview_name,
                read_path=preview_path,
                publish_path=preview_path,
                target_fps=max(1, target_fps),
                target_width=target_width,
                target_height=target_height,
                ingest_path=passthrough_read,
            )

        return StreamRegistration(
            camera_id=camera_id,
            mode=StreamMode.PASSTHROUGH,
            path_name=passthrough_name,
            read_path=passthrough_read,
            managed_path_config=True,
            target_fps=max(1, target_fps),
            target_width=target_width,
            target_height=target_height,
            ingest_path=passthrough_read,
        )
```

Key behaviour: the camera-source `passthrough` path is always registered via `_ensure_path` at the top. The annotated path is registered additionally when `CENTRAL_GPU` + non-passthrough or privacy-active. All returned registrations carry `ingest_path` = the passthrough URL, so the worker always ingests via MediaMTX.

- [ ] **Step 2: Write tests for always-relay behaviour**

Append to `backend/tests/streaming/test_mediamtx.py` (put the helpers/fixtures from the existing file):

```python
@pytest.mark.asyncio
async def test_build_registration_always_registers_camera_source_path() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append((
            request.method,
            str(request.url),
            json.loads(request.content.decode("utf-8")) if request.content else None,
        ))
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        stream_kind="transcode",
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
    )

    # Passthrough path is registered with the camera as source
    passthrough_register = (
        "POST",
        f"http://mediamtx.internal:9997/v3/config/paths/replace/cameras/{camera_id}/passthrough",
        {
            "name": f"cameras/{camera_id}/passthrough",
            "source": "rtsp://camera.internal/live",
            "sourceOnDemand": True,
        },
    )
    assert passthrough_register in requests

    # Annotated path is registered additionally for non-passthrough
    annotated_register = (
        "POST",
        f"http://mediamtx.internal:9997/v3/config/paths/replace/cameras/{camera_id}/annotated",
        {
            "name": f"cameras/{camera_id}/annotated",
            "source": "publisher",
            "sourceOnDemand": False,
        },
    )
    assert annotated_register in requests

    # ingest_path is the passthrough URL regardless of mode
    assert registration.ingest_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough"
    assert registration.mode is StreamMode.ANNOTATED_WHIP

    await client.close()


@pytest.mark.asyncio
async def test_build_registration_passthrough_mode_registers_only_passthrough() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append((
            request.method,
            str(request.url),
            json.loads(request.content.decode("utf-8")) if request.content else None,
        ))
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        stream_kind="passthrough",
        privacy=PrivacyPolicy(blur_faces=False, blur_plates=False),
    )

    # Only the passthrough path is registered
    passthrough_register_urls = [
        url for _, url, _ in requests
        if f"cameras/{camera_id}/passthrough" in url
    ]
    annotated_register_urls = [
        url for _, url, _ in requests
        if f"cameras/{camera_id}/annotated" in url
    ]
    assert len(passthrough_register_urls) == 1
    assert annotated_register_urls == []

    assert registration.mode is StreamMode.PASSTHROUGH
    assert registration.ingest_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough"

    await client.close()


@pytest.mark.asyncio
async def test_build_registration_privacy_in_passthrough_request_falls_back_to_annotated() -> None:
    requests: list[tuple[str, str, dict[str, object] | None]] = []

    async def handler(request: Request) -> Response:
        requests.append((
            request.method,
            str(request.url),
            json.loads(request.content.decode("utf-8")) if request.content else None,
        ))
        return Response(200, json={"ok": True})

    camera_id = uuid4()
    client = MediaMTXClient(
        api_base_url="http://mediamtx.internal:9997",
        rtsp_base_url="rtsp://mediamtx.internal:8554",
        whip_base_url="http://mediamtx.internal:8889",
        http_client=AsyncClient(transport=_transport(handler)),
    )

    registration = await client.register_stream(
        camera_id=camera_id,
        rtsp_url="rtsp://camera.internal/live",
        profile=PublishProfile.CENTRAL_GPU,
        stream_kind="passthrough",
        privacy=PrivacyPolicy(blur_faces=True, blur_plates=True),
    )

    assert registration.mode is StreamMode.ANNOTATED_WHIP
    assert registration.ingest_path == f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough"

    await client.close()
```

Existing tests must still pass. The existing "registers whip target for central profile" test is superseded by `test_build_registration_always_registers_camera_source_path` — keep both; the new one asserts more. If the older one now fails because it asserted `len(requests) == 1` (only the annotated register), update its expected-requests list to include both registrations.

- [ ] **Step 3: Run streaming tests**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/streaming/test_mediamtx.py -q`
Expected: all pass. Any regression in pre-existing tests → update their expected-request list to reflect the always-registered passthrough path (the test assertions that previously expected `requests == []` or a single `add/annotated` request now need to include the passthrough replace + annotated replace).

- [ ] **Step 4: Lint + type-check**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run ruff check src/argus/streaming/mediamtx.py tests/streaming/test_mediamtx.py && python3 -m uv run mypy src/argus/streaming/mediamtx.py`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/streaming/mediamtx.py backend/tests/streaming/test_mediamtx.py
git commit -m "feat(mediamtx): always relay camera RTSP through passthrough path"
```

---

## Task 5: Worker bootstrap uses `ingest_path`

**Files:**
- Modify: `backend/src/argus/inference/engine.py` (the `build_inference_engine` helper around line 740 onwards + `InferenceEngine.start`)
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Reorder engine construction to register first, then build frame source**

In `backend/src/argus/inference/engine.py`, locate the helper that constructs the engine (function around line 740 — the one that calls `create_camera_source(...)` at line 751 and then `InferenceEngine(...)` at line 844). Currently the frame source is created from `config.camera.rtsp_url` before the engine is instantiated.

Change the order so the stream registration happens first. Specifically:

1. Create a `MediaMTXClient` instance (it is already created around line 851) and move its construction above `create_camera_source`.
2. Call `stream_client.register_stream(...)` to obtain the registration.
3. Build the frame source from `registration.ingest_path` instead of `config.camera.rtsp_url`.
4. Pass the already-registered `registration` into `InferenceEngine.__init__` via a new `initial_registration: StreamRegistration | None = None` parameter.

Concretely, in `build_inference_engine` replace the top of the function:

```python
    stream_client = MediaMTXClient(
        api_base_url=config.publish.mediamtx_api_url,
        rtsp_base_url=config.publish.mediamtx_rtsp_url,
        whip_base_url=config.publish.mediamtx_whip_url,
        publish_token_factory=token_factory,
    )

    registration = await stream_client.register_stream(
        camera_id=config.camera_id,
        rtsp_url=config.camera.rtsp_url,
        profile=_resolve_profile(config, settings),
        stream_kind=config.stream.kind,
        privacy=config.privacy,
        target_fps=config.stream.fps,
        target_width=config.stream.width,
        target_height=config.stream.height,
    )
    logger.info(
        "Worker ingesting from MediaMTX relay at %s (registered for camera %s)",
        registration.ingest_path,
        config.camera_id,
    )

    frame_source = create_camera_source(
        CameraSourceConfig(
            source_uri=registration.ingest_path,
            frame_skip=config.camera.frame_skip,
            fps_cap=config.camera.fps_cap,
        )
    )
```

The existing `MediaMTXClient` construction further down (around line 851) becomes unused — remove it. Pass `stream_client=stream_client` and `initial_registration=registration` into the `InferenceEngine(...)` instantiation at the existing call site.

If `_resolve_profile` doesn't exist yet as a helper, inline the profile-resolution logic that `InferenceEngine.profile` property currently uses:

```python
profile = config.profile if config.profile is not None else PublishProfile.CENTRAL_GPU
```

Use this `profile` variable in the `register_stream` call.

- [ ] **Step 2: Accept pre-built registration in `InferenceEngine.__init__`**

In `InferenceEngine.__init__` (line 268), add a new parameter right before `attribute_classifier`:

```python
        initial_registration: StreamRegistration | None = None,
```

And store it:

```python
        self._initial_registration = initial_registration
```

- [ ] **Step 3: `start()` uses the pre-built registration if available**

Rewrite the first section of `InferenceEngine.start()` (line 327):

```python
    async def start(self) -> None:
        if self._started:
            return
        if self._initial_registration is not None:
            self._stream_registration = self._initial_registration
        else:
            self._stream_registration = await self.stream_client.register_stream(
                camera_id=self.config.camera_id,
                rtsp_url=self.config.camera.rtsp_url,
                profile=self.profile,
                stream_kind=self.config.stream.kind,
                privacy=self._state.privacy,
                target_fps=self.config.stream.fps,
                target_width=self.config.stream.width,
                target_height=self.config.stream.height,
            )
        await self.event_client.subscribe(
            f"cmd.camera.{self.config.camera_id}",
            self._handle_command_message,
        )
        if self.incident_capture is not None:
            await self.incident_capture.start(
                camera_id=self.config.camera_id,
                event_bus=self.event_client,
            )
        self._started = True
```

The else-branch preserves the old behaviour for any existing call site that doesn't pass `initial_registration`.

- [ ] **Step 4: Write test for the bootstrap reorder**

Append to `backend/tests/inference/test_engine.py`. Existing fixtures in that file include `_FakeFrameSource`, `_FakeDetector`, `_FakePublisher`, `_FakeTracker`, `_FakeTrackingStore`, `_FakeRuleEngine`, `_FakeEventClient`, `_FakeStreamClient`, and `_engine_config(camera_id)` — reuse them.

```python
@pytest.mark.asyncio
async def test_engine_uses_initial_registration_without_calling_register_stream() -> None:
    from argus.streaming.mediamtx import StreamMode, StreamRegistration

    camera_id = uuid4()
    registration = StreamRegistration(
        camera_id=camera_id,
        mode=StreamMode.PASSTHROUGH,
        path_name=f"cameras/{camera_id}/passthrough",
        read_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
        managed_path_config=True,
        ingest_path=f"rtsp://mediamtx.internal:8554/cameras/{camera_id}/passthrough",
    )

    stream_client = _FakeStreamClient()
    engine = InferenceEngine(
        config=_engine_config(camera_id),
        frame_source=_FakeFrameSource([np.zeros((32, 32, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _FakeTracker(tracker_type),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=stream_client,
        initial_registration=registration,
    )

    await engine.start()

    assert engine._stream_registration is registration
    # _FakeStreamClient records register_stream calls; expect none
    assert stream_client.register_stream_calls == []
```

If `_FakeStreamClient` doesn't expose a `register_stream_calls` attribute today, grep for it with `grep -n "class _FakeStreamClient" backend/tests/inference/test_engine.py` and add a list attribute + append-in-method pattern analogous to other `_FakeXxx` helpers in the file. Keep the addition minimal: one attribute, one `append` call inside `register_stream`.

- [ ] **Step 5: Run tests**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/inference/test_engine.py -q`
Expected: all pre-existing + new test pass.

- [ ] **Step 6: Lint + types**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run ruff check src/argus/inference/engine.py tests/inference/test_engine.py && python3 -m uv run mypy src/argus/inference/engine.py`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat(worker): ingest frames via MediaMTX relay path (Bug 5)"
```

---

## Task 6: Zustand telemetry store (Bug 4)

**Files:**
- Create: `frontend/src/stores/telemetry-store.ts`
- Create: `frontend/src/stores/telemetry-store.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/stores/telemetry-store.test.ts`:

```typescript
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { createTelemetryStore } from "@/stores/telemetry-store";

class MockWebSocket {
  public onopen: ((this: MockWebSocket, ev: Event) => void) | null = null;
  public onmessage: ((this: MockWebSocket, ev: MessageEvent) => void) | null = null;
  public onerror: ((this: MockWebSocket, ev: Event) => void) | null = null;
  public onclose: ((this: MockWebSocket, ev: CloseEvent) => void) | null = null;
  public readyState: number = 0;
  public closed = false;
  public static instances: MockWebSocket[] = [];

  constructor(public readonly url: string) {
    MockWebSocket.instances.push(this);
  }

  close() {
    this.closed = true;
    this.readyState = 3;
    this.onclose?.call(this, new CloseEvent("close"));
  }

  receive(payload: unknown) {
    this.onmessage?.call(this, new MessageEvent("message", { data: JSON.stringify(payload) }));
  }
}

describe("telemetry-store", () => {
  const originalWS = globalThis.WebSocket;
  beforeEach(() => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = MockWebSocket;
  });
  afterEach(() => {
    vi.useRealTimers();
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = originalWS;
  });

  test("first subscribe opens a single WebSocket", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.subscribe("cam-2");
    expect(MockWebSocket.instances.length).toBe(1);
  });

  test("last unsubscribe keeps the WebSocket open during the idle grace period", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(5_000);
    expect(MockWebSocket.instances[0].closed).toBe(false);
  });

  test("idle grace expires then the socket closes", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(10_500);
    expect(MockWebSocket.instances[0].closed).toBe(true);
  });

  test("resubscribe within grace cancels the timer", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
    });
    store.subscribe("cam-1");
    store.unsubscribe("cam-1");
    vi.advanceTimersByTime(5_000);
    store.subscribe("cam-1");
    vi.advanceTimersByTime(20_000);
    expect(MockWebSocket.instances[0].closed).toBe(false);
  });

  test("ring buffer retains only allowed capacity", () => {
    const store = createTelemetryStore({
      accessToken: "t",
      tenantId: "tenant",
      idleGraceMs: 10_000,
      ringBufferCapacity: 3,
    });
    store.subscribe("cam-1");
    const socket = MockWebSocket.instances[0];
    socket.onopen?.call(socket, new Event("open"));

    for (let i = 0; i < 5; i++) {
      socket.receive({
        camera_id: "cam-1",
        ts: new Date(2026, 3, 24, 14, i).toISOString(),
        counts: { person: i },
        tracks: [],
      });
    }

    const buffer = store.getBuffer("cam-1");
    expect(buffer.length).toBe(3);
    expect(buffer[0].counts.person).toBe(2);
    expect(buffer[2].counts.person).toBe(4);
  });
});
```

- [ ] **Step 2: Run — expect failure**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run src/stores/telemetry-store.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the store**

Create `frontend/src/stores/telemetry-store.ts`:

```typescript
import { create } from "zustand";

import { parseTelemetryPayload, type TelemetryFrame } from "@/lib/live";
import { buildWebSocketUrl } from "@/lib/ws";

export type TelemetryConnectionState = "connecting" | "open" | "closed" | "error";

export type CreateTelemetryStoreOptions = {
  accessToken: string | null;
  tenantId: string | null;
  idleGraceMs?: number;
  ringBufferCapacity?: number;
};

export interface TelemetryStore {
  subscribe: (cameraId: string) => void;
  unsubscribe: (cameraId: string) => void;
  getLatest: (cameraId: string) => TelemetryFrame | null;
  getBuffer: (cameraId: string) => TelemetryFrame[];
  connectionState: () => TelemetryConnectionState;
  onChange: (listener: () => void) => () => void;
}

const DEFAULT_IDLE_GRACE_MS = 10_000;
const DEFAULT_RING_BUFFER_CAPACITY = 6_000;

export function createTelemetryStore(options: CreateTelemetryStoreOptions): TelemetryStore {
  const idleGraceMs = options.idleGraceMs ?? DEFAULT_IDLE_GRACE_MS;
  const capacity = options.ringBufferCapacity ?? DEFAULT_RING_BUFFER_CAPACITY;

  const subscribers = new Map<string, number>();
  const buffers = new Map<string, TelemetryFrame[]>();
  const latest = new Map<string, TelemetryFrame>();
  const listeners = new Set<() => void>();
  let socket: WebSocket | null = null;
  let connectionState: TelemetryConnectionState = "closed";
  let idleTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const notify = () => {
    listeners.forEach((l) => l());
  };

  const openSocket = () => {
    if (socket || !options.accessToken) return;
    connectionState = "connecting";
    const ws = new WebSocket(
      buildWebSocketUrl("/ws/telemetry", {
        access_token: options.accessToken,
        tenant_id: options.tenantId,
      }),
    );
    socket = ws;
    ws.onopen = () => {
      connectionState = "open";
      notify();
    };
    ws.onerror = () => {
      connectionState = "error";
      notify();
    };
    ws.onclose = () => {
      socket = null;
      connectionState = "closed";
      notify();
      if (subscribers.size > 0) {
        reconnectTimer = setTimeout(openSocket, 1_500);
      }
    };
    ws.onmessage = (event) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(String(event.data));
      } catch {
        return;
      }
      const frames = parseTelemetryPayload(parsed);
      if (frames.length === 0) return;
      for (const frame of frames) {
        if (!subscribers.has(frame.camera_id)) continue;
        latest.set(frame.camera_id, frame);
        const buffer = buffers.get(frame.camera_id) ?? [];
        buffer.push(frame);
        if (buffer.length > capacity) {
          buffer.splice(0, buffer.length - capacity);
        }
        buffers.set(frame.camera_id, buffer);
      }
      notify();
    };
  };

  const closeSocket = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket?.close();
    socket = null;
  };

  const scheduleIdleClose = () => {
    if (idleTimer !== null) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      if (subscribers.size === 0) {
        closeSocket();
      }
      idleTimer = null;
    }, idleGraceMs);
  };

  return {
    subscribe(cameraId) {
      if (idleTimer !== null) {
        clearTimeout(idleTimer);
        idleTimer = null;
      }
      subscribers.set(cameraId, (subscribers.get(cameraId) ?? 0) + 1);
      if (!socket) openSocket();
    },
    unsubscribe(cameraId) {
      const next = (subscribers.get(cameraId) ?? 1) - 1;
      if (next <= 0) {
        subscribers.delete(cameraId);
      } else {
        subscribers.set(cameraId, next);
      }
      if (subscribers.size === 0) scheduleIdleClose();
    },
    getLatest(cameraId) {
      return latest.get(cameraId) ?? null;
    },
    getBuffer(cameraId) {
      return buffers.get(cameraId) ?? [];
    },
    connectionState() {
      return connectionState;
    },
    onChange(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

type StoreHolder = {
  instance: TelemetryStore | null;
  accessToken: string | null;
  tenantId: string | null;
};

export const useTelemetryStore = create<StoreHolder>(() => ({
  instance: null,
  accessToken: null,
  tenantId: null,
}));

export function ensureTelemetryStore(
  accessToken: string | null,
  tenantId: string | null,
): TelemetryStore | null {
  if (!accessToken) return null;
  const state = useTelemetryStore.getState();
  if (
    state.instance &&
    state.accessToken === accessToken &&
    state.tenantId === tenantId
  ) {
    return state.instance;
  }
  const instance = createTelemetryStore({ accessToken, tenantId });
  useTelemetryStore.setState({ instance, accessToken, tenantId });
  return instance;
}
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run src/stores/telemetry-store.test.ts`
Expected: 5 passed.

- [ ] **Step 5: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/stores/telemetry-store.ts frontend/src/stores/telemetry-store.test.ts
git commit -m "feat(telemetry): app-level telemetry store with ring buffer and idle grace"
```

---

## Task 7: Rewrite `useLiveTelemetry` over the store

**Files:**
- Modify: `frontend/src/hooks/use-live-telemetry.ts`

- [ ] **Step 1: Replace the hook entirely**

Replace `frontend/src/hooks/use-live-telemetry.ts` with:

```typescript
import { useEffect, useMemo, useState } from "react";

import { ensureTelemetryStore } from "@/stores/telemetry-store";
import type { TelemetryConnectionState } from "@/stores/telemetry-store";
import type { TelemetryFrame } from "@/lib/live";
import { useAuthStore } from "@/stores/auth-store";

export type { TelemetryConnectionState };

export function useLiveTelemetry(cameraIds: string[]) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const [framesByCamera, setFramesByCamera] = useState<Record<string, TelemetryFrame>>({});
  const [connectionState, setConnectionState] = useState<TelemetryConnectionState>("closed");

  const cameraKey = useMemo(() => [...cameraIds].sort().join(","), [cameraIds]);

  useEffect(() => {
    const store = ensureTelemetryStore(accessToken, tenantId);
    if (!store) {
      setConnectionState("closed");
      setFramesByCamera({});
      return;
    }

    const ids = cameraKey ? cameraKey.split(",") : [];
    ids.forEach((id) => store.subscribe(id));
    const unsubscribe = store.onChange(() => {
      setConnectionState(store.connectionState());
      setFramesByCamera((current) => {
        const next: Record<string, TelemetryFrame> = {};
        for (const id of ids) {
          const frame = store.getLatest(id);
          if (frame) {
            next[id] = frame;
          } else if (current[id]) {
            next[id] = current[id];
          }
        }
        return next;
      });
    });

    return () => {
      unsubscribe();
      ids.forEach((id) => store.unsubscribe(id));
    };
  }, [accessToken, tenantId, cameraKey]);

  return {
    connectionState,
    framesByCamera,
  } as const;
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 3: Run existing vitest to confirm no regressions**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run`
Expected: all existing tests continue to pass. If a test relied on the old `useLiveTelemetry` internals (creating its own `WebSocket` mock inside the hook), it continues to work because the new hook also creates a WebSocket via the store.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-live-telemetry.ts
git commit -m "refactor(telemetry): route useLiveTelemetry through shared store"
```

---

## Task 8: IA consolidation — delete wrapper, rename, redirect, drop nav entry

**Files:**
- Delete: `frontend/src/pages/Live.tsx` (the wrapper)
- Rename: `frontend/src/pages/Dashboard.tsx` → `frontend/src/pages/Live.tsx` via `git mv`
- Modify: `frontend/src/app/router.tsx`
- Modify: `frontend/src/components/layout/TopNav.tsx`

- [ ] **Step 1: Delete the Live.tsx wrapper**

```bash
cd /Users/yann.moren/vision
git rm frontend/src/pages/Live.tsx
```

- [ ] **Step 2: Rename Dashboard.tsx to Live.tsx**

```bash
cd /Users/yann.moren/vision
git mv frontend/src/pages/Dashboard.tsx frontend/src/pages/Live.tsx
```

- [ ] **Step 3: Rename the exported component inside the file**

Open the new `frontend/src/pages/Live.tsx`. Find the two exports `DashboardPage` and `LivePage` (the file previously exported both, with one thin wrapper). Replace them with a single `LivePage` export. The `LivePage` wrapper and `DashboardPage` were re-using `WorkspacePage` with different labels; drop the `workspaceLabel` prop entirely or hardcode `"Live"` inside `WorkspacePage`. The simplest change:

- Remove `DashboardPage` entirely if present.
- Rename any `function LivePage()` / `function DashboardPage()` body to a single `export function LivePage()` that passes `workspaceLabel="Live"` to `WorkspacePage`.

Use `grep` to confirm the exact shape: `grep -n "export function\|workspaceLabel" frontend/src/pages/Live.tsx`.

- [ ] **Step 4: Update router.tsx**

Replace `frontend/src/app/router.tsx` lines 42–54 region. Original:

```tsx
      { index: true, element: <Navigate to="dashboard" replace /> },
      {
        path: "dashboard",
        lazy: async () => ({
          Component: (await import("@/pages/Dashboard")).DashboardPage,
        }),
      },
      {
        path: "live",
        lazy: async () => ({
          Component: (await import("@/pages/Live")).LivePage,
        }),
      },
```

Replace with:

```tsx
      { index: true, element: <Navigate to="live" replace /> },
      { path: "dashboard", element: <Navigate to="/live" replace /> },
      {
        path: "live",
        lazy: async () => ({
          Component: (await import("@/pages/Live")).LivePage,
        }),
      },
```

- [ ] **Step 5: Drop the Dashboard nav entry**

In `frontend/src/components/layout/TopNav.tsx`, find the `workspaceNavGroups` declaration (around line 27–36) and remove the "Dashboard" entry from the `Operations` items array:

```tsx
  {
    label: "Operations",
    items: [
      { label: "Live", to: "/live", icon: Radio },
      { label: "History", to: "/history", icon: Clock3 },
      { label: "Incidents", to: "/incidents", icon: ShieldAlert },
    ],
  },
```

Also remove the `LayoutDashboard` icon from the lucide-react imports at the top of the file if nothing else uses it — run `grep "LayoutDashboard" frontend/src/components/layout/TopNav.tsx` after the edit.

- [ ] **Step 6: Update any remaining `/dashboard` links**

Run: `grep -rn '"/dashboard"\|to="dashboard"\|/dashboard' frontend/src --exclude-dir=node_modules`

For each non-router occurrence, either change the link to `/live` or leave as-is (the redirect handles it). Tests that expect `/dashboard` in URLs should be updated to `/live`; the redirect means the landing URL is `/live` not `/dashboard`.

- [ ] **Step 7: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0. If `DashboardPage` is imported anywhere else, update those imports to `LivePage`.

- [ ] **Step 8: Run the full vitest suite**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run`
Expected: all tests pass. Any test that imports `Dashboard` or hits `/dashboard` needs updating.

- [ ] **Step 9: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/Live.tsx frontend/src/app/router.tsx frontend/src/components/layout/TopNav.tsx
git add -u   # stages the deleted Live.tsx wrapper + the Dashboard.tsx rename
git commit -m "refactor(ia): consolidate Dashboard and Live into a single Live page"
```

If Step 6 prompted changes to any non-router files (tests, other components), stage and commit them with the same commit.

---

## Task 9: Live sparkline hook

**Files:**
- Create: `frontend/src/hooks/use-live-sparkline.ts`

- [ ] **Step 1: Implement the hook**

Create `frontend/src/hooks/use-live-sparkline.ts`:

```typescript
import { useEffect, useMemo, useRef, useState } from "react";

import { apiClient, toApiError } from "@/lib/api";
import type { TelemetryFrame } from "@/lib/live";
import { ensureTelemetryStore } from "@/stores/telemetry-store";
import { useAuthStore } from "@/stores/auth-store";

const BUCKET_COUNT = 30;
const BUCKET_MS = 60_000;

export type SparklineBuckets = Record<string, number[]>;
export type SparklineTotals = Record<string, number>;

export type UseLiveSparklineResult = {
  buckets: SparklineBuckets;
  totals: SparklineTotals;
  loading: boolean;
  error: Error | null;
};

function floorMinute(value: number): number {
  return value - (value % BUCKET_MS);
}

function bucketIndex(tsMs: number, windowEndMs: number): number {
  const diff = Math.floor((windowEndMs - tsMs) / BUCKET_MS);
  return BUCKET_COUNT - 1 - diff;
}

function emptyBuckets(classes: string[]): SparklineBuckets {
  const out: SparklineBuckets = {};
  for (const cls of classes) {
    out[cls] = new Array(BUCKET_COUNT).fill(0);
  }
  return out;
}

function addCounts(
  buckets: SparklineBuckets,
  classesCount: Record<string, number>,
  index: number,
): SparklineBuckets {
  const next: SparklineBuckets = { ...buckets };
  for (const [cls, count] of Object.entries(classesCount)) {
    const series = next[cls] ?? new Array(BUCKET_COUNT).fill(0);
    const copy = series.slice();
    copy[index] = (copy[index] ?? 0) + count;
    next[cls] = copy;
  }
  return next;
}

export function useLiveSparkline(cameraId: string): UseLiveSparklineResult {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const windowEndRef = useRef<number>(floorMinute(Date.now()));
  const [buckets, setBuckets] = useState<SparklineBuckets>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  // Seed from history
  useEffect(() => {
    let cancelled = false;
    const now = new Date();
    const fromDate = new Date(now.getTime() - BUCKET_COUNT * BUCKET_MS);
    windowEndRef.current = floorMinute(now.getTime());
    (async () => {
      try {
        const { data, error: apiError } = await apiClient.GET(
          "/api/v1/history/series",
          {
            params: {
              query: {
                granularity: "1m",
                from: fromDate.toISOString(),
                to: now.toISOString(),
                camera_ids: [cameraId],
              },
            },
          },
        );
        if (cancelled) return;
        if (apiError || !data) {
          throw toApiError(apiError, "Failed to seed sparkline.");
        }
        const classNames = data.class_names ?? [];
        const seed = emptyBuckets(classNames);
        for (const row of data.rows ?? []) {
          const tsMs = Date.parse(row.bucket);
          const idx = bucketIndex(tsMs, windowEndRef.current);
          if (idx < 0 || idx >= BUCKET_COUNT) continue;
          for (const [cls, count] of Object.entries(row.values ?? {})) {
            const series = seed[cls] ?? new Array(BUCKET_COUNT).fill(0);
            series[idx] = (series[idx] ?? 0) + count;
            seed[cls] = series;
          }
        }
        setBuckets(seed);
      } catch (err) {
        if (!cancelled) setError(err as Error);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cameraId]);

  // Live updates from telemetry store
  useEffect(() => {
    const store = ensureTelemetryStore(accessToken, tenantId);
    if (!store) return;
    store.subscribe(cameraId);
    let lastFrame: TelemetryFrame | null = null;
    const unsubscribe = store.onChange(() => {
      const frame = store.getLatest(cameraId);
      if (!frame || frame === lastFrame) return;
      lastFrame = frame;
      const tsMs = Date.parse(frame.ts);
      const end = windowEndRef.current;
      if (tsMs < end - BUCKET_COUNT * BUCKET_MS) return;
      const idx = bucketIndex(tsMs, end);
      if (idx < 0 || idx >= BUCKET_COUNT) return;
      setBuckets((current) => addCounts(current, frame.counts ?? {}, idx));
    });
    return () => {
      unsubscribe();
      store.unsubscribe(cameraId);
    };
  }, [cameraId, accessToken, tenantId]);

  // Minute rollover
  useEffect(() => {
    const id = setInterval(() => {
      windowEndRef.current = floorMinute(Date.now());
      setBuckets((current) => {
        const next: SparklineBuckets = {};
        for (const [cls, series] of Object.entries(current)) {
          next[cls] = [...series.slice(1), 0];
        }
        return next;
      });
    }, BUCKET_MS);
    return () => clearInterval(id);
  }, []);

  const totals = useMemo(() => {
    const out: SparklineTotals = {};
    for (const [cls, series] of Object.entries(buckets)) {
      out[cls] = series.reduce((a, b) => a + b, 0);
    }
    return out;
  }, [buckets]);

  return { buckets, totals, loading, error };
}
```

- [ ] **Step 2: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 3: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-live-sparkline.ts
git commit -m "feat(live): useLiveSparkline hook with history seed + WS live updates"
```

---

## Task 10: LiveSparkline component

**Files:**
- Create: `frontend/src/components/live/LiveSparkline.tsx`
- Create: `frontend/src/components/live/LiveSparkline.test.tsx`

- [ ] **Step 1: Write failing tests**

Create `frontend/src/components/live/LiveSparkline.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

vi.mock("@/hooks/use-live-sparkline", () => ({
  useLiveSparkline: () => ({
    buckets: {
      person: [1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      car: [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      truck: [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      bicycle: [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      bus: [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    },
    totals: { person: 15, car: 1, truck: 1, bicycle: 1, bus: 1 },
    loading: false,
    error: null,
  }),
}));

import { LiveSparkline } from "@/components/live/LiveSparkline";

describe("LiveSparkline", () => {
  test("renders top 3 classes by total", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    expect(screen.getByText(/person/i)).toBeInTheDocument();
    // top 3 by total: person(15), car(1), truck(1) — any two of the 1-count classes may tie for 2nd/3rd; accept that
    const visibleClasses = ["person", "car", "truck", "bicycle", "bus"].filter(
      (cls) => screen.queryByText(new RegExp(`\\b${cls}\\b`, "i")) !== null,
    );
    expect(visibleClasses.length).toBeGreaterThanOrEqual(3);
  });

  test("shows the +N more button when there are more than 3 classes", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    expect(screen.getByRole("button", { name: /\+2 more/i })).toBeInTheDocument();
  });

  test("expands to show all classes after clicking +N more", async () => {
    const user = userEvent.setup();
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck", "bicycle", "bus"]} />);
    await user.click(screen.getByRole("button", { name: /\+2 more/i }));
    expect(screen.getByText(/bicycle/i)).toBeInTheDocument();
    expect(screen.getByText(/bus/i)).toBeInTheDocument();
  });

  test("renders totals next to each class", () => {
    render(<LiveSparkline cameraId="cam-1" activeClasses={["person", "car", "truck"]} />);
    expect(screen.getByText("15")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run — expect failure**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run src/components/live/LiveSparkline.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

Create `frontend/src/components/live/LiveSparkline.tsx`:

```typescript
import { useMemo, useState } from "react";

import { useLiveSparkline } from "@/hooks/use-live-sparkline";

const PALETTE = ["#4f8cff", "#8b6dff", "#26d0ff", "#6de4a7", "#ffaf52", "#ff6b91", "#c28bff", "#f5d570"];
const TOP_N = 3;

type LiveSparklineProps = {
  cameraId: string;
  activeClasses: string[];
};

type RowProps = {
  className: string;
  color: string;
  series: number[];
  total: number;
};

function SparklineRow({ className, color, series, total }: RowProps) {
  const max = Math.max(1, ...series);
  const points = useMemo(
    () =>
      series
        .map((value, index) => {
          const x = (index / (series.length - 1)) * 100;
          const y = 100 - (value / max) * 100;
          return `${x.toFixed(2)},${y.toFixed(2)}`;
        })
        .join(" "),
    [series, max],
  );
  return (
    <div className="flex items-center gap-2 text-xs text-[#d9e5f7]">
      <span className="w-16 truncate font-medium">{className}</span>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="h-5 flex-1"
        aria-label={`${className} sparkline`}
      >
        <polyline
          fill="none"
          stroke={color}
          strokeWidth="3"
          vectorEffect="non-scaling-stroke"
          points={points}
        />
      </svg>
      <span className="w-10 text-right tabular-nums text-[#8ea8cf]">{total}</span>
    </div>
  );
}

export function LiveSparkline({ cameraId, activeClasses }: LiveSparklineProps) {
  const { buckets, totals, loading, error } = useLiveSparkline(cameraId);
  const [showAll, setShowAll] = useState(false);

  const ranked = useMemo(
    () =>
      activeClasses
        .map((cls) => [cls, totals[cls] ?? 0] as const)
        .sort(([, a], [, b]) => b - a)
        .map(([cls]) => cls),
    [activeClasses, totals],
  );
  const top = ranked.slice(0, TOP_N);
  const rest = ranked.slice(TOP_N);

  if (loading) {
    return <div className="h-16 animate-pulse rounded-md bg-white/[0.04]" />;
  }
  if (error) {
    return <p className="text-xs text-[#f0b7c1]">Sparkline unavailable: {error.message}</p>;
  }

  const renderRow = (cls: string, index: number) => (
    <SparklineRow
      key={cls}
      className={cls}
      color={PALETTE[index % PALETTE.length]}
      series={buckets[cls] ?? []}
      total={totals[cls] ?? 0}
    />
  );

  return (
    <div className="space-y-1.5">
      {top.map((cls, index) => renderRow(cls, index))}
      {rest.length > 0 && !showAll && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="text-xs text-[#8ea8cf] underline"
        >
          +{rest.length} more
        </button>
      )}
      {showAll && rest.map((cls, index) => renderRow(cls, TOP_N + index))}
    </div>
  );
}
```

- [ ] **Step 4: Run tests — expect pass**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run src/components/live/LiveSparkline.test.tsx`
Expected: 4 passed.

- [ ] **Step 5: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/components/live/LiveSparkline.tsx frontend/src/components/live/LiveSparkline.test.tsx
git commit -m "feat(live): LiveSparkline component with top-3 + expander"
```

---

## Task 11: Integrate sparkline into Live tile

**Files:**
- Modify: `frontend/src/pages/Live.tsx` (the renamed page from Task 8)

- [ ] **Step 1: Find the tile rendering block**

Run: `grep -n "heartbeat\|stream_mode\|aspect-video\|<article" frontend/src/pages/Live.tsx | head -10`

The camera card is an `<article>` around the video element. Per the earlier explore, the existing card structure in `Dashboard.tsx` (now `Live.tsx`) renders video + overlay + footer at approximately lines 137–181 of the pre-rename file.

- [ ] **Step 2: Import LiveSparkline**

Add to the imports at the top of `frontend/src/pages/Live.tsx`:

```tsx
import { LiveSparkline } from "@/components/live/LiveSparkline";
```

- [ ] **Step 3: Render sparkline in each card's footer**

In the card-rendering map (each `<article>`), add `<LiveSparkline>` after the existing footer content. Example placement (you'll need to adapt to the exact existing JSX shape — keep whatever wraps the footer):

```tsx
<div className="space-y-3 px-4 pb-4 pt-2">
  {/* existing heartbeat / count overlay preserved */}
  <LiveSparkline
    cameraId={camera.id}
    activeClasses={camera.active_classes ?? []}
  />
</div>
```

The `camera.active_classes` comes from the camera object already passed to the card renderer; the sparkline reads per-class buckets only for the classes in this list.

- [ ] **Step 4: Typecheck**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 5: Run existing vitest for regression**

Run: `cd /Users/yann.moren/vision/frontend && corepack pnpm exec vitest run`
Expected: all pass. The mock in `Dashboard.test.tsx` (now effectively testing `Live.tsx`) may need the `LiveSparkline` import mocked. If a test fails with a render error inside `LiveSparkline`, add this to the top of that test file:

```tsx
vi.mock("@/components/live/LiveSparkline", () => ({
  LiveSparkline: () => <div data-testid="live-sparkline-mock" />,
}));
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/pages/Live.tsx
# If Step 5 required test-file tweaks, add those files too
git commit -m "feat(live): embed LiveSparkline in each camera tile"
```

---

## Task 12: Playwright end-to-end scenarios

**Files:**
- Modify: `frontend/e2e/prompt8-live-dashboard.spec.ts` (or the closest live e2e spec — check with `ls frontend/e2e`)

- [ ] **Step 1: Locate the target file**

Run: `ls frontend/e2e/*.spec.ts`

If `prompt8-live-dashboard.spec.ts` exists, edit it. Otherwise pick the closest live/dashboard e2e spec and edit it. If none exist, create `frontend/e2e/live-dashboard-refresh.spec.ts` with the same top-matter as other e2e specs (imports from `@playwright/test`).

- [ ] **Step 2: Append the new scenarios**

Add these two tests to the chosen file:

```typescript
test("visiting /dashboard redirects to /live and only shows Live in Operations nav", async ({ page }) => {
  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/live$/);

  const operationsNav = page.locator("nav").getByRole("link");
  await expect(operationsNav.filter({ hasText: /^Dashboard$/ })).toHaveCount(0);
  await expect(operationsNav.filter({ hasText: /^Live$/ })).toHaveCount(1);
});

test("live sparkline renders with seeded data and does not reset on history round-trip", async ({ page }) => {
  await page.route("**/api/v1/cameras", async (route) => {
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "11111111-1111-1111-1111-111111111111",
          site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          edge_node_id: null,
          name: "Gate 1",
          rtsp_url_masked: "rtsp://***",
          processing_mode: "central",
          primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          secondary_model_id: null,
          tracker_type: "botsort",
          active_classes: ["person", "car"],
          attribute_rules: [],
          zones: [],
          homography: null,
          privacy: { blur_faces: false, blur_plates: false, method: "gaussian", strength: 7 },
          browser_delivery: { default_profile: "720p10", allow_native_on_demand: true, profiles: [] },
          frame_skip: 1,
          fps_cap: 25,
          created_at: "2026-04-24T10:00:00Z",
          updated_at: "2026-04-24T10:00:00Z",
        },
      ]),
    });
  });

  await page.route("**/api/v1/history/series**", async (route) => {
    const rows = [];
    const start = Date.now() - 29 * 60 * 1000;
    for (let i = 0; i < 30; i++) {
      rows.push({
        bucket: new Date(start + i * 60 * 1000).toISOString(),
        values: { person: (i % 5) + 1, car: i % 3 },
        total_count: ((i % 5) + 1) + (i % 3),
      });
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        granularity: "1m",
        class_names: ["person", "car"],
        rows,
        granularity_adjusted: false,
        speed_classes_capped: false,
        speed_classes_used: null,
      }),
    });
  });

  await page.goto("/signin");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.locator("#username").fill("admin-dev");
  await page.locator("#password").fill("argus-admin-pass");
  await page.locator("#kc-login").click();

  await expect(page).toHaveURL(/\/live$/);
  await expect(page.getByLabel(/person sparkline/i)).toBeVisible();
  await expect(page.getByLabel(/car sparkline/i)).toBeVisible();

  await page.getByRole("link", { name: "History" }).click();
  await expect(page).toHaveURL(/\/history/);
  await page.getByRole("link", { name: "Live" }).click();
  await expect(page).toHaveURL(/\/live$/);
  await expect(page.getByLabel(/person sparkline/i)).toBeVisible();
});
```

- [ ] **Step 3: TypeScript check on the e2e file**

Run: `cd /Users/yann.moren/vision/frontend && npx tsc --noEmit`
Expected: exits 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/e2e/prompt8-live-dashboard.spec.ts
git commit -m "test(e2e): live dashboard redirect + sparkline seed + round-trip scenarios"
```

(If you created a new file in Step 1 instead, replace the path accordingly.)

---

## Task 13: Final verification

- [ ] **Step 1: Backend full regression**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest -q`
Expected: all tests pass (modulo the pre-existing `tests/api/test_prompt9_routes.py` failure that Spec B's Final Verification already noted — if it re-appears, it's pre-existing and unrelated; leave it alone).

- [ ] **Step 2: Backend lint + typecheck on touched files**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run ruff check \
  src/argus/vision/detector.py \
  src/argus/services/app.py \
  src/argus/streaming/mediamtx.py \
  src/argus/inference/engine.py \
  tests/vision/test_detector_rescale.py \
  tests/services/test_history_service.py \
  tests/streaming/test_mediamtx.py \
  tests/inference/test_engine.py
python3 -m uv run mypy \
  src/argus/vision/detector.py \
  src/argus/services/app.py \
  src/argus/streaming/mediamtx.py \
  src/argus/inference/engine.py
```

Expected: both clean.

- [ ] **Step 3: Frontend full regression + typecheck**

Run:

```bash
cd /Users/yann.moren/vision/frontend
corepack pnpm exec vitest run
npx tsc --noEmit
```

Expected: all tests pass, tsc exits 0.

- [ ] **Step 4: Bug 2 verification on the iMac (manual)**

Pull the branch on the iMac and run the worker under `ARGUS_WORKER_DIAGNOSTICS_ENABLED=true`. Walk in front of the camera. Observe whether the person count stabilises on a single detection (one track_id per physical person) rather than incrementing per frame.

If tracker IDs are still unstable:
- Share the last ~30 lines of `/tmp/argus-worker.log` where you're in frame.
- The follow-up commit goes in `backend/src/argus/vision/tracker.py`, targeted at whatever the diagnostic log shows. The plan considers this branch contingent on observed behaviour.

If tracker IDs are stable, Bug 2 is resolved by Bug 1's fix — no additional work.

- [ ] **Step 5: End-to-end smoke on the iMac dev stack**

```bash
cd "$HOME/vision"
git pull --ff-only
docker compose -f infra/docker-compose.dev.yml up -d --force-recreate backend frontend
# then the worker command from CLAUDE.md with diagnostics on
```

Walk through:

1. Visit `http://localhost:3000/dashboard` → redirects to `/live`.
2. Operations nav shows only `Live / History / Incidents`, no Dashboard.
3. Camera tile renders video + counter + sparkline (the sparkline should have ≤30 minutes of seeded history).
4. When a person is detected, the **bounding box in the TelemetryCanvas lands on the person**, not the top-left corner.
5. Navigate to `/history`, confirm the default (no "Show speed") chart renders rows (Bug 3 gone).
6. Navigate back to `/live` within 5 s, sparkline stays populated, counters resume (Bug 4 gone).
7. Switch camera to passthrough/native mode in the camera settings, restart worker. Worker should now ingest via MediaMTX (per startup log line), no more "Stream timeout triggered after 30026 ms". Detection continues to fire (Bug 5 gone).

If all 7 succeed, the spec is implementation-complete.

- [ ] **Step 6: Sync branch status**

Run: `git log --oneline new-features ^main | head -20`
Expected: 12 commits on top of the spec commit, each well-scoped.

---

## Known Deferred

- **Bug 2 deeper fix**: happens only if the iMac smoke shows tracker ID drift even after Bug 1.
- **Per-camera homography tag** in speed legend: still Spec B follow-up.
- **Observability cleanup** (Tempo, Prometheus, otel-collector): still Spec C.
- **Attribute-driven filtering** (person with a hat): still Spec D.
- **TimescaleDB realtime aggregates**: not needed; reading `tracking_events` directly suffices. Re-evaluate only at fleet scale.
