from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from argus.compat import UTC
from argus.maritime.contracts import (
    JsonObject,
    MaritimePortCallRecord,
    MaritimeRuntimeContribution,
    MaritimeVesselRecord,
    MaritimeVoyageRecord,
    PortCallStatus,
    VoyageStatus,
)
from argus.maritime.tables import MaritimePortCall, MaritimeVessel, MaritimeVoyage
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
