from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import numpy as np
import pytest

from argus.services.incident_capture import (
    IncidentClipCaptureService,
    IncidentTenantPolicy,
    IncidentTriggeredEvent,
)


@dataclass
class _FakeObjectStore:
    uploads: list[tuple[str, bytes, str]] = field(default_factory=list)

    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str:
        self.uploads.append((key, data, content_type))
        return f"https://minio.local/{key}"


@dataclass
class _FakeIncidentRepository:
    policy: IncidentTenantPolicy
    incidents: list[dict[str, object]] = field(default_factory=list)

    async def tenant_policy_for_camera(self, *, camera_id: UUID) -> IncidentTenantPolicy:
        return self.policy

    async def create_incident(
        self,
        *,
        camera_id: UUID,
        ts: datetime,
        incident_type: str,
        payload: dict[str, object],
        clip_url: str | None,
        storage_bytes: int,
    ) -> None:
        self.incidents.append(
            {
                "camera_id": camera_id,
                "ts": ts,
                "type": incident_type,
                "payload": payload,
                "clip_url": clip_url,
                "storage_bytes": storage_bytes,
            }
        )


@dataclass
class _FakeClipEncoder:
    encoded_bytes: bytes = b"synthetic-clip"

    def encode_clip(self, frames: list[np.ndarray], *, fps: int) -> bytes:
        assert frames
        assert fps == 2
        return self.encoded_bytes


@pytest.mark.asyncio
async def test_incident_capture_uploads_clip_and_persists_incident() -> None:
    camera_id = uuid4()
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=False,
                plaintext_justification=None,
                storage_quota_bytes=10_000,
                current_storage_bytes=0,
            )
        ),
        clip_encoder=_FakeClipEncoder(),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    started_at = datetime(2026, 4, 19, 12, 0, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=started_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at + timedelta(milliseconds=500),
            type="anpr.line_crossed",
            payload={
                "plate_text": "ZH123456",
                "plate_hash": "hash-value",
            },
        )
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=1),
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=2),
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    uploads = service.object_store.uploads  # type: ignore[attr-defined]

    assert len(uploads) == 1
    assert uploads[0][0].startswith("incidents/")
    assert len(incidents) == 1
    assert incidents[0]["clip_url"] == f"https://minio.local/{uploads[0][0]}"
    assert incidents[0]["storage_bytes"] == len(b"synthetic-clip")
    assert incidents[0]["payload"]["plate_hash"] == "hash-value"
    assert "plate_text" not in incidents[0]["payload"]


@pytest.mark.asyncio
async def test_incident_capture_skips_clip_when_tenant_storage_quota_is_exceeded() -> None:
    camera_id = uuid4()
    service = IncidentClipCaptureService(
        object_store=_FakeObjectStore(),
        repository=_FakeIncidentRepository(
            policy=IncidentTenantPolicy(
                tenant_id=uuid4(),
                allow_plaintext_plates=True,
                plaintext_justification="Municipal evidentiary retention policy",
                storage_quota_bytes=4,
                current_storage_bytes=4,
            )
        ),
        clip_encoder=_FakeClipEncoder(encoded_bytes=b"longer-than-quota"),
        pre_seconds=1,
        post_seconds=1,
        fps=2,
    )

    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    started_at = datetime(2026, 4, 19, 12, 5, tzinfo=UTC)
    await service.record_frame(camera_id=camera_id, frame=frame, ts=started_at)
    await service.queue_incident(
        IncidentTriggeredEvent(
            camera_id=camera_id,
            ts=started_at,
            type="anpr.line_crossed",
            payload={
                "plate_text": "ZH987654",
                "plate_hash": "hash-two",
            },
        )
    )
    await service.record_frame(
        camera_id=camera_id,
        frame=frame,
        ts=started_at + timedelta(seconds=2),
    )
    await service.flush(camera_id=camera_id)

    incidents = service.repository.incidents  # type: ignore[attr-defined]
    uploads = service.object_store.uploads  # type: ignore[attr-defined]

    assert uploads == []
    assert len(incidents) == 1
    assert incidents[0]["clip_url"] is None
    assert incidents[0]["storage_bytes"] == 0
    assert incidents[0]["payload"]["storage_quota_exceeded"] is True
    assert incidents[0]["payload"]["plate_text"] == "ZH987654"
