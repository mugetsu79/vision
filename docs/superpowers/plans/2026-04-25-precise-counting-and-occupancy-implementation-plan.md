# Precise Counting and Occupancy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add precise count events (`line_cross`, `zone_enter`, `zone_exit`) while keeping Live occupancy stable, preserving multi-object tracking and speed measurement, and making History explicitly metric-aware.

**Architecture:** Keep `tracking_events` as the observation stream, add a new durable `count_events` stream for operational counting, and make the history API select between `occupancy`, `count_events`, and `observations`. On the worker side, reuse the existing `zones` payload for both polygon zones and line boundaries, run a generic count-event processor after tracking/zone assignment, and persist those events separately from frame observations.

**Tech Stack:** FastAPI + Pydantic + SQLAlchemy async + Alembic + TimescaleDB; Python worker pipeline in `argus.inference.engine`; React 19 + TanStack Query v5 + Vitest + React Router v6.

---

## File Structure

**Backend — create:**
- `backend/src/argus/vision/count_events.py` — generic count-event processor for line crossing and zone entry/exit, including short dedupe for tracker churn near boundaries.
- `backend/src/argus/migrations/versions/0004_prompt12_count_events.py` — schema migration for `count_events`, Timescale hypertable setup, and `count_events_1m` / `count_events_1h` continuous aggregates.
- `backend/tests/vision/test_count_events.py` — focused unit tests for line crossing direction, zone transitions, and duplicate suppression.

**Backend — modify:**
- `backend/src/argus/models/enums.py` — add `HistoryMetric` and `CountEventType`.
- `backend/src/argus/models/tables.py` — add `CountEvent`.
- `backend/src/argus/core/db.py` — add `CountEventStore`.
- `backend/src/argus/api/contracts.py` — add metric-aware history contracts and `CountEventBoundarySummary`.
- `backend/src/argus/api/v1/history.py` — accept `metric` query parameter on `/history`, `/history/series`, and `/history/classes`.
- `backend/src/argus/services/app.py` — route history queries by metric; query `count_events` and `tracking_events` with the correct semantics.
- `backend/src/argus/inference/engine.py` — wire generic count-event processing and persistence after zone assignment and before telemetry publish/persistence.
- `backend/src/argus/vision/anpr.py` — keep current behavior but reuse the new direction helper so ANPR and generic counting agree on line-side math.

**Backend — extend existing tests:**
- `backend/tests/core/test_db.py` — verify `CountEventStore` creates rows with payload/speed data intact.
- `backend/tests/inference/test_engine.py` — verify the engine emits and persists generic count events while still publishing telemetry.
- `backend/tests/services/test_history_service.py` — verify all three metrics (`occupancy`, `count_events`, `observations`) query the correct storage.
- `backend/tests/api/test_history_endpoints.py` — verify `metric` reaches the service and serializes in responses.

**Frontend — modify:**
- `frontend/src/hooks/use-live-sparkline.ts` — represent occupancy buckets from frame snapshots, keep each bucket as the maximum visible occupancy seen in that minute, and expose latest-bucket occupancy instead of 30-minute cumulative sums.
- `frontend/src/components/live/LiveSparkline.tsx` — rename/right-size labels from cumulative totals to “visible now” semantics.
- `frontend/src/pages/Live.tsx` — change tile copy from “visible detections” to “visible now”.
- `frontend/src/lib/history-url-state.ts` — add `metric` filter to URL state.
- `frontend/src/hooks/use-history.ts` — add `metric` to query keys and history API calls.
- `frontend/src/pages/History.tsx` — add metric selector, change labels/descriptions based on metric, and default to `count_events` when selected cameras contain count boundaries.
- `frontend/src/components/history/HistoryTrendChart.tsx` — update chart legend/axis copy to reflect the chosen metric.
- `frontend/src/lib/api.generated.ts` — regenerate after the backend OpenAPI changes.

**Frontend — extend existing tests:**
- `frontend/src/hooks/use-live-sparkline.test.tsx` — verify current-minute occupancy does not accumulate frame-by-frame for a stable track.
- `frontend/src/components/live/LiveSparkline.test.tsx` — verify latest occupancy values render instead of 30-minute totals.
- `frontend/src/pages/Live.test.tsx` — verify “visible now” copy.
- `frontend/src/pages/History.test.tsx` — verify metric selection, URL hydration, and count-event defaulting.

**Docs — modify after code lands:**
- `README.md` — explain the split between occupancy and count events.
- `product-spec-v4.md` — mark precise counting as event-based and metric-aware.
- `ai-coder-prompt-v4.md` — update implementation guardrails so future work does not collapse occupancy and cumulative counts again.

**Out of scope for this plan:**
- separate camera-admin UI for authoring line boundaries; this plan reuses the existing `zones` payload shape where `type: "line"` already reaches the worker today.
- cross-camera ReID or “perfect identity” counting.

---

## Task 1: Add Metric and Count Event Schema Primitives

**Files:**
- Modify: `backend/src/argus/models/enums.py`
- Modify: `backend/src/argus/models/tables.py`
- Modify: `backend/src/argus/api/contracts.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Write the failing contract/store test**

Append to `backend/tests/core/test_db.py`:

```python
from datetime import UTC, datetime
from uuid import uuid4

from argus.core.db import CountEventStore
from argus.models.enums import CountEventType


class _CaptureSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    def add_all(self, rows):
        self.added.extend(rows)

    async def commit(self) -> None:
        self.committed = True


class _CaptureSessionFactory:
    def __init__(self, session: _CaptureSession) -> None:
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self) -> _CaptureSession:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


@pytest.mark.asyncio
async def test_count_event_store_persists_speed_and_boundary_metadata() -> None:
    session = _CaptureSession()
    store = CountEventStore(_CaptureSessionFactory(session))
    camera_id = uuid4()

    await store.record(
        camera_id=camera_id,
        events=[
            {
                "ts": datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
                "class_name": "car",
                "track_id": 7,
                "event_type": CountEventType.LINE_CROSS,
                "boundary_id": "driveway-main",
                "direction": "negative-to-positive",
                "from_zone_id": None,
                "to_zone_id": None,
                "speed_kph": 37.5,
                "confidence": 0.92,
                "attributes": {"color": "blue"},
                "payload": {"profile_id": "540p5"},
            }
        ],
    )

    assert session.committed is True
    assert len(session.added) == 1
    row = session.added[0]
    assert row.camera_id == camera_id
    assert row.class_name == "car"
    assert row.boundary_id == "driveway-main"
    assert row.event_type == CountEventType.LINE_CROSS
    assert row.speed_kph == 37.5
    assert row.payload == {"profile_id": "540p5"}
```

- [ ] **Step 2: Run the failing test**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/core/test_db.py -q`

Expected: FAIL with `ImportError` / `AttributeError` because `CountEventStore` and `CountEventType` do not exist yet.

- [ ] **Step 3: Add enum and table primitives**

In `backend/src/argus/models/enums.py`, append:

```python
class HistoryMetric(StrEnum):
    OCCUPANCY = "occupancy"
    COUNT_EVENTS = "count_events"
    OBSERVATIONS = "observations"


class CountEventType(StrEnum):
    LINE_CROSS = "line_cross"
    ZONE_ENTER = "zone_enter"
    ZONE_EXIT = "zone_exit"
```

In `backend/src/argus/models/tables.py`, extend imports and add the model immediately after `TrackingEvent`:

```python
from argus.models.enums import (
    CountEventType,
    HistoryMetric,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    RoleEnum,
    RuleAction,
    TrackerType,
)
```

```python
class CountEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "count_events"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True, nullable=False)
    camera_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cameras.id"),
        nullable=False,
    )
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_type: Mapped[CountEventType] = mapped_column(
        enum_column(CountEventType, "count_event_type_enum"),
        nullable=False,
    )
    boundary_id: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str | None] = mapped_column(String(64), nullable=True)
    from_zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_zone_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    attributes: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
```

In `backend/src/argus/api/contracts.py`, add the new metric-aware history types near the existing history models:

```python
from argus.models.enums import (
    CountEventType,
    HistoryMetric,
    ModelFormat,
    ModelTask,
    ProcessingMode,
    TrackerType,
)
```

```python
class CountEventBoundarySummary(BaseModel):
    boundary_id: str
    event_types: list[CountEventType]


class HistoryPoint(BaseModel):
    bucket: datetime
    camera_id: UUID | None = None
    class_name: str
    event_count: int
    granularity: str
    metric: HistoryMetric = HistoryMetric.OCCUPANCY


class HistorySeriesResponse(BaseModel):
    granularity: str
    metric: HistoryMetric = HistoryMetric.OCCUPANCY
    class_names: list[str]
    rows: list[HistorySeriesRow]
    granularity_adjusted: bool = False
    speed_classes_capped: bool = False
    speed_classes_used: list[str] | None = None


class HistoryClassEntry(BaseModel):
    class_name: str
    event_count: int
    has_speed_data: bool


class HistoryClassesResponse(BaseModel):
    from_: datetime = Field(serialization_alias="from", validation_alias="from")
    to: datetime
    metric: HistoryMetric = HistoryMetric.OCCUPANCY
    boundaries: list[CountEventBoundarySummary] = Field(default_factory=list)
    classes: list[HistoryClassEntry]
```

- [ ] **Step 4: Add the new store**

In `backend/src/argus/core/db.py`, extend imports and add `CountEventStore` under `TrackingEventStore`:

```python
from argus.models.enums import CountEventType
from argus.models.tables import CountEvent, TrackingEvent
```

```python
class CountEventStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def record(
        self,
        camera_id: UUID,
        events: list[dict[str, object]],
    ) -> None:
        if not events:
            return

        rows = [
            CountEvent(
                ts=event["ts"],
                camera_id=camera_id,
                class_name=str(event["class_name"]),
                track_id=event.get("track_id"),
                event_type=CountEventType(str(event["event_type"])),
                boundary_id=str(event["boundary_id"]),
                direction=event.get("direction"),
                from_zone_id=event.get("from_zone_id"),
                to_zone_id=event.get("to_zone_id"),
                speed_kph=event.get("speed_kph"),
                confidence=event.get("confidence"),
                attributes=event.get("attributes"),
                payload=dict(event.get("payload") or {}),
            )
            for event in events
        ]

        async with self.session_factory() as session:
            session.add_all(rows)
            await session.commit()
```

- [ ] **Step 5: Re-run the focused test**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/core/test_db.py -q`

Expected: PASS with both the existing async-session test and the new `CountEventStore` test green.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/models/enums.py backend/src/argus/models/tables.py backend/src/argus/api/contracts.py backend/src/argus/core/db.py backend/tests/core/test_db.py
git commit -m "feat(history): add metric and count event schema primitives"
```

---

## Task 2: Add the `count_events` Migration and Aggregates

**Files:**
- Create: `backend/src/argus/migrations/versions/0004_prompt12_count_events.py`
- Test: `backend/tests/core/test_db.py`

- [ ] **Step 1: Write the failing migration smoke test**

Append to `backend/tests/core/test_db.py`:

```python
from pathlib import Path


def test_count_events_migration_exists() -> None:
    migration = Path(
        "/Users/yann.moren/vision/backend/src/argus/migrations/versions/0004_prompt12_count_events.py"
    )
    assert migration.exists()
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/core/test_db.py::test_count_events_migration_exists -q`

Expected: FAIL because the new migration file does not exist yet.

- [ ] **Step 3: Create the migration**

Create `backend/src/argus/migrations/versions/0004_prompt12_count_events.py`:

```python
"""Add count events hypertable and aggregates."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_prompt12_count_events"
down_revision = "0003_prompt11_quota"
branch_labels = None
depends_on = None


count_event_type_enum = sa.Enum(
    "line_cross",
    "zone_enter",
    "zone_exit",
    name="count_event_type_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    count_event_type_enum.create(bind, checkfirst=True)

    op.create_table(
        "count_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), primary_key=True, nullable=False),
        sa.Column(
            "camera_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cameras.id"),
            nullable=False,
        ),
        sa.Column("class_name", sa.String(length=255), nullable=False),
        sa.Column("track_id", sa.Integer(), nullable=True),
        sa.Column("event_type", count_event_type_enum, nullable=False),
        sa.Column("boundary_id", sa.String(length=255), nullable=False),
        sa.Column("direction", sa.String(length=64), nullable=True),
        sa.Column("from_zone_id", sa.String(length=255), nullable=True),
        sa.Column("to_zone_id", sa.String(length=255), nullable=True),
        sa.Column("speed_kph", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.alter_column("count_events", "payload", server_default=None)
    op.execute("SELECT create_hypertable('count_events', 'ts', if_not_exists => TRUE)")

    with op.get_context().autocommit_block():
        op.execute(
            '''
            CREATE MATERIALIZED VIEW IF NOT EXISTS count_events_1m
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 minute', ts) AS bucket,
              camera_id,
              class_name,
              boundary_id,
              event_type,
              COUNT(*) AS event_count
            FROM count_events
            GROUP BY bucket, camera_id, class_name, boundary_id, event_type
            '''
        )
        op.execute(
            '''
            CREATE MATERIALIZED VIEW IF NOT EXISTS count_events_1h
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket(INTERVAL '1 hour', ts) AS bucket,
              camera_id,
              class_name,
              boundary_id,
              event_type,
              COUNT(*) AS event_count
            FROM count_events
            GROUP BY bucket, camera_id, class_name, boundary_id, event_type
            '''
        )


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS count_events_1h")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS count_events_1m")
    op.drop_table("count_events")
    bind = op.get_bind()
    count_event_type_enum.drop(bind, checkfirst=True)
```

- [ ] **Step 4: Re-run the migration smoke test**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/core/test_db.py::test_count_events_migration_exists -q`

Expected: PASS.

- [ ] **Step 5: Apply the migration locally**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run alembic upgrade head`

Expected: Alembic upgrades from `0003_prompt11_quota` to `0004_prompt12_count_events` without enum or Timescale view errors.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/migrations/versions/0004_prompt12_count_events.py backend/tests/core/test_db.py
git commit -m "feat(db): add count events hypertable and aggregates"
```

---

## Task 3: Implement Generic Line and Zone Count Event Processing

**Files:**
- Create: `backend/src/argus/vision/count_events.py`
- Modify: `backend/src/argus/vision/anpr.py`
- Create: `backend/tests/vision/test_count_events.py`

- [ ] **Step 1: Write failing processor tests**

Create `backend/tests/vision/test_count_events.py`:

```python
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from argus.models.enums import CountEventType
from argus.vision.count_events import CountEventProcessor
from argus.vision.types import Detection


def _car(track_id: int, bbox: tuple[float, float, float, float], zone_id: str | None = None) -> Detection:
    return Detection(
        class_name="car",
        confidence=0.95,
        bbox=bbox,
        track_id=track_id,
        zone_id=zone_id,
        speed_kph=32.0,
        attributes={},
    )


def test_line_cross_emits_direction_once() -> None:
    processor = CountEventProcessor(
        definitions=[
            {"id": "driveway", "type": "line", "points": [[50, 0], [50, 100]], "class_names": ["car"]}
        ]
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(1, (10, 10, 30, 30))]) == []
    events = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(1, (60, 10, 80, 30))])

    assert len(events) == 1
    assert events[0]["event_type"] == CountEventType.LINE_CROSS
    assert events[0]["boundary_id"] == "driveway"
    assert events[0]["direction"] == "negative-to-positive"


def test_zone_enter_and_exit_emit_distinct_events() -> None:
    processor = CountEventProcessor(definitions=[{"id": "yard", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]}])
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    assert processor.process(ts=ts, detections=[_car(7, (10, 10, 30, 30), zone_id=None)]) == []
    entered = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(7, (10, 10, 30, 30), zone_id="yard")])
    exited = processor.process(ts=ts + timedelta(seconds=2), detections=[_car(7, (10, 10, 30, 30), zone_id=None)])

    assert [event["event_type"] for event in entered] == [CountEventType.ZONE_ENTER]
    assert entered[0]["to_zone_id"] == "yard"
    assert [event["event_type"] for event in exited] == [CountEventType.ZONE_EXIT]
    assert exited[0]["from_zone_id"] == "yard"


def test_short_boundary_dedupe_suppresses_track_churn() -> None:
    processor = CountEventProcessor(
        definitions=[
            {"id": "driveway", "type": "line", "points": [[50, 0], [50, 100]], "class_names": ["car"]}
        ],
        dedupe_seconds=2.0,
    )
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    processor.process(ts=ts, detections=[_car(10, (10, 10, 30, 30))])
    first = processor.process(ts=ts + timedelta(seconds=1), detections=[_car(10, (60, 10, 80, 30))])
    second = processor.process(ts=ts + timedelta(seconds=1, milliseconds=500), detections=[_car(11, (62, 10, 82, 30))])

    assert len(first) == 1
    assert second == []
```

- [ ] **Step 2: Run the failing tests**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/vision/test_count_events.py -q`

Expected: FAIL because `CountEventProcessor` does not exist yet.

- [ ] **Step 3: Implement the processor**

Create `backend/src/argus/vision/count_events.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from shapely.geometry import Point, Polygon  # type: ignore[import-untyped]
from shapely.prepared import prep  # type: ignore[import-untyped]

from argus.models.enums import CountEventType
from argus.vision.types import Detection


@dataclass(slots=True, frozen=True)
class _LineBoundary:
    boundary_id: str
    start: tuple[float, float]
    end: tuple[float, float]
    class_names: frozenset[str]


@dataclass(slots=True, frozen=True)
class _ZoneBoundary:
    boundary_id: str
    polygon: Any


class CountEventProcessor:
    def __init__(self, definitions: list[dict[str, Any]], *, dedupe_seconds: float = 1.5) -> None:
        self._lines: list[_LineBoundary] = []
        self._zones: list[_ZoneBoundary] = []
        self._last_line_side: dict[tuple[str, int], float] = {}
        self._last_zone_by_track: dict[int, str | None] = {}
        self._recent_boundary_hits: dict[tuple[str, str], datetime] = {}
        self._dedupe_seconds = dedupe_seconds

        for definition in definitions:
            boundary_type = str(definition.get("type", "polygon")).lower()
            if boundary_type == "line":
                points = definition["points"]
                self._lines.append(
                    _LineBoundary(
                        boundary_id=str(definition["id"]),
                        start=(float(points[0][0]), float(points[0][1])),
                        end=(float(points[1][0]), float(points[1][1])),
                        class_names=frozenset(str(name) for name in definition.get("class_names", [])),
                    )
                )
                continue

            polygon = Polygon(definition["polygon"])
            self._zones.append(
                _ZoneBoundary(boundary_id=str(definition["id"]), polygon=prep(polygon))
            )

    def process(self, *, ts: datetime, detections: list[Detection]) -> list[dict[str, object]]:
        events: list[dict[str, object]] = []
        for detection in detections:
            if detection.track_id is None:
                continue
            events.extend(self._process_lines(ts=ts, detection=detection))
            events.extend(self._process_zones(ts=ts, detection=detection))
        return events

    def _process_lines(self, *, ts: datetime, detection: Detection) -> list[dict[str, object]]:
        emitted: list[dict[str, object]] = []
        x1, y1, x2, y2 = detection.bbox
        bottom_center = ((x1 + x2) / 2.0, y2)
        for boundary in self._lines:
            if boundary.class_names and detection.class_name not in boundary.class_names:
                continue
            side = point_side(bottom_center, boundary.start, boundary.end)
            key = (boundary.boundary_id, detection.track_id)
            previous_side = self._last_line_side.get(key)
            self._last_line_side[key] = side
            if previous_side is None or previous_side == 0 or side == 0 or previous_side * side > 0:
                continue

            direction = line_cross_direction(previous_side, side)
            dedupe_key = (boundary.boundary_id, direction)
            previous_hit = self._recent_boundary_hits.get(dedupe_key)
            if previous_hit is not None and (ts - previous_hit).total_seconds() < self._dedupe_seconds:
                continue
            self._recent_boundary_hits[dedupe_key] = ts
            emitted.append(
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.LINE_CROSS,
                    boundary_id=boundary.boundary_id,
                    direction=direction,
                )
            )
        return emitted

    def _process_zones(self, *, ts: datetime, detection: Detection) -> list[dict[str, object]]:
        previous_zone = self._last_zone_by_track.get(detection.track_id)
        current_zone = detection.zone_id
        self._last_zone_by_track[detection.track_id] = current_zone
        if previous_zone == current_zone:
            return []
        if previous_zone is None and current_zone is not None:
            return [
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.ZONE_ENTER,
                    boundary_id=current_zone,
                    to_zone_id=current_zone,
                )
            ]
        if previous_zone is not None and current_zone is None:
            return [
                build_count_event(
                    ts=ts,
                    detection=detection,
                    event_type=CountEventType.ZONE_EXIT,
                    boundary_id=previous_zone,
                    from_zone_id=previous_zone,
                )
            ]
        return []


def build_count_event(
    *,
    ts: datetime,
    detection: Detection,
    event_type: CountEventType,
    boundary_id: str,
    direction: str | None = None,
    from_zone_id: str | None = None,
    to_zone_id: str | None = None,
) -> dict[str, object]:
    return {
        "ts": ts,
        "class_name": detection.class_name,
        "track_id": detection.track_id,
        "event_type": event_type,
        "boundary_id": boundary_id,
        "direction": direction,
        "from_zone_id": from_zone_id,
        "to_zone_id": to_zone_id,
        "speed_kph": detection.speed_kph,
        "confidence": detection.confidence,
        "attributes": dict(detection.attributes) if detection.attributes else None,
        "payload": {"zone_id": detection.zone_id},
    }


def point_side(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = start
    x2, y2 = end
    return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)


def line_cross_direction(previous_side: float, side: float) -> str:
    if previous_side > 0 and side < 0:
        return "positive-to-negative"
    return "negative-to-positive"
```

- [ ] **Step 4: Reuse the shared line helper in ANPR**

In `backend/src/argus/vision/anpr.py`, replace the private geometry helpers with imports from the new module:

```python
from argus.vision.count_events import line_cross_direction, point_side
```

And inside `process`, replace:

```python
                side = _point_side(bottom_center, line)
```

with:

```python
                side = point_side(bottom_center, line.start, line.end)
```

And replace:

```python
                            "direction": _direction(previous_side, side),
```

with:

```python
                            "direction": line_cross_direction(previous_side, side),
```

Then delete the old `_point_side` / `_direction` helpers.

- [ ] **Step 5: Re-run focused vision tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/vision/test_count_events.py tests/vision/test_anpr.py tests/vision/test_zones.py -q
```

Expected: PASS. The new processor tests, existing ANPR tests, and existing zone tests should all stay green.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/vision/count_events.py backend/src/argus/vision/anpr.py backend/tests/vision/test_count_events.py
git commit -m "feat(worker): add generic line and zone count event processor"
```

---

## Task 4: Wire Count Event Persistence Into the Worker

**Files:**
- Modify: `backend/src/argus/inference/engine.py`
- Modify: `backend/src/argus/core/db.py`
- Modify: `backend/tests/inference/test_engine.py`

- [ ] **Step 1: Write the failing engine test**

Append to `backend/tests/inference/test_engine.py`:

```python
class _FakeCountEventStore:
    def __init__(self) -> None:
        self.records: list[tuple[UUID, list[dict[str, object]]]] = []

    async def record(self, camera_id: UUID, events: list[dict[str, object]]) -> None:
        self.records.append((camera_id, events))


class _SingleDetectionTracker:
    def update(self, detections: list[Detection], frame: np.ndarray | None = None) -> list[Detection]:
        return [detections[0].with_updates(track_id=1, zone_id="yard")]


@pytest.mark.asyncio
async def test_engine_records_generic_count_events() -> None:
    camera_id = uuid4()
    count_store = _FakeCountEventStore()
    engine = InferenceEngine(
        config=_engine_config(camera_id).model_copy(
            update={
                "zones": [
                    {"id": "driveway", "type": "line", "points": [[50, 0], [50, 100]], "class_names": ["car"]},
                    {"id": "yard", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]},
                ]
            }
        ),
        frame_source=_FakeFrameSource([np.zeros((120, 120, 3), dtype=np.uint8), np.zeros((120, 120, 3), dtype=np.uint8)]),
        detector=_FakeDetector(),
        tracker_factory=lambda tracker_type: _SingleDetectionTracker(),
        publisher=_FakePublisher(),
        tracking_store=_FakeTrackingStore(),
        count_event_store=count_store,
        rule_engine=_FakeRuleEngine(),
        event_client=_FakeEventClient(),
        stream_client=_FakeStreamClient(),
    )

    await engine.run_once(ts=datetime(2026, 4, 25, 12, 0, tzinfo=UTC))
    await engine.run_once(ts=datetime(2026, 4, 25, 12, 0, 1, tzinfo=UTC))

    assert count_store.records
    camera_seen, events = count_store.records[-1]
    assert camera_seen == camera_id
    assert any(event["boundary_id"] == "yard" for event in events)
```

- [ ] **Step 2: Run the failing engine test**

Run: `cd /Users/yann.moren/vision/backend && python3 -m uv run pytest tests/inference/test_engine.py::test_engine_records_generic_count_events -q`

Expected: FAIL because `InferenceEngine` does not yet accept `count_event_store`.

- [ ] **Step 3: Extend engine protocols and state**

In `backend/src/argus/inference/engine.py`, add:

```python
from argus.core.db import CountEventStore, DatabaseManager, TrackingEventStore
from argus.vision.count_events import CountEventProcessor
```

Add a new protocol near `TrackingStore`:

```python
class CountEventStoreProtocol(Protocol):
    async def record(self, camera_id: UUID, events: list[dict[str, object]]) -> None: ...
```

Extend `InferenceEngine.__init__`:

```python
        tracking_store: TrackingStore,
        count_event_store: CountEventStoreProtocol | None,
```

Store it and build the processor:

```python
        self.count_event_store = count_event_store
        self._count_event_processor = CountEventProcessor(config.zones) if config.zones else None
```

- [ ] **Step 4: Emit and persist count events in `run_once`**

Right after `tracked = self._apply_zones(tracked)` and before rule evaluation, insert:

```python
        count_events = (
            self._count_event_processor.process(ts=current_ts, detections=tracked)
            if self._count_event_processor is not None
            else []
        )
```

After telemetry publish and before `persist_tracking`, insert:

```python
        if self.count_event_store is not None and count_events:
            await self.count_event_store.record(self.config.camera_id, count_events)
```

When `command.zones` changes in `apply_command`, rebuild the processor too:

```python
            self._count_event_processor = (
                CountEventProcessor(self._state.zones) if self._state.zones else None
            )
```

In `build_runtime_engine`, pass the real store:

```python
        count_event_store=CountEventStore(db_manager.session_factory),
```

If `build_runtime_engine` is still passed an injected `tracking_store`, keep that injection and add a new optional `count_event_store` parameter in the factory signature so tests can pass fakes without spinning up the DB.

- [ ] **Step 5: Re-run the focused engine suite**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/inference/test_engine.py -q
```

Expected: PASS. Existing telemetry/publish tests keep working and the new count-event persistence test passes.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/inference/engine.py backend/tests/inference/test_engine.py
git commit -m "feat(engine): persist generic count events from tracked detections"
```

---

## Task 5: Make History Metric-Aware

**Files:**
- Modify: `backend/src/argus/api/v1/history.py`
- Modify: `backend/src/argus/services/app.py`
- Modify: `backend/tests/services/test_history_service.py`
- Modify: `backend/tests/api/test_history_endpoints.py`

- [ ] **Step 1: Write failing service tests for the three metrics**

Append to `backend/tests/services/test_history_service.py`:

```python
from argus.models.enums import HistoryMetric


@pytest.mark.asyncio
async def test_query_series_count_events_reads_count_event_views(monkeypatch: pytest.MonkeyPatch) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    count_events = AsyncMock(
        return_value=[
            {"bucket": datetime(2026, 4, 25, tzinfo=UTC), "class_name": "car", "event_count": 3}
        ]
    )
    occupancy = AsyncMock(return_value=[])
    monkeypatch.setattr(service, "_fetch_count_event_series_rows", count_events)
    monkeypatch.setattr(service, "_fetch_series_rows_from_events", occupancy)

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1h",
        starts_at=datetime(2026, 4, 25, tzinfo=UTC),
        ends_at=datetime(2026, 4, 25, 1, tzinfo=UTC),
        metric=HistoryMetric.COUNT_EVENTS,
    )

    assert response.metric == HistoryMetric.COUNT_EVENTS
    count_events.assert_awaited_once()
    occupancy.assert_not_awaited()


@pytest.mark.asyncio
async def test_query_series_observations_reads_observation_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    service = HistoryService(session_factory=MagicMock())
    service._ensure_camera_access = AsyncMock()
    observations = AsyncMock(
        return_value=[
            {"bucket": datetime(2026, 4, 25, tzinfo=UTC), "class_name": "person", "event_count": 12}
        ]
    )
    monkeypatch.setattr(service, "_fetch_observation_series_rows", observations)

    response = await service.query_series(
        _tenant_context(),
        camera_ids=None,
        class_names=None,
        granularity="1h",
        starts_at=datetime(2026, 4, 25, tzinfo=UTC),
        ends_at=datetime(2026, 4, 25, 1, tzinfo=UTC),
        metric=HistoryMetric.OBSERVATIONS,
    )

    assert response.metric == HistoryMetric.OBSERVATIONS
    observations.assert_awaited_once()
```

Append to `backend/tests/api/test_history_endpoints.py`:

```python
@pytest.mark.asyncio
async def test_series_endpoint_passes_metric(tenant_context: TenantContext) -> None:
    service = _FakeHistoryService()
    app = _app_with_fakes(service, tenant_context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/history/series",
            params={
                "from": "2026-04-23T00:00:00Z",
                "to": "2026-04-23T06:00:00Z",
                "metric": "count_events",
            },
        )

    assert resp.status_code == 200
    assert service.calls[-1]["metric"] == "count_events"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py -q
```

Expected: FAIL because `metric` is not accepted and the new helpers do not exist yet.

- [ ] **Step 3: Add the `metric` query parameter and defaults**

In `backend/src/argus/api/v1/history.py`, import `HistoryMetric` and add:

```python
MetricQuery = Annotated[HistoryMetric, Query()] 
```

Then extend each endpoint:

```python
    metric: MetricQuery = HistoryMetric.OCCUPANCY,
```

and pass `metric=metric` into `query_history`, `query_series`, and `list_classes`.

- [ ] **Step 4: Teach `HistoryService` the three metrics**

In `backend/src/argus/services/app.py`, import `HistoryMetric` and change method signatures:

```python
    async def query_history(..., metric: HistoryMetric = HistoryMetric.OCCUPANCY) -> list[HistoryPoint]:
```

```python
    async def query_series(..., metric: HistoryMetric = HistoryMetric.OCCUPANCY, include_speed: bool = False, ...) -> HistorySeriesResponse:
```

```python
    async def list_classes(..., metric: HistoryMetric = HistoryMetric.OCCUPANCY) -> HistoryClassesResponse:
```

Add three helpers:

```python
    async def _fetch_occupancy_series_rows(...)
    async def _fetch_observation_series_rows(...)
    async def _fetch_count_event_series_rows(...)
```

Use these SQL shapes:

```python
    # occupancy: maximum concurrent visible tracks seen inside each bucket/class
    SELECT
      bucket,
      class_name,
      MAX(active_count)::bigint AS event_count
    FROM (
      SELECT
        time_bucket(INTERVAL '{interval}', ts) AS bucket,
        class_name,
        ts,
        count(DISTINCT track_id)::bigint AS active_count
      FROM tracking_events
      WHERE ts >= :starts_at
        AND ts <= :ends_at
        ...
      GROUP BY 1, 2, 3
    ) occupancy_samples
    GROUP BY 1, 2
    ORDER BY 1 ASC, 2 ASC
```

```python
    # observations: raw event density
    SELECT
      time_bucket(INTERVAL '{interval}', ts) AS bucket,
      class_name,
      count(*)::bigint AS event_count
    FROM tracking_events
    ...
```

```python
    # count events: aggregate from count_events_1m / count_events_1h with rollup
    SELECT
      {bucket_expr} AS bucket,
      class_name,
      SUM(event_count)::bigint AS event_count
    FROM {view_name}
    WHERE bucket >= :starts_at
      AND bucket <= :ends_at
      ...
```

Dispatch inside `query_series`:

```python
        if metric is HistoryMetric.COUNT_EVENTS:
            rows = await self._fetch_count_event_series_rows(...)
        elif metric is HistoryMetric.OBSERVATIONS:
            rows = await self._fetch_observation_series_rows(...)
        elif include_speed:
            rows = await self._fetch_series_rows_with_speed(...)
        else:
            rows = await self._fetch_occupancy_series_rows(...)
```

In `HistorySeriesResponse(...)`, return `metric=metric`.

In `list_classes`, use metric-specific queries and include boundary metadata for count events:

```python
        return HistoryClassesResponse.model_validate(
            {
                "from": starts_at,
                "to": ends_at,
                "metric": metric,
                "boundaries": boundary_rows,
                "classes": [...],
            }
        )
```

Use `count_events` for boundary summaries:

```python
SELECT boundary_id, array_agg(DISTINCT event_type ORDER BY event_type) AS event_types
FROM count_events
WHERE ts >= :starts_at AND ts <= :ends_at
...
GROUP BY boundary_id
ORDER BY boundary_id ASC
```

- [ ] **Step 5: Re-run history tests**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/services/test_history_service.py tests/api/test_history_endpoints.py -q
```

Expected: PASS. The responses now carry `metric`, and `count_events` reads from the new storage instead of `tracking_events`.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add backend/src/argus/api/v1/history.py backend/src/argus/services/app.py backend/tests/services/test_history_service.py backend/tests/api/test_history_endpoints.py
git commit -m "feat(history): support occupancy observations and count event metrics"
```

---

## Task 6: Switch Live Sparkline and Tile Copy to Occupancy Semantics

**Files:**
- Modify: `frontend/src/hooks/use-live-sparkline.ts`
- Modify: `frontend/src/components/live/LiveSparkline.tsx`
- Modify: `frontend/src/pages/Live.tsx`
- Modify: `frontend/src/hooks/use-live-sparkline.test.tsx`
- Modify: `frontend/src/components/live/LiveSparkline.test.tsx`
- Modify: `frontend/src/pages/Live.test.tsx`

- [ ] **Step 1: Write the failing frontend tests**

In `frontend/src/hooks/use-live-sparkline.test.tsx`, add:

```tsx
import { describe, expect, test } from "vitest";

import { mergeOccupancyCounts } from "@/hooks/use-live-sparkline";

describe("mergeOccupancyCounts", () => {
  test("keeps the highest occupancy seen in a minute without cumulative growth", () => {
    const seed = { person: [0, 0, 0] };
    const afterFirst = mergeOccupancyCounts(seed, { person: 1 }, 2);
    const afterSecond = mergeOccupancyCounts(afterFirst, { person: 1 }, 2);
    const afterThird = mergeOccupancyCounts(afterSecond, { person: 2 }, 2);

    expect(afterFirst.person[2]).toBe(1);
    expect(afterSecond.person[2]).toBe(1);
    expect(afterThird.person[2]).toBe(2);
  });
});
```

In `frontend/src/components/live/LiveSparkline.test.tsx`, update the mock and assertions:

```tsx
vi.mock("@/hooks/use-live-sparkline", () => ({
  useLiveSparkline: () => ({
    buckets: { person: [0, 0, 1], car: [0, 2, 2] },
    latestValues: { person: 1, car: 2 },
    loading: false,
    error: null,
  }),
}));

test("shows latest occupancy instead of cumulative totals", () => {
  render(<LiveSparkline cameraId="cam-1" activeClasses={["car", "person"]} />);
  expect(screen.getByText("2")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
});
```

In `frontend/src/pages/Live.test.tsx`, change the text expectation from `visible detections` to `visible now`.

- [ ] **Step 2: Run the failing frontend tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/hooks/use-live-sparkline.test.tsx src/components/live/LiveSparkline.test.tsx src/pages/Live.test.tsx
```

Expected: FAIL because the UI still uses cumulative language and cumulative totals.

- [ ] **Step 3: Change the hook result semantics**

In `frontend/src/hooks/use-live-sparkline.ts`, replace additive accumulation with occupancy merging:

```tsx
export function mergeOccupancyCounts(
  buckets: SparklineBuckets,
  classesCount: Record<string, number>,
  index: number,
): SparklineBuckets {
  const next: SparklineBuckets = { ...buckets };
  for (const [cls, count] of Object.entries(classesCount)) {
    const series = next[cls] ?? new Array(BUCKET_COUNT).fill(0);
    const copy = series.slice();
    copy[index] = Math.max(copy[index] ?? 0, count);
    next[cls] = copy;
  }
  return next;
}
```

Delete `SeenTrackBuckets`, `collectNewTrackCounts`, `pruneSeenTrackBuckets`, and `seenTracksRef`; live occupancy should come from `frame.counts` snapshots rather than unique-track accumulation.

When applying live frames, replace:

```tsx
      const deltaCounts = collectNewTrackCounts(seenTracksRef.current, alignedTsMs, frame);
      if (Object.keys(deltaCounts).length === 0) return;
      setBuckets((current) => addCounts(current, deltaCounts, idx));
```

with:

```tsx
      const occupancyCounts = frame.counts ?? {};
      if (Object.keys(occupancyCounts).length === 0) return;
      setBuckets((current) => mergeOccupancyCounts(current, occupancyCounts, idx));
```

Then expose latest values separately:

```tsx
  const latestValues = useMemo(() => {
    const out: SparklineTotals = {};
    for (const [cls, series] of Object.entries(buckets)) {
      out[cls] = series[series.length - 1] ?? 0;
    }
    return out;
  }, [buckets]);
```

Update the return type and hook return line:

```tsx
export type UseLiveSparklineResult = {
  buckets: SparklineBuckets;
  latestValues: SparklineTotals;
  loading: boolean;
  error: Error | null;
};
```

- [ ] **Step 4: Update the sparkline and tile copy**

In `frontend/src/components/live/LiveSparkline.tsx`, consume `latestValues`:

```tsx
  const { buckets, latestValues, loading, error } = useLiveSparkline(cameraId);

type RowProps = {
  className: string;
  color: string;
  series: number[];
  latestValue: number;
};
```

and render:

```tsx
      <span className="w-10 text-right tabular-nums text-[#8ea8cf]">{latestValue}</span>
```

In `frontend/src/pages/Live.tsx`, replace:

```tsx
{visibleTracks.length} visible detections
```

with:

```tsx
{visibleTracks.length} visible now
```

- [ ] **Step 5: Re-run the focused frontend tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/hooks/use-live-sparkline.test.tsx src/components/live/LiveSparkline.test.tsx src/pages/Live.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/hooks/use-live-sparkline.ts frontend/src/hooks/use-live-sparkline.test.tsx frontend/src/components/live/LiveSparkline.tsx frontend/src/components/live/LiveSparkline.test.tsx frontend/src/pages/Live.tsx frontend/src/pages/Live.test.tsx
git commit -m "feat(live): switch sparkline totals to occupancy semantics"
```

---

## Task 7: Add Metric Selection and Boundary-Aware Defaults to History

**Files:**
- Modify: `frontend/src/lib/history-url-state.ts`
- Modify: `frontend/src/hooks/use-history.ts`
- Modify: `frontend/src/pages/History.tsx`
- Modify: `frontend/src/components/history/HistoryTrendChart.tsx`
- Modify: `frontend/src/pages/History.test.tsx`

- [ ] **Step 1: Write failing History tests**

Append to `frontend/src/pages/History.test.tsx`:

```tsx
test("metric is read from the URL and forwarded to the history endpoint", async () => {
  renderPage("/history?metric=count_events");
  await screen.findByTestId("history-trend-chart");

  const historyCalls = vi.mocked(global.fetch).mock.calls.filter(([input]) =>
    String(input).includes("/api/v1/history/series"),
  );
  expect(String(historyCalls[0]?.[0])).toContain("metric=count_events");
});

test("defaults to count events when the selected camera has a line boundary", async () => {
  vi.spyOn(global, "fetch").mockImplementation((input, init) => {
    const request = input instanceof Request ? input : new Request(String(input), init);
    const url = new URL(request.url);
    if (url.pathname === "/api/v1/cameras") {
      return Promise.resolve(
        jsonResponse([
          {
            id: "11111111-1111-1111-1111-111111111111",
            site_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            edge_node_id: null,
            name: "North Gate",
            rtsp_url_masked: "rtsp://***",
            processing_mode: "central",
            primary_model_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            secondary_model_id: null,
            tracker_type: "botsort",
            active_classes: ["car"],
            attribute_rules: [],
            zones: [{ id: "driveway", type: "line", points: [[0, 0], [1, 1]], class_names: ["car"] }],
            homography: null,
            privacy: { blur_faces: false, blur_plates: false, method: "gaussian", strength: 7 },
            browser_delivery: { default_profile: "540p5", allow_native_on_demand: true, profiles: [] },
            frame_skip: 1,
            fps_cap: 15,
            created_at: "2026-04-18T10:00:00Z",
            updated_at: "2026-04-18T10:00:00Z",
          },
        ]),
      );
    }
    if (url.pathname === "/api/v1/history/classes") {
      return Promise.resolve(jsonResponse({ ...classesResponse(), metric: "count_events", boundaries: [] }));
    }
    if (url.pathname === "/api/v1/history/series") {
      return Promise.resolve(jsonResponse({ ...historySeriesResponse(), metric: "count_events" }));
    }
    return Promise.resolve(new Response("Not found", { status: 404 }));
  });

  renderPage("/history?cameras=11111111-1111-1111-1111-111111111111");
  await waitFor(() => expect(screen.getByDisplayValue(/count events/i)).toBeInTheDocument());
});
```

- [ ] **Step 2: Run the failing History tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: FAIL because the filter state does not carry `metric` yet.

- [ ] **Step 3: Add `metric` to filter state and query hooks**

In `frontend/src/lib/history-url-state.ts`, add:

```tsx
export type HistoryMetric = "occupancy" | "count_events" | "observations";
```

Extend `HistoryFilterState`:

```tsx
  metric: HistoryMetric;
```

Add helpers:

```tsx
const METRICS = new Set<HistoryMetric>(["occupancy", "count_events", "observations"]);

function toMetric(value: string | null): HistoryMetric {
  if (value && METRICS.has(value as HistoryMetric)) return value as HistoryMetric;
  return "occupancy";
}
```

Read and write it:

```tsx
    metric: toMetric(params.get("metric")),
```

```tsx
  params.set("metric", state.metric);
```

In `frontend/src/hooks/use-history.ts`, extend `HistoryFilters` and the query key:

```tsx
  metric: "occupancy" | "count_events" | "observations";
```

Send the query parameter:

```tsx
            metric: filters.metric,
```

Also include `metric` in `historyClassesQueryOptions`.

- [ ] **Step 4: Update the History page**

In `frontend/src/pages/History.tsx`, extend `filters`:

```tsx
      metric: state.metric,
```

Compute boundary-aware default:

```tsx
  useEffect(() => {
    if (state.metric !== "occupancy" || state.cameraIds.length === 0 || cameras.length === 0) {
      return;
    }
    const selected = cameras.filter((camera) => state.cameraIds.includes(camera.id));
    const hasCountBoundary = selected.some((camera) =>
      (camera.zones ?? []).some((zone) => {
        const type = String(zone?.type ?? "polygon").toLowerCase();
        return type === "line" || Boolean(zone?.count_events);
      }),
    );
    if (hasCountBoundary) {
      applyState((prev) => ({ ...prev, metric: "count_events" }));
    }
  }, [state.metric, state.cameraIds, cameras, applyState]);
```

Add a metric select above granularity:

```tsx
            <label className="space-y-2 text-sm text-[#d9e5f7]">
              <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">Metric</span>
              <Select
                aria-label="Metric"
                value={state.metric}
                onChange={(e) =>
                  applyState((p) => ({ ...p, metric: e.target.value as HistoryFilterState["metric"] }))
                }
              >
                <option value="count_events">Count events</option>
                <option value="occupancy">Occupancy</option>
                <option value="observations">Observations</option>
              </Select>
            </label>
```

Change labels:

```tsx
  const headline = state.metric === "count_events"
    ? "Precise pass-by counts and event-time speed."
    : state.metric === "observations"
      ? "Raw observation density and speed telemetry."
      : "Visible occupancy and speed telemetry.";
```

Feed the chart the chosen metric:

```tsx
      metric: state.metric,
```

In `frontend/src/components/history/HistoryTrendChart.tsx`, extend the series type:

```tsx
  metric?: "occupancy" | "count_events" | "observations";
```

and set the first y-axis name accordingly:

```tsx
      name:
        series.metric === "count_events"
          ? "events"
          : series.metric === "observations"
            ? "observations"
            : "visible",
```

- [ ] **Step 5: Re-run History tests**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/lib/history-url-state.ts frontend/src/hooks/use-history.ts frontend/src/pages/History.tsx frontend/src/components/history/HistoryTrendChart.tsx frontend/src/pages/History.test.tsx
git commit -m "feat(history-ui): add metric selector and count event defaults"
```

---

## Task 8: Regenerate OpenAPI, Run End-to-End Verification, and Update Docs

**Files:**
- Modify: `frontend/src/lib/api.generated.ts`
- Modify: `README.md`
- Modify: `product-spec-v4.md`
- Modify: `ai-coder-prompt-v4.md`

- [ ] **Step 1: Regenerate frontend API types**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend generate:api
```

Expected: `frontend/src/lib/api.generated.ts` updates with the new `metric` field/enum and history response shapes.

- [ ] **Step 2: Run backend verification**

Run:

```bash
cd /Users/yann.moren/vision/backend
python3 -m uv run pytest tests/core/test_db.py tests/vision/test_count_events.py tests/vision/test_anpr.py tests/inference/test_engine.py tests/services/test_history_service.py tests/api/test_history_endpoints.py -q
```

Expected: PASS.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd /Users/yann.moren/vision
corepack pnpm --dir frontend exec vitest run src/hooks/use-live-sparkline.test.tsx src/components/live/LiveSparkline.test.tsx src/pages/Live.test.tsx src/pages/History.test.tsx
```

Expected: PASS.

- [ ] **Step 4: Update the root docs**

In `README.md`, add a short “Metrics” section:

```md
## Metrics semantics

- `occupancy` means objects currently visible in the scene
- `count_events` means discrete operational events such as line crossing or zone entry/exit
- `observations` means raw tracking-event density for debugging and analytics
```

In `product-spec-v4.md`, update the history/live sections so they explicitly state:

```md
- Live tiles show occupancy (`visible now`)
- History can switch between occupancy, count events, and observations
- precise pass-by counts come from line and zone event generation, not raw tracking row density
```

In `ai-coder-prompt-v4.md`, add the guardrail:

```md
Never collapse occupancy, observations, and count events into one number. Live is occupancy-first; precise cumulative counts must come from durable count events.
```

- [ ] **Step 5: Do the manual smoke test**

Run the camera that previously inflated counts and verify:

1. `/live` shows `1 visible now` for a stationary person instead of a growing cumulative total.
2. A configured line-cross camera increments only when a car crosses the line.
3. History with `metric=count_events` shows line/zone counts.
4. History with `metric=occupancy` stays stable for stationary objects.
5. Speed panels still render when homography data is present.

- [ ] **Step 6: Commit**

```bash
cd /Users/yann.moren/vision
git add frontend/src/lib/api.generated.ts README.md product-spec-v4.md ai-coder-prompt-v4.md
git commit -m "docs(api): document occupancy and precise count event metrics"
```

---

## Final Verification Checklist

- [ ] `count_events` exists as a Timescale hypertable with 1-minute and 1-hour continuous aggregates.
- [ ] Worker emits `line_cross`, `zone_enter`, and `zone_exit` events without breaking telemetry publish.
- [ ] Live shows occupancy semantics (`visible now`) rather than cumulative per-frame inflation.
- [ ] History is explicitly metric-aware and defaults to `count_events` for cameras with count boundaries.
- [ ] Speed remains available in occupancy/count-event workflows.
- [ ] Root docs reflect the metric split so future work does not regress it.
