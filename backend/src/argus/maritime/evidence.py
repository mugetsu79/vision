from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.link.service import LinkService
from argus.maritime.contracts import (
    JsonObject,
    MaritimeAISPositionRecord,
    MaritimeCarrierTerminalRecord,
    MaritimeEvidenceContextRecord,
    MaritimeEvidenceExportRecord,
    MaritimePortCallRecord,
    MaritimeVesselRecord,
    MaritimeVoyageRecord,
)
from argus.maritime.service import MaritimeRuntimeService
from argus.maritime.tables import (
    MaritimeEvidenceContext,
    MaritimeEvidenceExport,
)
from argus.models.tables import Camera, EvidenceArtifact, EvidenceLedgerEntry, Incident, Site

AIS_FRESHNESS_WINDOW = timedelta(minutes=30)
CARRIER_FRESHNESS_WINDOW = timedelta(minutes=30)


@dataclass(frozen=True, slots=True)
class CoreIncidentEvidenceRecord:
    incident_id: UUID
    camera_id: UUID
    incident_time: datetime
    scene_contract_hash: str | None = None
    privacy_manifest_hash: str | None = None
    runtime_passport_hash: str | None = None
    recording_policy: JsonObject | None = None
    artifact_hashes: dict[UUID, str] | None = None
    ledger_summary: JsonObject | None = None
    time_source: JsonObject | None = None


class MaritimeEvidenceError(ValueError):
    pass


class MaritimeEvidenceNotFoundError(MaritimeEvidenceError):
    pass


class MaritimeEvidenceService:
    def __init__(
        self,
        *,
        maritime_service: MaritimeRuntimeService,
        link_service: LinkService,
        tenant_id: UUID,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.maritime_service = maritime_service
        self.link_service = link_service
        self.tenant_id = tenant_id
        self.session_factory = session_factory
        self._camera_sites: dict[UUID, UUID] = {}
        self._incidents: dict[UUID, CoreIncidentEvidenceRecord] = {}
        self._contexts: dict[UUID, MaritimeEvidenceContextRecord] = {}
        self._exports: list[MaritimeEvidenceExportRecord] = []

    def register_camera_site(self, *, camera_id: UUID, site_id: UUID) -> None:
        self._camera_sites[camera_id] = site_id

    def register_incident(
        self,
        *,
        incident_id: UUID,
        camera_id: UUID,
        incident_time: datetime,
        scene_contract_hash: str | None = None,
        privacy_manifest_hash: str | None = None,
        runtime_passport_hash: str | None = None,
        recording_policy: Mapping[str, object] | None = None,
        artifact_hashes: Mapping[UUID, str] | None = None,
        ledger_summary: Mapping[str, object] | None = None,
        time_source: Mapping[str, object] | None = None,
    ) -> None:
        self._incidents[incident_id] = CoreIncidentEvidenceRecord(
            incident_id=incident_id,
            camera_id=camera_id,
            incident_time=incident_time,
            scene_contract_hash=scene_contract_hash,
            privacy_manifest_hash=privacy_manifest_hash,
            runtime_passport_hash=runtime_passport_hash,
            recording_policy=_json_object(recording_policy),
            artifact_hashes=dict(artifact_hashes or {}),
            ledger_summary=_json_object(ledger_summary),
            time_source=_json_object(time_source),
        )

    async def create_context(
        self,
        *,
        incident_id: UUID,
        vessel_id: UUID | None = None,
        voyage_id: UUID | None = None,
        port_call_id: UUID | None = None,
        resolution_source: str = "manual",
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeEvidenceContextRecord:
        incident = await self._incident(incident_id)
        now = _now()
        existing = self._contexts.get(incident_id)
        record = MaritimeEvidenceContextRecord(
            id=existing.id if existing is not None else uuid4(),
            tenant_id=self.tenant_id,
            incident_id=incident_id,
            camera_id=incident.camera_id,
            incident_time=incident.incident_time,
            vessel_id=vessel_id,
            voyage_id=voyage_id,
            port_call_id=port_call_id,
            resolution_source=resolution_source,
            telemetry_freshness={"ais": "missing", "carrier": "missing"},
            partial=True,
            metadata=_json_object(metadata),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        if self.session_factory is None:
            self._contexts[incident_id] = record
            return record
        async with self.session_factory() as session:
            row = await self._db_context_for_incident(session, incident_id)
            if row is None:
                row = MaritimeEvidenceContext(
                    id=record.id,
                    tenant_id=record.tenant_id,
                    incident_id=record.incident_id,
                    camera_id=record.camera_id,
                    incident_time=record.incident_time,
                    vessel_id=record.vessel_id,
                    voyage_id=record.voyage_id,
                    port_call_id=record.port_call_id,
                    resolution_source=record.resolution_source,
                    telemetry_freshness=record.telemetry_freshness,
                    partial=record.partial,
                    attributes=record.metadata,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
                session.add(row)
            else:
                row.vessel_id = vessel_id
                row.voyage_id = voyage_id
                row.port_call_id = port_call_id
                row.resolution_source = resolution_source
                row.attributes = _json_object(metadata)
                row.updated_at = now
            await session.commit()
            await session.refresh(row)
        return _context_record(row)

    async def resolve_context(
        self,
        *,
        incident_id: UUID | None = None,
        camera_id: UUID | None = None,
        incident_time: datetime | None = None,
    ) -> MaritimeEvidenceContextRecord:
        if incident_id is not None:
            explicit = await self._explicit_context(incident_id)
            if explicit is not None:
                return explicit
            incident = await self._incident(incident_id)
            camera_id = incident.camera_id
            incident_time = incident.incident_time
        if camera_id is None or incident_time is None:
            raise MaritimeEvidenceError("Provide incident_id or camera_id with incident_time.")

        site_id = await self._site_for_camera(camera_id)
        if site_id is None:
            return self._partial_context(
                incident_id=incident_id,
                camera_id=camera_id,
                incident_time=incident_time,
                resolution_source="unresolved",
            )
        vessel = await self._vessel_for_site(site_id)
        if vessel is None:
            return self._partial_context(
                incident_id=incident_id,
                camera_id=camera_id,
                incident_time=incident_time,
                resolution_source="camera_site_no_vessel",
            )
        voyage = await self._active_voyage(vessel_id=vessel.id, incident_time=incident_time)
        port_call = await self._nearest_port_call(
            voyage_id=voyage.id if voyage is not None else None,
            incident_time=incident_time,
        )
        telemetry = await self.maritime_service.aget_vessel_telemetry(
            tenant_id=self.tenant_id,
            vessel_id=vessel.id,
        )
        ais = _fresh_ais(telemetry.latest_ais_position, incident_time)
        carrier = _fresh_carrier(telemetry.carrier_terminal, incident_time)
        freshness: JsonObject = {
            "ais": _freshness_label(telemetry.latest_ais_position, ais),
            "carrier": _freshness_label(telemetry.carrier_terminal, carrier),
        }
        partial = any(value != "fresh" for value in freshness.values())
        return MaritimeEvidenceContextRecord(
            id=uuid4(),
            tenant_id=self.tenant_id,
            incident_id=incident_id,
            camera_id=camera_id,
            incident_time=incident_time,
            vessel_id=vessel.id,
            voyage_id=voyage.id if voyage is not None else None,
            port_call_id=port_call.id if port_call is not None else None,
            resolution_source="camera_site_active_voyage",
            vessel_name=vessel.name,
            port_name=port_call.port_name if port_call is not None else None,
            ais_position=_ais_payload(ais) if ais is not None else None,
            carrier_terminal=_carrier_payload(carrier) if carrier is not None else None,
            telemetry_freshness=freshness,
            partial=partial,
            metadata={},
            created_at=_now(),
            updated_at=_now(),
        )

    async def core_artifact_hashes(self, incident_id: UUID) -> dict[str, str]:
        incident = await self._incident(incident_id)
        return {
            str(artifact_id): hash_value
            for artifact_id, hash_value in (incident.artifact_hashes or {}).items()
        }

    async def create_export(
        self,
        *,
        incident_id: UUID,
        include_maritime_context: bool = True,
        include_link_passport: bool = True,
    ) -> MaritimeEvidenceExportRecord:
        incident = await self._incident(incident_id)
        artifact_hashes = await self.core_artifact_hashes(incident_id)
        context = (
            await self.resolve_context(incident_id=incident_id)
            if include_maritime_context
            else None
        )
        link_passport = (
            await self.link_service.abuild_incident_passport(
                tenant_id=self.tenant_id,
                incident_id=incident_id,
            )
            if include_link_passport
            else None
        )
        metadata: JsonObject = {
            "incident_id": str(incident_id),
            "artifact_ids": sorted(artifact_hashes),
            "scene_contract_hash": incident.scene_contract_hash,
            "privacy_manifest_hash": incident.privacy_manifest_hash,
            "runtime_passport_hash": incident.runtime_passport_hash,
            "link_passport_hash": (
                f"sha256:{link_passport.passport_hash}" if link_passport is not None else None
            ),
            "ledger_summary": incident.ledger_summary or {},
            "retention_policy": _retention_policy(incident.recording_policy or {}),
            "time_source": incident.time_source or {"source": "unknown"},
        }
        if link_passport is not None:
            metadata["link_passport"] = link_passport.payload
        if context is not None:
            metadata["maritime_context"] = _context_payload(context)
        export = MaritimeEvidenceExportRecord(
            id=uuid4(),
            tenant_id=self.tenant_id,
            incident_id=incident_id,
            metadata=metadata,
            artifact_hashes=artifact_hashes,
            created_at=_now(),
        )
        if self.session_factory is None:
            self._exports.append(export)
            return export
        async with self.session_factory() as session:
            row = MaritimeEvidenceExport(
                id=export.id,
                tenant_id=export.tenant_id,
                incident_id=export.incident_id,
                export_metadata=export.metadata,
                artifact_hashes=export.artifact_hashes,
                created_at=export.created_at,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _export_record(row)

    async def list_exports(
        self,
        *,
        incident_id: UUID | None = None,
    ) -> list[MaritimeEvidenceExportRecord]:
        if self.session_factory is None:
            return [
                export
                for export in self._exports
                if incident_id is None or export.incident_id == incident_id
            ]
        async with self.session_factory() as session:
            query = select(MaritimeEvidenceExport).where(
                MaritimeEvidenceExport.tenant_id == self.tenant_id
            )
            if incident_id is not None:
                query = query.where(MaritimeEvidenceExport.incident_id == incident_id)
            result = await session.execute(
                query.order_by(MaritimeEvidenceExport.created_at.desc())
            )
        return [_export_record(row) for row in result.scalars().all()]

    async def _explicit_context(
        self,
        incident_id: UUID,
    ) -> MaritimeEvidenceContextRecord | None:
        if self.session_factory is None:
            return self._contexts.get(incident_id)
        async with self.session_factory() as session:
            row = await self._db_context_for_incident(session, incident_id)
        return _context_record(row) if row is not None else None

    async def _incident(self, incident_id: UUID) -> CoreIncidentEvidenceRecord:
        if incident_id in self._incidents:
            return self._incidents[incident_id]
        if self.session_factory is None:
            raise MaritimeEvidenceNotFoundError("Incident not found.")
        async with self.session_factory() as session:
            row = (
                await session.execute(
                    select(Incident)
                    .join(Camera, Camera.id == Incident.camera_id)
                    .join(Site, Site.id == Camera.site_id)
                    .where(Site.tenant_id == self.tenant_id)
                    .where(Incident.id == incident_id)
                )
            ).scalar_one_or_none()
            if row is None:
                raise MaritimeEvidenceNotFoundError("Incident not found.")
            artifacts = await session.execute(
                select(EvidenceArtifact.id, EvidenceArtifact.sha256)
                .join(Incident, Incident.id == EvidenceArtifact.incident_id)
                .join(Camera, Camera.id == Incident.camera_id)
                .join(Site, Site.id == Camera.site_id)
                .where(
                    Site.tenant_id == self.tenant_id,
                    EvidenceArtifact.incident_id == incident_id,
                )
            )
            ledger_rows = await session.execute(
                select(EvidenceLedgerEntry).where(
                    EvidenceLedgerEntry.tenant_id == self.tenant_id,
                    EvidenceLedgerEntry.incident_id == incident_id,
                )
            )
        ledger_entries = list(ledger_rows.scalars().all())
        latest = max(ledger_entries, key=lambda entry: entry.sequence, default=None)
        return CoreIncidentEvidenceRecord(
            incident_id=row.id,
            camera_id=row.camera_id,
            incident_time=row.ts,
            scene_contract_hash=row.scene_contract_hash,
            privacy_manifest_hash=row.privacy_manifest_hash,
            runtime_passport_hash=row.runtime_passport_hash,
            recording_policy=dict(row.recording_policy or {}),
            artifact_hashes={artifact_id: sha256 for artifact_id, sha256 in artifacts.all()},
            ledger_summary={
                "entry_count": len(ledger_entries),
                "latest_action": latest.action.value if latest is not None else None,
            },
            time_source={"source": "incident_ts"},
        )

    async def _site_for_camera(self, camera_id: UUID) -> UUID | None:
        if camera_id in self._camera_sites:
            return self._camera_sites[camera_id]
        if self.session_factory is None:
            return None
        async with self.session_factory() as session:
            return (
                await session.execute(
                    select(Camera.site_id)
                    .join(Site, Site.id == Camera.site_id)
                    .where(Camera.id == camera_id, Site.tenant_id == self.tenant_id)
                )
            ).scalar_one_or_none()

    async def _vessel_for_site(self, site_id: UUID) -> MaritimeVesselRecord | None:
        vessels = await self.maritime_service.alist_vessels(tenant_id=self.tenant_id)
        return next((vessel for vessel in vessels if vessel.site_id == site_id), None)

    async def _active_voyage(
        self,
        *,
        vessel_id: UUID,
        incident_time: datetime,
    ) -> MaritimeVoyageRecord | None:
        voyages = await self.maritime_service.alist_voyages(
            tenant_id=self.tenant_id,
            vessel_id=vessel_id,
        )
        active = [voyage for voyage in voyages if voyage.status == "active"]
        bounded = [
            voyage
            for voyage in active
            if _contains_time(
                incident_time,
                start=voyage.actual_departure_at or voyage.scheduled_departure_at,
                end=voyage.actual_arrival_at or voyage.scheduled_arrival_at,
            )
        ]
        candidates = bounded or active
        return candidates[0] if candidates else None

    async def _nearest_port_call(
        self,
        *,
        voyage_id: UUID | None,
        incident_time: datetime,
    ) -> MaritimePortCallRecord | None:
        if voyage_id is None:
            return None
        port_calls = await self.maritime_service.alist_port_calls(
            tenant_id=self.tenant_id,
            voyage_id=voyage_id,
        )
        if not port_calls:
            return None
        overlapping = [
            port_call
            for port_call in port_calls
            if _contains_time(
                incident_time,
                start=port_call.eta or port_call.ata,
                end=port_call.etd,
            )
        ]
        if overlapping:
            return overlapping[0]
        return min(port_calls, key=lambda port_call: _port_call_distance(port_call, incident_time))

    async def _db_context_for_incident(
        self,
        session: AsyncSession,
        incident_id: UUID,
    ) -> MaritimeEvidenceContext | None:
        result = await session.execute(
            select(MaritimeEvidenceContext).where(
                MaritimeEvidenceContext.tenant_id == self.tenant_id,
                MaritimeEvidenceContext.incident_id == incident_id,
            )
        )
        return result.scalar_one_or_none()

    def _partial_context(
        self,
        *,
        incident_id: UUID | None,
        camera_id: UUID | None,
        incident_time: datetime | None,
        resolution_source: str,
    ) -> MaritimeEvidenceContextRecord:
        now = _now()
        return MaritimeEvidenceContextRecord(
            id=uuid4(),
            tenant_id=self.tenant_id,
            incident_id=incident_id,
            camera_id=camera_id,
            incident_time=incident_time,
            resolution_source=resolution_source,
            telemetry_freshness={"ais": "missing", "carrier": "missing"},
            partial=True,
            metadata={},
            created_at=now,
            updated_at=now,
        )


def _empty_context() -> MaritimeEvidenceContextRecord:
    now = _now()
    return MaritimeEvidenceContextRecord(
        id=uuid4(),
        tenant_id=UUID("00000000-0000-4000-8000-000000000000"),
        incident_id=None,
        camera_id=None,
        incident_time=None,
        resolution_source="empty",
        telemetry_freshness={},
        partial=True,
        created_at=now,
        updated_at=now,
    )


def _contains_time(
    value: datetime,
    *,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    if start is not None and value < start:
        return False
    if end is not None and value > end:
        return False
    return start is not None or end is not None


def _port_call_distance(port_call: MaritimePortCallRecord, incident_time: datetime) -> float:
    candidates = [value for value in (port_call.eta, port_call.ata, port_call.etd) if value]
    if not candidates:
        return float("inf")
    return min(abs((candidate - incident_time).total_seconds()) for candidate in candidates)


def _fresh_ais(
    position: MaritimeAISPositionRecord | None,
    incident_time: datetime,
) -> MaritimeAISPositionRecord | None:
    if position is None or position.reported_at > incident_time:
        return None
    if incident_time - position.reported_at > AIS_FRESHNESS_WINDOW:
        return None
    return position


def _fresh_carrier(
    terminal: MaritimeCarrierTerminalRecord | None,
    incident_time: datetime,
) -> MaritimeCarrierTerminalRecord | None:
    if terminal is None or terminal.last_seen_at > incident_time:
        return None
    if incident_time - terminal.last_seen_at > CARRIER_FRESHNESS_WINDOW:
        return None
    return terminal


def _freshness_label(source: object | None, fresh: object | None) -> str:
    if source is None:
        return "missing"
    if fresh is None:
        return "stale"
    return "fresh"


def _context_payload(context: MaritimeEvidenceContextRecord) -> JsonObject:
    return {
        "vessel_id": str(context.vessel_id) if context.vessel_id is not None else None,
        "voyage_id": str(context.voyage_id) if context.voyage_id is not None else None,
        "port_call_id": (
            str(context.port_call_id) if context.port_call_id is not None else None
        ),
        "vessel_name": context.vessel_name,
        "port_name": context.port_name,
        "resolution_source": context.resolution_source,
        "telemetry_freshness": context.telemetry_freshness,
        "partial": context.partial,
        "ais_position": context.ais_position,
        "carrier_terminal": context.carrier_terminal,
    }


def _ais_payload(position: MaritimeAISPositionRecord) -> JsonObject:
    return {
        "mmsi": position.mmsi,
        "latitude": position.latitude,
        "longitude": position.longitude,
        "reported_at": position.reported_at.isoformat(),
    }


def _carrier_payload(terminal: MaritimeCarrierTerminalRecord) -> JsonObject:
    return {
        "terminal_id": terminal.terminal_id,
        "provider": terminal.provider,
        "status": terminal.status,
        "link_state": terminal.link_state,
        "last_seen_at": terminal.last_seen_at.isoformat(),
    }


def _retention_policy(recording_policy: Mapping[str, object]) -> JsonObject:
    return {
        "mode": recording_policy.get("mode", "unknown"),
        "retention_days": recording_policy.get("retention_days"),
    }


def _json_object(value: Mapping[str, object] | None) -> JsonObject:
    if value is None:
        return {}
    return {str(key): item for key, item in value.items()}


def _context_record(row: MaritimeEvidenceContext) -> MaritimeEvidenceContextRecord:
    return MaritimeEvidenceContextRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        incident_id=row.incident_id,
        camera_id=row.camera_id,
        incident_time=row.incident_time,
        vessel_id=row.vessel_id,
        voyage_id=row.voyage_id,
        port_call_id=row.port_call_id,
        resolution_source=row.resolution_source,
        vessel_name=row.vessel_name,
        port_name=row.port_name,
        ais_position=dict(row.ais_position) if row.ais_position is not None else None,
        carrier_terminal=(
            dict(row.carrier_terminal) if row.carrier_terminal is not None else None
        ),
        telemetry_freshness=dict(row.telemetry_freshness or {}),
        partial=row.partial,
        metadata=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _export_record(row: MaritimeEvidenceExport) -> MaritimeEvidenceExportRecord:
    return MaritimeEvidenceExportRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        incident_id=row.incident_id,
        metadata=dict(row.export_metadata or {}),
        artifact_hashes={str(key): str(value) for key, value in row.artifact_hashes.items()},
        created_at=row.created_at,
    )


def _now() -> datetime:
    return datetime.now(tz=UTC)
