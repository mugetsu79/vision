from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.maritime.contracts import (
    CarrierLinkState,
    CarrierStatus,
    JsonObject,
    MaritimeAISPositionRecord,
    MaritimeCarrierTerminalRecord,
    MaritimeNMEAReadingRecord,
    MaritimePortCallRecord,
    MaritimeRuntimeContribution,
    MaritimeTelemetryIngestEventRecord,
    MaritimeTelemetrySnapshot,
    MaritimeVesselRecord,
    MaritimeVoyageRecord,
    PortCallStatus,
    VoyageStatus,
)
from argus.maritime.tables import (
    MaritimeAISPosition,
    MaritimeCarrierTerminal,
    MaritimeNMEAReading,
    MaritimePortCall,
    MaritimeTelemetryIngestEvent,
    MaritimeVessel,
    MaritimeVoyage,
)
from argus.maritime.telemetry import (
    AISPositionReading,
    CarrierTerminalReading,
    NmeaSentenceReading,
    TransferLaneDecision,
    select_transfer_lane,
)
from argus.models.tables import Site
from argus.services.pack_registry import PackManifest, PackRegistry

MARITIME_PACK_ID = "maritime-fleet"
MARITIME_REQUIRED_CORE_CAPABILITIES = [
    "argus.link",
    "argus.fleet",
    "argus.billing",
    "argus.support",
]
VOYAGE_STATUSES = {"planned", "active", "completed", "cancelled"}
PORT_CALL_STATUSES = {"scheduled", "arrived", "alongside", "departed", "cancelled"}
CARRIER_STATUSES = {"unknown", "online", "degraded", "offline", "blocked"}
CARRIER_LINK_STATES = {
    "unknown",
    "satellite_good",
    "satellite_degraded",
    "port_wifi",
    "dark",
    "recovering",
}
TELEMETRY_EVENT_STATUSES = {"succeeded", "partial", "failed"}


class MaritimeError(ValueError):
    pass


class MaritimeConflictError(MaritimeError):
    pass


class MaritimeNotFoundError(MaritimeError):
    pass


class MaritimeStateError(MaritimeConflictError):
    pass


class MaritimeRuntimeService:
    def __init__(
        self,
        *,
        pack_registry: PackRegistry,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self.pack_registry = pack_registry
        self.session_factory = session_factory
        self._vessels: dict[UUID, MaritimeVesselRecord] = {}
        self._voyages: dict[UUID, MaritimeVoyageRecord] = {}
        self._port_calls: dict[UUID, MaritimePortCallRecord] = {}
        self._ais_positions: list[MaritimeAISPositionRecord] = []
        self._nmea_readings: list[MaritimeNMEAReadingRecord] = []
        self._carrier_terminals: dict[tuple[UUID, str], MaritimeCarrierTerminalRecord] = {}
        self._telemetry_events: list[MaritimeTelemetryIngestEventRecord] = []

    def runtime(self) -> MaritimeRuntimeContribution:
        manifest = self._manifest()
        if not manifest.is_runtime_enabled:
            raise ValueError("Maritime runtime pack is not enabled.")
        if not manifest.metadata.implementation_commitment:
            raise ValueError("Maritime runtime pack has no implementation commitment.")
        return MaritimeRuntimeContribution(
            pack_id=manifest.metadata.id,
            manifest_version=manifest.api_version,
            enabled=manifest.is_runtime_enabled,
            implementation_commitment=manifest.metadata.implementation_commitment,
            required_core_capabilities=list(MARITIME_REQUIRED_CORE_CAPABILITIES),
            engine_required_capabilities=list(manifest.engine.required_capabilities),
            scene_templates=[
                template.model_dump(mode="python") for template in manifest.scene_templates
            ],
            model_presets=manifest.model_presets.model_dump(mode="python"),
            evidence_fields=list(manifest.evidence_context.fields),
            integrations=[
                integration.model_dump(mode="python") for integration in manifest.integrations
            ],
            ui_labels=dict(manifest.ui_extensions.navigation_labels),
            ui_panels=list(manifest.ui_extensions.panels),
            billing_labels=list(manifest.billing.hierarchy_labels),
            billing_meters=list(manifest.billing.meters),
        )

    def runtime_payload(self) -> JsonObject:
        runtime = self.runtime()
        return {
            "pack_id": runtime.pack_id,
            "manifest_version": runtime.manifest_version,
            "enabled": runtime.enabled,
            "implementation_commitment": runtime.implementation_commitment,
            "required_core_capabilities": runtime.required_core_capabilities,
            "engine_required_capabilities": runtime.engine_required_capabilities,
            "scene_templates": runtime.scene_templates,
            "model_presets": runtime.model_presets,
            "evidence_fields": runtime.evidence_fields,
            "integrations": runtime.integrations,
            "ui_labels": runtime.ui_labels,
            "ui_panels": runtime.ui_panels,
            "billing_labels": runtime.billing_labels,
            "billing_meters": runtime.billing_meters,
        }

    def create_vessel(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        name: str,
        imo_number: str | None = None,
        mmsi: str | None = None,
        call_sign: str | None = None,
        flag_state: str | None = None,
        vessel_type: str | None = None,
        owner_label: str | None = None,
        manager_label: str | None = None,
        charterer_label: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVesselRecord:
        self._ensure_memory_mode()
        self._validate_vessel_identity(
            name=name,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )
        self._ensure_memory_vessel_unique(
            tenant_id=tenant_id,
            site_id=site_id,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )
        now = _now()
        vessel = MaritimeVesselRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            site_id=site_id,
            name=name,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
            flag_state=flag_state,
            vessel_type=vessel_type,
            owner_label=owner_label,
            manager_label=manager_label,
            charterer_label=charterer_label,
            metadata=_json_object(metadata),
            created_at=now,
            updated_at=now,
        )
        self._vessels[vessel.id] = vessel
        return vessel

    async def acreate_vessel(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        name: str,
        imo_number: str | None = None,
        mmsi: str | None = None,
        call_sign: str | None = None,
        flag_state: str | None = None,
        vessel_type: str | None = None,
        owner_label: str | None = None,
        manager_label: str | None = None,
        charterer_label: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVesselRecord:
        if self.session_factory is None:
            return self.create_vessel(
                tenant_id=tenant_id,
                site_id=site_id,
                name=name,
                imo_number=imo_number,
                mmsi=mmsi,
                call_sign=call_sign,
                flag_state=flag_state,
                vessel_type=vessel_type,
                owner_label=owner_label,
                manager_label=manager_label,
                charterer_label=charterer_label,
                metadata=metadata,
            )
        self._validate_vessel_identity(
            name=name,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )
        async with self.session_factory() as session:
            await self._aensure_site_belongs_to_tenant(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
            )
            await self._aensure_vessel_unique(
                session,
                tenant_id=tenant_id,
                site_id=site_id,
                imo_number=imo_number,
                mmsi=mmsi,
                call_sign=call_sign,
            )
            now = _now()
            row = MaritimeVessel(
                id=uuid4(),
                tenant_id=tenant_id,
                site_id=site_id,
                name=name,
                imo_number=imo_number,
                mmsi=mmsi,
                call_sign=call_sign,
                flag_state=flag_state,
                vessel_type=vessel_type,
                owner_label=owner_label,
                manager_label=manager_label,
                charterer_label=charterer_label,
                active=True,
                attributes=_json_object(metadata),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            try:
                await session.commit()
                await session.refresh(row)
            except IntegrityError as exc:
                await session.rollback()
                raise MaritimeConflictError(
                    "Vessel identifier or site binding already belongs to a vessel."
                ) from exc
        return _vessel_record(row)

    def ensure_vessel_identifiers_available(
        self,
        *,
        tenant_id: UUID,
        imo_number: str | None = None,
        mmsi: str | None = None,
        call_sign: str | None = None,
    ) -> None:
        self._ensure_memory_mode()
        self._ensure_memory_vessel_identifiers_unique(
            tenant_id=tenant_id,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )

    async def aensure_vessel_identifiers_available(
        self,
        *,
        tenant_id: UUID,
        imo_number: str | None = None,
        mmsi: str | None = None,
        call_sign: str | None = None,
    ) -> None:
        if self.session_factory is None:
            self.ensure_vessel_identifiers_available(
                tenant_id=tenant_id,
                imo_number=imo_number,
                mmsi=mmsi,
                call_sign=call_sign,
            )
            return
        async with self.session_factory() as session:
            await self._aensure_vessel_identifiers_unique(
                session,
                tenant_id=tenant_id,
                imo_number=imo_number,
                mmsi=mmsi,
                call_sign=call_sign,
            )

    def list_vessels(self, *, tenant_id: UUID) -> list[MaritimeVesselRecord]:
        self._ensure_memory_mode()
        return sorted(
            (vessel for vessel in self._vessels.values() if vessel.tenant_id == tenant_id),
            key=lambda vessel: vessel.name,
        )

    async def alist_vessels(self, *, tenant_id: UUID) -> list[MaritimeVesselRecord]:
        if self.session_factory is None:
            return self.list_vessels(tenant_id=tenant_id)
        async with self.session_factory() as session:
            result = await session.execute(
                select(MaritimeVessel)
                .where(MaritimeVessel.tenant_id == tenant_id)
                .order_by(MaritimeVessel.name)
            )
        return [_vessel_record(row) for row in result.scalars().all() if row.tenant_id == tenant_id]

    def get_vessel(self, *, tenant_id: UUID, vessel_id: UUID) -> MaritimeVesselRecord:
        self._ensure_memory_mode()
        vessel = self._vessels.get(vessel_id)
        if vessel is None or vessel.tenant_id != tenant_id:
            raise MaritimeNotFoundError("Vessel not found.")
        return vessel

    async def aget_vessel(self, *, tenant_id: UUID, vessel_id: UUID) -> MaritimeVesselRecord:
        if self.session_factory is None:
            return self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        async with self.session_factory() as session:
            row = await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
        return _vessel_record(row)

    def update_vessel(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        name: str | None = None,
        active: bool | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVesselRecord:
        self._ensure_memory_mode()
        vessel = self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        updated = replace(
            vessel,
            name=name if name is not None else vessel.name,
            active=active if active is not None else vessel.active,
            metadata=_json_object(metadata) if metadata is not None else vessel.metadata,
            updated_at=_now(),
        )
        self._vessels[vessel_id] = updated
        return updated

    async def aupdate_vessel(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        name: str | None = None,
        active: bool | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVesselRecord:
        if self.session_factory is None:
            return self.update_vessel(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                name=name,
                active=active,
                metadata=metadata,
            )
        async with self.session_factory() as session:
            row = await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            if name is not None:
                row.name = name
            if active is not None:
                row.active = active
            if metadata is not None:
                row.attributes = _json_object(metadata)
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _vessel_record(row)

    def deactivate_vessel(self, *, tenant_id: UUID, vessel_id: UUID) -> None:
        self.update_vessel(tenant_id=tenant_id, vessel_id=vessel_id, active=False)

    async def adeactivate_vessel(self, *, tenant_id: UUID, vessel_id: UUID) -> None:
        await self.aupdate_vessel(tenant_id=tenant_id, vessel_id=vessel_id, active=False)

    def create_voyage(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        name: str,
        voyage_number: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        scheduled_departure_at: datetime | None = None,
        scheduled_arrival_at: datetime | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVoyageRecord:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        now = _now()
        voyage = MaritimeVoyageRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            name=name,
            voyage_number=voyage_number,
            origin=origin,
            destination=destination,
            status="planned",
            scheduled_departure_at=scheduled_departure_at,
            scheduled_arrival_at=scheduled_arrival_at,
            metadata=_json_object(metadata),
            created_at=now,
            updated_at=now,
        )
        self._voyages[voyage.id] = voyage
        return voyage

    async def acreate_voyage(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        name: str,
        voyage_number: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        scheduled_departure_at: datetime | None = None,
        scheduled_arrival_at: datetime | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVoyageRecord:
        if self.session_factory is None:
            return self.create_voyage(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                name=name,
                voyage_number=voyage_number,
                origin=origin,
                destination=destination,
                scheduled_departure_at=scheduled_departure_at,
                scheduled_arrival_at=scheduled_arrival_at,
                metadata=metadata,
            )
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            now = _now()
            row = MaritimeVoyage(
                id=uuid4(),
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                name=name,
                voyage_number=voyage_number,
                origin=origin,
                destination=destination,
                status="planned",
                scheduled_departure_at=scheduled_departure_at,
                scheduled_arrival_at=scheduled_arrival_at,
                attributes=_json_object(metadata),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _voyage_record(row)

    def list_voyages(self, *, tenant_id: UUID, vessel_id: UUID) -> list[MaritimeVoyageRecord]:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        return sorted(
            (
                voyage
                for voyage in self._voyages.values()
                if voyage.tenant_id == tenant_id and voyage.vessel_id == vessel_id
            ),
            key=lambda voyage: voyage.created_at,
        )

    async def alist_voyages(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
    ) -> list[MaritimeVoyageRecord]:
        if self.session_factory is None:
            return self.list_voyages(tenant_id=tenant_id, vessel_id=vessel_id)
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            result = await session.execute(
                select(MaritimeVoyage).where(
                    MaritimeVoyage.tenant_id == tenant_id,
                    MaritimeVoyage.vessel_id == vessel_id,
                )
            )
        return [_voyage_record(row) for row in result.scalars().all()]

    def get_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        self._ensure_memory_mode()
        voyage = self._voyages.get(voyage_id)
        if voyage is None or voyage.tenant_id != tenant_id:
            raise MaritimeNotFoundError("Voyage not found.")
        return voyage

    async def aget_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        if self.session_factory is None:
            return self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        async with self.session_factory() as session:
            row = await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
        return _voyage_record(row)

    def update_voyage(
        self,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
        name: str | None = None,
        voyage_number: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        scheduled_departure_at: datetime | None = None,
        scheduled_arrival_at: datetime | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVoyageRecord:
        self._ensure_memory_mode()
        voyage = self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        updated = replace(
            voyage,
            name=name if name is not None else voyage.name,
            voyage_number=voyage_number if voyage_number is not None else voyage.voyage_number,
            origin=origin if origin is not None else voyage.origin,
            destination=destination if destination is not None else voyage.destination,
            scheduled_departure_at=(
                scheduled_departure_at
                if scheduled_departure_at is not None
                else voyage.scheduled_departure_at
            ),
            scheduled_arrival_at=(
                scheduled_arrival_at
                if scheduled_arrival_at is not None
                else voyage.scheduled_arrival_at
            ),
            metadata=_json_object(metadata) if metadata is not None else voyage.metadata,
            updated_at=_now(),
        )
        self._voyages[voyage.id] = updated
        return updated

    async def aupdate_voyage(
        self,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
        name: str | None = None,
        voyage_number: str | None = None,
        origin: str | None = None,
        destination: str | None = None,
        scheduled_departure_at: datetime | None = None,
        scheduled_arrival_at: datetime | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimeVoyageRecord:
        if self.session_factory is None:
            return self.update_voyage(
                tenant_id=tenant_id,
                voyage_id=voyage_id,
                name=name,
                voyage_number=voyage_number,
                origin=origin,
                destination=destination,
                scheduled_departure_at=scheduled_departure_at,
                scheduled_arrival_at=scheduled_arrival_at,
                metadata=metadata,
            )
        async with self.session_factory() as session:
            row = await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
            if name is not None:
                row.name = name
            if voyage_number is not None:
                row.voyage_number = voyage_number
            if origin is not None:
                row.origin = origin
            if destination is not None:
                row.destination = destination
            if scheduled_departure_at is not None:
                row.scheduled_departure_at = scheduled_departure_at
            if scheduled_arrival_at is not None:
                row.scheduled_arrival_at = scheduled_arrival_at
            if metadata is not None:
                row.attributes = _json_object(metadata)
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _voyage_record(row)

    def activate_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        self._ensure_memory_mode()
        voyage = self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        active = [
            item
            for item in self._voyages.values()
            if item.tenant_id == tenant_id
            and item.vessel_id == voyage.vessel_id
            and item.status == "active"
            and item.id != voyage.id
        ]
        if active:
            raise MaritimeConflictError("Vessel already has an active voyage.")
        updated = _replace_voyage(
            voyage,
            status="active",
            actual_departure_at=voyage.actual_departure_at or _now(),
        )
        self._voyages[voyage.id] = updated
        return updated

    async def aactivate_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        if self.session_factory is None:
            return self.activate_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        async with self.session_factory() as session:
            row = await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
            await self._aensure_no_active_voyage(
                session,
                tenant_id=tenant_id,
                vessel_id=row.vessel_id,
                excluded_voyage_id=row.id,
            )
            row.status = "active"
            if row.actual_departure_at is None:
                row.actual_departure_at = _now()
            row.updated_at = _now()
            try:
                await session.commit()
                await session.refresh(row)
            except IntegrityError as exc:
                await session.rollback()
                raise MaritimeConflictError("Vessel already has an active voyage.") from exc
        return _voyage_record(row)

    def complete_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        self._ensure_memory_mode()
        voyage = self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        if voyage.actual_departure_at is None:
            raise MaritimeStateError("Voyage requires departure before completion.")
        updated = _replace_voyage(voyage, status="completed", actual_arrival_at=_now())
        self._voyages[voyage.id] = updated
        return updated

    async def acomplete_voyage(self, *, tenant_id: UUID, voyage_id: UUID) -> MaritimeVoyageRecord:
        if self.session_factory is None:
            return self.complete_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        async with self.session_factory() as session:
            row = await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
            if row.actual_departure_at is None:
                raise MaritimeStateError("Voyage requires departure before completion.")
            row.status = "completed"
            row.actual_arrival_at = _now()
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _voyage_record(row)

    def create_port_call(
        self,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
        port_name: str,
        un_locode: str | None = None,
        terminal_name: str | None = None,
        berth: str | None = None,
        eta: datetime | None = None,
        etd: datetime | None = None,
        link_profile: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimePortCallRecord:
        self._ensure_memory_mode()
        voyage = self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        now = _now()
        port_call = MaritimePortCallRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            vessel_id=voyage.vessel_id,
            voyage_id=voyage_id,
            port_name=port_name,
            un_locode=un_locode,
            terminal_name=terminal_name,
            berth=berth,
            status="scheduled",
            eta=eta,
            etd=etd,
            link_profile=link_profile,
            metadata=_json_object(metadata),
            created_at=now,
            updated_at=now,
        )
        self._port_calls[port_call.id] = port_call
        return port_call

    async def acreate_port_call(
        self,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
        port_name: str,
        un_locode: str | None = None,
        terminal_name: str | None = None,
        berth: str | None = None,
        eta: datetime | None = None,
        etd: datetime | None = None,
        link_profile: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimePortCallRecord:
        if self.session_factory is None:
            return self.create_port_call(
                tenant_id=tenant_id,
                voyage_id=voyage_id,
                port_name=port_name,
                un_locode=un_locode,
                terminal_name=terminal_name,
                berth=berth,
                eta=eta,
                etd=etd,
                link_profile=link_profile,
                metadata=metadata,
            )
        async with self.session_factory() as session:
            voyage = await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
            now = _now()
            row = MaritimePortCall(
                id=uuid4(),
                tenant_id=tenant_id,
                vessel_id=voyage.vessel_id,
                voyage_id=voyage_id,
                port_name=port_name,
                un_locode=un_locode,
                terminal_name=terminal_name,
                berth=berth,
                status="scheduled",
                eta=eta,
                etd=etd,
                link_profile=link_profile,
                attributes=_json_object(metadata),
                created_at=now,
                updated_at=now,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _port_call_record(row)

    def list_port_calls(self, *, tenant_id: UUID, voyage_id: UUID) -> list[MaritimePortCallRecord]:
        self._ensure_memory_mode()
        self.get_voyage(tenant_id=tenant_id, voyage_id=voyage_id)
        return sorted(
            (
                port_call
                for port_call in self._port_calls.values()
                if port_call.tenant_id == tenant_id and port_call.voyage_id == voyage_id
            ),
            key=lambda port_call: port_call.created_at,
        )

    async def alist_port_calls(
        self,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
    ) -> list[MaritimePortCallRecord]:
        if self.session_factory is None:
            return self.list_port_calls(tenant_id=tenant_id, voyage_id=voyage_id)
        async with self.session_factory() as session:
            await self._aget_voyage_row(session, tenant_id=tenant_id, voyage_id=voyage_id)
            result = await session.execute(
                select(MaritimePortCall).where(
                    MaritimePortCall.tenant_id == tenant_id,
                    MaritimePortCall.voyage_id == voyage_id,
                )
            )
        return [_port_call_record(row) for row in result.scalars().all()]

    def update_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
        port_name: str | None = None,
        un_locode: str | None = None,
        terminal_name: str | None = None,
        berth: str | None = None,
        eta: datetime | None = None,
        etd: datetime | None = None,
        link_profile: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimePortCallRecord:
        self._ensure_memory_mode()
        port_call = self._get_port_call(tenant_id=tenant_id, port_call_id=port_call_id)
        updated = replace(
            port_call,
            port_name=port_name if port_name is not None else port_call.port_name,
            un_locode=un_locode if un_locode is not None else port_call.un_locode,
            terminal_name=terminal_name if terminal_name is not None else port_call.terminal_name,
            berth=berth if berth is not None else port_call.berth,
            eta=eta if eta is not None else port_call.eta,
            etd=etd if etd is not None else port_call.etd,
            link_profile=link_profile if link_profile is not None else port_call.link_profile,
            metadata=_json_object(metadata) if metadata is not None else port_call.metadata,
            updated_at=_now(),
        )
        self._port_calls[port_call.id] = updated
        return updated

    async def aupdate_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
        port_name: str | None = None,
        un_locode: str | None = None,
        terminal_name: str | None = None,
        berth: str | None = None,
        eta: datetime | None = None,
        etd: datetime | None = None,
        link_profile: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> MaritimePortCallRecord:
        if self.session_factory is None:
            return self.update_port_call(
                tenant_id=tenant_id,
                port_call_id=port_call_id,
                port_name=port_name,
                un_locode=un_locode,
                terminal_name=terminal_name,
                berth=berth,
                eta=eta,
                etd=etd,
                link_profile=link_profile,
                metadata=metadata,
            )
        async with self.session_factory() as session:
            row = await self._aget_port_call_row(
                session,
                tenant_id=tenant_id,
                port_call_id=port_call_id,
            )
            if port_name is not None:
                row.port_name = port_name
            if un_locode is not None:
                row.un_locode = un_locode
            if terminal_name is not None:
                row.terminal_name = terminal_name
            if berth is not None:
                row.berth = berth
            if eta is not None:
                row.eta = eta
            if etd is not None:
                row.etd = etd
            if link_profile is not None:
                row.link_profile = link_profile
            if metadata is not None:
                row.attributes = _json_object(metadata)
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _port_call_record(row)

    def arrive_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
    ) -> MaritimePortCallRecord:
        self._ensure_memory_mode()
        port_call = self._get_port_call(tenant_id=tenant_id, port_call_id=port_call_id)
        updated = _replace_port_call(port_call, status="arrived", ata=_now())
        self._port_calls[port_call.id] = updated
        return updated

    async def aarrive_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
    ) -> MaritimePortCallRecord:
        if self.session_factory is None:
            return self.arrive_port_call(tenant_id=tenant_id, port_call_id=port_call_id)
        async with self.session_factory() as session:
            row = await self._aget_port_call_row(
                session,
                tenant_id=tenant_id,
                port_call_id=port_call_id,
            )
            row.status = "arrived"
            row.ata = _now()
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _port_call_record(row)

    def depart_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
    ) -> MaritimePortCallRecord:
        self._ensure_memory_mode()
        port_call = self._get_port_call(tenant_id=tenant_id, port_call_id=port_call_id)
        if port_call.status not in {"arrived", "alongside"}:
            raise MaritimeStateError("Port call must be arrived or alongside before departure.")
        updated = _replace_port_call(port_call, status="departed", atd=_now())
        self._port_calls[port_call.id] = updated
        return updated

    async def adepart_port_call(
        self,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
    ) -> MaritimePortCallRecord:
        if self.session_factory is None:
            return self.depart_port_call(tenant_id=tenant_id, port_call_id=port_call_id)
        async with self.session_factory() as session:
            row = await self._aget_port_call_row(
                session,
                tenant_id=tenant_id,
                port_call_id=port_call_id,
            )
            if row.status not in {"arrived", "alongside"}:
                raise MaritimeStateError("Port call must be arrived or alongside before departure.")
            row.status = "departed"
            row.atd = _now()
            row.updated_at = _now()
            await session.commit()
            await session.refresh(row)
        return _port_call_record(row)

    def ingest_ais_position(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        reading: AISPositionReading,
        source: str | None = None,
    ) -> MaritimeAISPositionRecord:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        source_value = source or reading.source
        duplicate = self._find_memory_ais_duplicate(
            tenant_id=tenant_id,
            source=source_value,
            reading=reading,
        )
        if duplicate is not None:
            return duplicate
        now = _now()
        record = MaritimeAISPositionRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            source=source_value,
            received_at=now,
            reported_at=reading.reported_at,
            mmsi=reading.mmsi,
            latitude=reading.latitude,
            longitude=reading.longitude,
            speed_over_ground=reading.speed_over_ground,
            course_over_ground=reading.course_over_ground,
            heading=reading.heading,
            navigational_status=reading.navigational_status,
            raw_payload=dict(reading.raw_payload),
            created_at=now,
        )
        self._ais_positions.append(record)
        self.record_telemetry_ingest_event(
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            source=source_value,
            event_type="ais_position",
            status="succeeded",
            raw_payload=reading.raw_payload,
            summary="AIS position ingested.",
        )
        return record

    async def aingest_ais_position(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        reading: AISPositionReading,
        source: str | None = None,
    ) -> MaritimeAISPositionRecord:
        if self.session_factory is None:
            return self.ingest_ais_position(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                reading=reading,
                source=source,
            )
        source_value = source or reading.source
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            now = _now()
            row = MaritimeAISPosition(
                id=uuid4(),
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source_value,
                received_at=now,
                reported_at=reading.reported_at,
                mmsi=reading.mmsi,
                latitude=reading.latitude,
                longitude=reading.longitude,
                speed_over_ground=reading.speed_over_ground,
                course_over_ground=reading.course_over_ground,
                heading=reading.heading,
                navigational_status=reading.navigational_status,
                raw_payload=dict(reading.raw_payload),
                created_at=now,
            )
            session.add(row)
            session.add(
                _telemetry_event_row(
                    tenant_id=tenant_id,
                    vessel_id=vessel_id,
                    source=source_value,
                    event_type="ais_position",
                    status="succeeded",
                    raw_payload=reading.raw_payload,
                    summary="AIS position ingested.",
                    failure_count=0,
                    created_at=now,
                )
            )
            try:
                await session.commit()
                await session.refresh(row)
            except IntegrityError:
                await session.rollback()
                existing = await self._afind_ais_duplicate(
                    session,
                    tenant_id=tenant_id,
                    source=source_value,
                    reading=reading,
                )
                if existing is None:
                    raise
                row = existing
        return _ais_position_record(row)

    def ingest_nmea_readings(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        source: str,
        sentences: Sequence[NmeaSentenceReading],
    ) -> list[MaritimeNMEAReadingRecord]:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        records: list[MaritimeNMEAReadingRecord] = []
        for sentence in sentences:
            now = _now()
            record = MaritimeNMEAReadingRecord(
                id=uuid4(),
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source,
                received_at=now,
                sentence_type=sentence.sentence_type,
                timestamp=sentence.timestamp,
                values=dict(sentence.values),
                raw_sentence=sentence.raw_sentence,
                created_at=now,
            )
            self._nmea_readings.append(record)
            records.append(record)
        if records:
            self.record_telemetry_ingest_event(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source,
                event_type="nmea_readings",
                status="succeeded",
                raw_payload={"sentence_count": len(records)},
                summary="NMEA readings ingested.",
            )
        return records

    async def aingest_nmea_readings(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        source: str,
        sentences: Sequence[NmeaSentenceReading],
    ) -> list[MaritimeNMEAReadingRecord]:
        if self.session_factory is None:
            return self.ingest_nmea_readings(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source,
                sentences=sentences,
            )
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            rows: list[MaritimeNMEAReading] = []
            for sentence in sentences:
                now = _now()
                row = MaritimeNMEAReading(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    vessel_id=vessel_id,
                    source=source,
                    received_at=now,
                    sentence_type=sentence.sentence_type,
                    timestamp=sentence.timestamp,
                    values=dict(sentence.values),
                    raw_sentence=sentence.raw_sentence,
                    created_at=now,
                )
                rows.append(row)
                session.add(row)
            if rows:
                session.add(
                    _telemetry_event_row(
                        tenant_id=tenant_id,
                        vessel_id=vessel_id,
                        source=source,
                        event_type="nmea_readings",
                        status="succeeded",
                        raw_payload={"sentence_count": len(rows)},
                        summary="NMEA readings ingested.",
                        failure_count=0,
                        created_at=_now(),
                    )
                )
            await session.commit()
            for row in rows:
                await session.refresh(row)
        return [_nmea_reading_record(row) for row in rows]

    def upsert_carrier_terminal(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        reading: CarrierTerminalReading,
    ) -> MaritimeCarrierTerminalRecord:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        now = _now()
        existing = self._carrier_terminals.get((tenant_id, reading.terminal_id))
        record = MaritimeCarrierTerminalRecord(
            id=existing.id if existing is not None else uuid4(),
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            terminal_id=reading.terminal_id,
            provider=reading.provider,
            status=reading.status,
            link_state=reading.link_state,
            downlink_mbps=reading.downlink_mbps,
            uplink_mbps=reading.uplink_mbps,
            latency_ms=reading.latency_ms,
            packet_loss_percent=reading.packet_loss_percent,
            last_seen_at=reading.last_seen_at,
            raw_payload=dict(reading.raw_payload),
            created_at=existing.created_at if existing is not None else now,
            updated_at=now,
        )
        self._carrier_terminals[(tenant_id, reading.terminal_id)] = record
        self.record_telemetry_ingest_event(
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            source="carrier_terminal",
            event_type="carrier_terminal_state",
            status="succeeded",
            raw_payload=_carrier_event_payload(reading, previous=existing),
            summary="Carrier terminal state ingested.",
        )
        return record

    async def aupsert_carrier_terminal(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        reading: CarrierTerminalReading,
    ) -> MaritimeCarrierTerminalRecord:
        if self.session_factory is None:
            return self.upsert_carrier_terminal(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                reading=reading,
            )
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            row = await self._afind_carrier_terminal(
                session,
                tenant_id=tenant_id,
                terminal_id=reading.terminal_id,
            )
            now = _now()
            previous = _carrier_terminal_record(row) if row is not None else None
            if row is None:
                row = MaritimeCarrierTerminal(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    vessel_id=vessel_id,
                    terminal_id=reading.terminal_id,
                    provider=reading.provider,
                    status=reading.status,
                    link_state=reading.link_state,
                    downlink_mbps=reading.downlink_mbps,
                    uplink_mbps=reading.uplink_mbps,
                    latency_ms=reading.latency_ms,
                    packet_loss_percent=reading.packet_loss_percent,
                    last_seen_at=reading.last_seen_at,
                    raw_payload=dict(reading.raw_payload),
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            else:
                row.vessel_id = vessel_id
                row.provider = reading.provider
                row.status = reading.status
                row.link_state = reading.link_state
                row.downlink_mbps = reading.downlink_mbps
                row.uplink_mbps = reading.uplink_mbps
                row.latency_ms = reading.latency_ms
                row.packet_loss_percent = reading.packet_loss_percent
                row.last_seen_at = reading.last_seen_at
                row.raw_payload = dict(reading.raw_payload)
                row.updated_at = now
            session.add(
                _telemetry_event_row(
                    tenant_id=tenant_id,
                    vessel_id=vessel_id,
                    source="carrier_terminal",
                    event_type="carrier_terminal_state",
                    status="succeeded",
                    raw_payload=_carrier_event_payload(reading, previous=previous),
                    summary="Carrier terminal state ingested.",
                    failure_count=0,
                    created_at=now,
                )
            )
            try:
                await session.commit()
                await session.refresh(row)
            except IntegrityError:
                await session.rollback()
                row = await self._afind_carrier_terminal(
                    session,
                    tenant_id=tenant_id,
                    terminal_id=reading.terminal_id,
                )
                if row is None:
                    raise
                previous = _carrier_terminal_record(row)
                now = _now()
                row.vessel_id = vessel_id
                row.provider = reading.provider
                row.status = reading.status
                row.link_state = reading.link_state
                row.downlink_mbps = reading.downlink_mbps
                row.uplink_mbps = reading.uplink_mbps
                row.latency_ms = reading.latency_ms
                row.packet_loss_percent = reading.packet_loss_percent
                row.last_seen_at = reading.last_seen_at
                row.raw_payload = dict(reading.raw_payload)
                row.updated_at = now
                session.add(
                    _telemetry_event_row(
                        tenant_id=tenant_id,
                        vessel_id=vessel_id,
                        source="carrier_terminal",
                        event_type="carrier_terminal_state",
                        status="succeeded",
                        raw_payload=_carrier_event_payload(reading, previous=previous),
                        summary="Carrier terminal state ingested.",
                        failure_count=0,
                        created_at=now,
                    )
                )
                await session.commit()
                await session.refresh(row)
        return _carrier_terminal_record(row)

    def get_carrier_terminal_by_terminal_id(
        self,
        *,
        tenant_id: UUID,
        terminal_id: str,
    ) -> MaritimeCarrierTerminalRecord | None:
        self._ensure_memory_mode()
        terminal = self._carrier_terminals.get((tenant_id, terminal_id))
        if terminal is None or terminal.tenant_id != tenant_id:
            return None
        return terminal

    async def aget_carrier_terminal_by_terminal_id(
        self,
        *,
        tenant_id: UUID,
        terminal_id: str,
    ) -> MaritimeCarrierTerminalRecord | None:
        if self.session_factory is None:
            return self.get_carrier_terminal_by_terminal_id(
                tenant_id=tenant_id,
                terminal_id=terminal_id,
            )
        async with self.session_factory() as session:
            row = await self._afind_carrier_terminal(
                session,
                tenant_id=tenant_id,
                terminal_id=terminal_id,
            )
        return _carrier_terminal_record(row) if row is not None else None

    def get_vessel_telemetry(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        nmea_limit: int = 20,
    ) -> MaritimeTelemetrySnapshot:
        self._ensure_memory_mode()
        self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        ais_positions = [
            position
            for position in self._ais_positions
            if position.tenant_id == tenant_id and position.vessel_id == vessel_id
        ]
        carrier_terminals = [
            terminal
            for terminal in self._carrier_terminals.values()
            if terminal.tenant_id == tenant_id and terminal.vessel_id == vessel_id
        ]
        nmea_readings = [
            reading
            for reading in self._nmea_readings
            if reading.tenant_id == tenant_id and reading.vessel_id == vessel_id
        ]
        telemetry_events = [
            event
            for event in self._telemetry_events
            if event.tenant_id == tenant_id and event.vessel_id == vessel_id
        ]
        return MaritimeTelemetrySnapshot(
            vessel_id=vessel_id,
            latest_ais_position=max(
                ais_positions,
                key=lambda item: (item.reported_at, item.created_at),
                default=None,
            ),
            carrier_terminal=max(
                carrier_terminals,
                key=lambda item: item.updated_at,
                default=None,
            ),
            recent_nmea_readings=sorted(
                nmea_readings,
                key=lambda item: item.created_at,
                reverse=True,
            )[:nmea_limit],
            recent_ingest_events=sorted(
                telemetry_events,
                key=lambda item: item.created_at,
                reverse=True,
            )[:20],
        )

    async def aget_vessel_telemetry(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        nmea_limit: int = 20,
    ) -> MaritimeTelemetrySnapshot:
        if self.session_factory is None:
            return self.get_vessel_telemetry(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                nmea_limit=nmea_limit,
            )
        async with self.session_factory() as session:
            await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            ais_result = await session.execute(
                select(MaritimeAISPosition)
                .where(
                    MaritimeAISPosition.tenant_id == tenant_id,
                    MaritimeAISPosition.vessel_id == vessel_id,
                )
                .order_by(
                    MaritimeAISPosition.reported_at.desc(),
                    MaritimeAISPosition.created_at.desc(),
                )
                .limit(1)
            )
            carrier_result = await session.execute(
                select(MaritimeCarrierTerminal)
                .where(
                    MaritimeCarrierTerminal.tenant_id == tenant_id,
                    MaritimeCarrierTerminal.vessel_id == vessel_id,
                )
                .order_by(MaritimeCarrierTerminal.updated_at.desc())
                .limit(1)
            )
            nmea_result = await session.execute(
                select(MaritimeNMEAReading)
                .where(
                    MaritimeNMEAReading.tenant_id == tenant_id,
                    MaritimeNMEAReading.vessel_id == vessel_id,
                )
                .order_by(MaritimeNMEAReading.created_at.desc())
                .limit(nmea_limit)
            )
            event_result = await session.execute(
                select(MaritimeTelemetryIngestEvent)
                .where(
                    MaritimeTelemetryIngestEvent.tenant_id == tenant_id,
                    MaritimeTelemetryIngestEvent.vessel_id == vessel_id,
                )
                .order_by(MaritimeTelemetryIngestEvent.created_at.desc())
                .limit(20)
            )
        ais_row = ais_result.scalar_one_or_none()
        carrier_row = carrier_result.scalar_one_or_none()
        return MaritimeTelemetrySnapshot(
            vessel_id=vessel_id,
            latest_ais_position=_ais_position_record(ais_row) if ais_row is not None else None,
            carrier_terminal=(
                _carrier_terminal_record(carrier_row) if carrier_row is not None else None
            ),
            recent_nmea_readings=[
                _nmea_reading_record(row) for row in nmea_result.scalars().all()
            ],
            recent_ingest_events=[
                _telemetry_event_record(row) for row in event_result.scalars().all()
            ],
        )

    def get_carrier_selection(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        priority_lane: str,
        remaining_budget_bytes: int,
    ) -> TransferLaneDecision:
        snapshot = self.get_vessel_telemetry(tenant_id=tenant_id, vessel_id=vessel_id)
        terminal = snapshot.carrier_terminal
        return select_transfer_lane(
            link_state=terminal.link_state if terminal is not None else "unknown",
            terminal_status=terminal.status if terminal is not None else "unknown",
            priority_lane=priority_lane,
            remaining_budget_bytes=remaining_budget_bytes,
        )

    async def aget_carrier_selection(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        priority_lane: str,
        remaining_budget_bytes: int,
    ) -> TransferLaneDecision:
        if self.session_factory is None:
            return self.get_carrier_selection(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                priority_lane=priority_lane,
                remaining_budget_bytes=remaining_budget_bytes,
            )
        snapshot = await self.aget_vessel_telemetry(tenant_id=tenant_id, vessel_id=vessel_id)
        terminal = snapshot.carrier_terminal
        return select_transfer_lane(
            link_state=terminal.link_state if terminal is not None else "unknown",
            terminal_status=terminal.status if terminal is not None else "unknown",
            priority_lane=priority_lane,
            remaining_budget_bytes=remaining_budget_bytes,
        )

    def record_telemetry_ingest_event(
        self,
        *,
        tenant_id: UUID,
        source: str,
        event_type: str,
        status: str,
        raw_payload: Mapping[str, object],
        vessel_id: UUID | None = None,
        summary: str | None = None,
        failure_count: int = 0,
    ) -> MaritimeTelemetryIngestEventRecord:
        self._ensure_memory_mode()
        if vessel_id is not None:
            self.get_vessel(tenant_id=tenant_id, vessel_id=vessel_id)
        _validate_telemetry_event_status(status)
        now = _now()
        event = MaritimeTelemetryIngestEventRecord(
            id=uuid4(),
            tenant_id=tenant_id,
            vessel_id=vessel_id,
            source=source,
            event_type=event_type,
            status=status,
            summary=summary,
            failure_count=failure_count,
            raw_payload=_json_object(raw_payload),
            created_at=now,
        )
        self._telemetry_events.append(event)
        return event

    async def arecord_telemetry_ingest_event(
        self,
        *,
        tenant_id: UUID,
        source: str,
        event_type: str,
        status: str,
        raw_payload: Mapping[str, object],
        vessel_id: UUID | None = None,
        summary: str | None = None,
        failure_count: int = 0,
    ) -> MaritimeTelemetryIngestEventRecord:
        if self.session_factory is None:
            return self.record_telemetry_ingest_event(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source,
                event_type=event_type,
                status=status,
                summary=summary,
                failure_count=failure_count,
                raw_payload=raw_payload,
            )
        _validate_telemetry_event_status(status)
        async with self.session_factory() as session:
            if vessel_id is not None:
                await self._aget_vessel_row(session, tenant_id=tenant_id, vessel_id=vessel_id)
            row = _telemetry_event_row(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
                source=source,
                event_type=event_type,
                status=status,
                raw_payload=raw_payload,
                summary=summary,
                failure_count=failure_count,
                created_at=_now(),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
        return _telemetry_event_record(row)

    def list_telemetry_ingest_events(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID | None = None,
    ) -> list[MaritimeTelemetryIngestEventRecord]:
        self._ensure_memory_mode()
        return sorted(
            (
                event
                for event in self._telemetry_events
                if event.tenant_id == tenant_id
                and (vessel_id is None or event.vessel_id == vessel_id)
            ),
            key=lambda event: event.created_at,
        )

    async def alist_telemetry_ingest_events(
        self,
        *,
        tenant_id: UUID,
        vessel_id: UUID | None = None,
        limit: int = 50,
    ) -> list[MaritimeTelemetryIngestEventRecord]:
        if self.session_factory is None:
            return self.list_telemetry_ingest_events(
                tenant_id=tenant_id,
                vessel_id=vessel_id,
            )[-limit:]
        async with self.session_factory() as session:
            query = select(MaritimeTelemetryIngestEvent).where(
                MaritimeTelemetryIngestEvent.tenant_id == tenant_id,
            )
            if vessel_id is not None:
                query = query.where(MaritimeTelemetryIngestEvent.vessel_id == vessel_id)
            result = await session.execute(
                query.order_by(MaritimeTelemetryIngestEvent.created_at.desc()).limit(limit)
            )
        return [_telemetry_event_record(row) for row in result.scalars().all()]

    def _manifest(self) -> PackManifest:
        try:
            manifest = self.pack_registry.get_pack(MARITIME_PACK_ID)
        except KeyError as exc:
            raise ValueError("Maritime runtime pack manifest not found.") from exc
        if manifest.metadata.id != MARITIME_PACK_ID:
            raise ValueError("Unexpected maritime runtime pack manifest.")
        return manifest

    def _get_port_call(self, *, tenant_id: UUID, port_call_id: UUID) -> MaritimePortCallRecord:
        port_call = self._port_calls.get(port_call_id)
        if port_call is None or port_call.tenant_id != tenant_id:
            raise MaritimeNotFoundError("Port call not found.")
        return port_call

    def _find_memory_ais_duplicate(
        self,
        *,
        tenant_id: UUID,
        source: str,
        reading: AISPositionReading,
    ) -> MaritimeAISPositionRecord | None:
        for position in self._ais_positions:
            if (
                position.tenant_id == tenant_id
                and position.source == source
                and position.mmsi == reading.mmsi
                and position.reported_at == reading.reported_at
                and position.latitude == reading.latitude
                and position.longitude == reading.longitude
            ):
                return position
        return None

    def _validate_vessel_identity(
        self,
        *,
        name: str,
        imo_number: str | None,
        mmsi: str | None,
        call_sign: str | None,
    ) -> None:
        if not any((name, imo_number, mmsi, call_sign)):
            raise MaritimeError("Vessel requires a name or identifier.")

    def _ensure_memory_vessel_unique(
        self,
        *,
        tenant_id: UUID,
        site_id: UUID,
        imo_number: str | None,
        mmsi: str | None,
        call_sign: str | None,
    ) -> None:
        self._ensure_memory_vessel_identifiers_unique(
            tenant_id=tenant_id,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )
        for vessel in self._vessels.values():
            if vessel.tenant_id != tenant_id:
                continue
            if vessel.site_id == site_id:
                raise MaritimeConflictError("site_id already belongs to a vessel.")

    def _ensure_memory_vessel_identifiers_unique(
        self,
        *,
        tenant_id: UUID,
        imo_number: str | None,
        mmsi: str | None,
        call_sign: str | None,
    ) -> None:
        for vessel in self._vessels.values():
            if vessel.tenant_id != tenant_id:
                continue
            for field_name, value in (
                ("imo_number", imo_number),
                ("mmsi", mmsi),
                ("call_sign", call_sign),
            ):
                if value is not None and getattr(vessel, field_name) == value:
                    raise MaritimeConflictError(f"{field_name} already belongs to a vessel.")

    async def _aensure_vessel_unique(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
        imo_number: str | None,
        mmsi: str | None,
        call_sign: str | None,
    ) -> None:
        result = await session.execute(
            select(MaritimeVessel).where(MaritimeVessel.tenant_id == tenant_id)
        )
        rows = result.scalars().all()
        for row in rows:
            if row.site_id == site_id:
                raise MaritimeConflictError("site_id already belongs to a vessel.")
        await self._aensure_vessel_identifiers_unique(
            session,
            tenant_id=tenant_id,
            imo_number=imo_number,
            mmsi=mmsi,
            call_sign=call_sign,
        )

    async def _aensure_vessel_identifiers_unique(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        imo_number: str | None,
        mmsi: str | None,
        call_sign: str | None,
    ) -> None:
        result = await session.execute(
            select(MaritimeVessel).where(MaritimeVessel.tenant_id == tenant_id)
        )
        rows = result.scalars().all()
        for row in rows:
            for field_name, value in (
                ("imo_number", imo_number),
                ("mmsi", mmsi),
                ("call_sign", call_sign),
            ):
                if value is not None and getattr(row, field_name) == value:
                    raise MaritimeConflictError(f"{field_name} already belongs to a vessel.")

    async def _aensure_site_belongs_to_tenant(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        site_id: UUID,
    ) -> None:
        result = await session.execute(
            select(Site.id).where(
                Site.id == site_id,
                Site.tenant_id == tenant_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise MaritimeNotFoundError("Site not found.")

    async def _aget_vessel_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
    ) -> MaritimeVessel:
        result = await session.execute(
            select(MaritimeVessel).where(
                MaritimeVessel.tenant_id == tenant_id,
                MaritimeVessel.id == vessel_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise MaritimeNotFoundError("Vessel not found.")
        return row

    async def _aget_voyage_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        voyage_id: UUID,
    ) -> MaritimeVoyage:
        result = await session.execute(
            select(MaritimeVoyage).where(
                MaritimeVoyage.tenant_id == tenant_id,
                MaritimeVoyage.id == voyage_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise MaritimeNotFoundError("Voyage not found.")
        return row

    async def _aget_port_call_row(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        port_call_id: UUID,
    ) -> MaritimePortCall:
        result = await session.execute(
            select(MaritimePortCall).where(
                MaritimePortCall.tenant_id == tenant_id,
                MaritimePortCall.id == port_call_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise MaritimeNotFoundError("Port call not found.")
        return row

    async def _aensure_no_active_voyage(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        vessel_id: UUID,
        excluded_voyage_id: UUID,
    ) -> None:
        result = await session.execute(
            select(MaritimeVoyage).where(
                MaritimeVoyage.tenant_id == tenant_id,
                MaritimeVoyage.vessel_id == vessel_id,
                MaritimeVoyage.status == "active",
            )
        )
        row = result.scalar_one_or_none()
        if row is not None and row.id != excluded_voyage_id:
            raise MaritimeConflictError("Vessel already has an active voyage.")

    async def _afind_ais_duplicate(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        source: str,
        reading: AISPositionReading,
    ) -> MaritimeAISPosition | None:
        result = await session.execute(
            select(MaritimeAISPosition).where(
                MaritimeAISPosition.tenant_id == tenant_id,
                MaritimeAISPosition.source == source,
                MaritimeAISPosition.mmsi == reading.mmsi,
                MaritimeAISPosition.reported_at == reading.reported_at,
                MaritimeAISPosition.latitude == reading.latitude,
                MaritimeAISPosition.longitude == reading.longitude,
            )
        )
        return result.scalar_one_or_none()

    async def _afind_carrier_terminal(
        self,
        session: AsyncSession,
        *,
        tenant_id: UUID,
        terminal_id: str,
    ) -> MaritimeCarrierTerminal | None:
        result = await session.execute(
            select(MaritimeCarrierTerminal).where(
                MaritimeCarrierTerminal.tenant_id == tenant_id,
                MaritimeCarrierTerminal.terminal_id == terminal_id,
            )
        )
        return result.scalar_one_or_none()

    def _ensure_memory_mode(self) -> None:
        if self.session_factory is not None:
            raise RuntimeError(
                "Use async MaritimeRuntimeService methods when session_factory is configured."
            )


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _json_object(value: Mapping[str, object] | None) -> JsonObject:
    if value is None:
        return {}
    return {str(key): item for key, item in value.items()}


def _voyage_status(value: str) -> VoyageStatus:
    if value not in VOYAGE_STATUSES:
        raise MaritimeError(f"Invalid voyage status: {value}")
    return cast(VoyageStatus, value)


def _port_call_status(value: str) -> PortCallStatus:
    if value not in PORT_CALL_STATUSES:
        raise MaritimeError(f"Invalid port call status: {value}")
    return cast(PortCallStatus, value)


def _validate_telemetry_event_status(value: str) -> None:
    if value not in TELEMETRY_EVENT_STATUSES:
        raise MaritimeError(f"Invalid telemetry event status: {value}")


def _replace_voyage(
    voyage: MaritimeVoyageRecord,
    *,
    status: VoyageStatus,
    actual_departure_at: datetime | None = None,
    actual_arrival_at: datetime | None = None,
) -> MaritimeVoyageRecord:
    return MaritimeVoyageRecord(
        id=voyage.id,
        tenant_id=voyage.tenant_id,
        vessel_id=voyage.vessel_id,
        name=voyage.name,
        voyage_number=voyage.voyage_number,
        origin=voyage.origin,
        destination=voyage.destination,
        status=status,
        scheduled_departure_at=voyage.scheduled_departure_at,
        scheduled_arrival_at=voyage.scheduled_arrival_at,
        actual_departure_at=actual_departure_at or voyage.actual_departure_at,
        actual_arrival_at=actual_arrival_at or voyage.actual_arrival_at,
        metadata=voyage.metadata,
        created_at=voyage.created_at,
        updated_at=_now(),
    )


def _replace_port_call(
    port_call: MaritimePortCallRecord,
    *,
    status: PortCallStatus,
    ata: datetime | None = None,
    atd: datetime | None = None,
) -> MaritimePortCallRecord:
    return MaritimePortCallRecord(
        id=port_call.id,
        tenant_id=port_call.tenant_id,
        vessel_id=port_call.vessel_id,
        voyage_id=port_call.voyage_id,
        port_name=port_call.port_name,
        un_locode=port_call.un_locode,
        terminal_name=port_call.terminal_name,
        berth=port_call.berth,
        status=status,
        eta=port_call.eta,
        ata=ata or port_call.ata,
        etd=port_call.etd,
        atd=atd or port_call.atd,
        link_profile=port_call.link_profile,
        metadata=port_call.metadata,
        created_at=port_call.created_at,
        updated_at=_now(),
    )


def _vessel_record(row: MaritimeVessel) -> MaritimeVesselRecord:
    return MaritimeVesselRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        site_id=row.site_id,
        name=row.name,
        imo_number=row.imo_number,
        mmsi=row.mmsi,
        call_sign=row.call_sign,
        flag_state=row.flag_state,
        vessel_type=row.vessel_type,
        owner_label=row.owner_label,
        manager_label=row.manager_label,
        charterer_label=row.charterer_label,
        active=row.active,
        metadata=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _voyage_record(row: MaritimeVoyage) -> MaritimeVoyageRecord:
    return MaritimeVoyageRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        name=row.name,
        voyage_number=row.voyage_number,
        origin=row.origin,
        destination=row.destination,
        status=_voyage_status(row.status),
        scheduled_departure_at=row.scheduled_departure_at,
        scheduled_arrival_at=row.scheduled_arrival_at,
        actual_departure_at=row.actual_departure_at,
        actual_arrival_at=row.actual_arrival_at,
        metadata=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _port_call_record(row: MaritimePortCall) -> MaritimePortCallRecord:
    return MaritimePortCallRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        voyage_id=row.voyage_id,
        port_name=row.port_name,
        un_locode=row.un_locode,
        terminal_name=row.terminal_name,
        berth=row.berth,
        status=_port_call_status(row.status),
        eta=row.eta,
        ata=row.ata,
        etd=row.etd,
        atd=row.atd,
        link_profile=row.link_profile,
        metadata=dict(row.attributes or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _ais_position_record(row: MaritimeAISPosition) -> MaritimeAISPositionRecord:
    return MaritimeAISPositionRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        source=row.source,
        received_at=row.received_at,
        reported_at=row.reported_at,
        mmsi=row.mmsi,
        latitude=row.latitude,
        longitude=row.longitude,
        speed_over_ground=row.speed_over_ground,
        course_over_ground=row.course_over_ground,
        heading=row.heading,
        navigational_status=row.navigational_status,
        raw_payload=dict(row.raw_payload or {}),
        created_at=row.created_at,
    )


def _nmea_reading_record(row: MaritimeNMEAReading) -> MaritimeNMEAReadingRecord:
    return MaritimeNMEAReadingRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        source=row.source,
        received_at=row.received_at,
        sentence_type=row.sentence_type,
        timestamp=row.timestamp,
        values=dict(row.values or {}),
        raw_sentence=row.raw_sentence,
        created_at=row.created_at,
    )


def _telemetry_event_record(
    row: MaritimeTelemetryIngestEvent,
) -> MaritimeTelemetryIngestEventRecord:
    return MaritimeTelemetryIngestEventRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        source=row.source,
        event_type=row.event_type,
        status=row.status,
        summary=row.summary,
        failure_count=row.failure_count,
        raw_payload=dict(row.raw_payload or {}),
        created_at=row.created_at,
    )


def _telemetry_event_row(
    *,
    tenant_id: UUID,
    source: str,
    event_type: str,
    status: str,
    raw_payload: Mapping[str, object],
    created_at: datetime,
    vessel_id: UUID | None = None,
    summary: str | None = None,
    failure_count: int = 0,
) -> MaritimeTelemetryIngestEvent:
    _validate_telemetry_event_status(status)
    return MaritimeTelemetryIngestEvent(
        id=uuid4(),
        tenant_id=tenant_id,
        vessel_id=vessel_id,
        source=source,
        event_type=event_type,
        status=status,
        summary=summary,
        failure_count=failure_count,
        raw_payload=_json_object(raw_payload),
        created_at=created_at,
    )


def _carrier_terminal_record(row: MaritimeCarrierTerminal) -> MaritimeCarrierTerminalRecord:
    return MaritimeCarrierTerminalRecord(
        id=row.id,
        tenant_id=row.tenant_id,
        vessel_id=row.vessel_id,
        terminal_id=row.terminal_id,
        provider=row.provider,
        status=_carrier_status(row.status),
        link_state=_carrier_link_state(row.link_state),
        downlink_mbps=row.downlink_mbps,
        uplink_mbps=row.uplink_mbps,
        latency_ms=row.latency_ms,
        packet_loss_percent=row.packet_loss_percent,
        last_seen_at=row.last_seen_at,
        raw_payload=dict(row.raw_payload or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _carrier_status(value: str) -> CarrierStatus:
    if value not in CARRIER_STATUSES:
        raise MaritimeError(f"Invalid carrier status: {value}")
    return cast(CarrierStatus, value)


def _carrier_link_state(value: str) -> CarrierLinkState:
    if value not in CARRIER_LINK_STATES:
        raise MaritimeError(f"Invalid carrier link_state: {value}")
    return cast(CarrierLinkState, value)


def _carrier_event_payload(
    reading: CarrierTerminalReading,
    *,
    previous: MaritimeCarrierTerminalRecord | None,
) -> JsonObject:
    payload = _json_object(reading.raw_payload)
    payload["terminal_id"] = reading.terminal_id
    payload["status"] = reading.status
    payload["link_state"] = reading.link_state
    if previous is not None:
        payload["previous_status"] = previous.status
        payload["previous_link_state"] = previous.link_state
    return payload
