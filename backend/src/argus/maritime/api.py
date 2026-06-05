from __future__ import annotations

from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from argus.api.contracts import SiteCreate, SiteResponse, TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.maritime.contracts import (
    JsonObject,
    MaritimePortCallRecord,
    MaritimeVesselRecord,
    MaritimeVoyageRecord,
)
from argus.maritime.service import (
    MaritimeConflictError,
    MaritimeError,
    MaritimeNotFoundError,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(tags=["maritime"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
OperatorUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.OPERATOR))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class VesselCreate(BaseModel):
    site_id: UUID | None = None
    create_site: SiteCreate | None = None
    name: str = Field(min_length=1, max_length=255)
    imo_number: str | None = Field(default=None, min_length=1, max_length=16)
    mmsi: str | None = Field(default=None, min_length=1, max_length=16)
    call_sign: str | None = Field(default=None, min_length=1, max_length=32)
    flag_state: str | None = Field(default=None, min_length=1, max_length=64)
    vessel_type: str | None = Field(default=None, min_length=1, max_length=80)
    owner_label: str | None = Field(default=None, min_length=1, max_length=160)
    manager_label: str | None = Field(default=None, min_length=1, max_length=160)
    charterer_label: str | None = Field(default=None, min_length=1, max_length=160)
    metadata: JsonObject = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_one_site_binding(self) -> VesselCreate:
        if self.site_id is None and self.create_site is None:
            raise ValueError("Provide site_id or create_site.")
        if self.site_id is not None and self.create_site is not None:
            raise ValueError("Provide either site_id or create_site, not both.")
        return self


class VesselUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    active: bool | None = None
    metadata: JsonObject | None = None


class VoyageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    voyage_number: str | None = Field(default=None, min_length=1, max_length=80)
    origin: str | None = Field(default=None, min_length=1, max_length=160)
    destination: str | None = Field(default=None, min_length=1, max_length=160)
    scheduled_departure_at: datetime | None = None
    scheduled_arrival_at: datetime | None = None
    metadata: JsonObject = Field(default_factory=dict)


class VoyageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    voyage_number: str | None = Field(default=None, min_length=1, max_length=80)
    origin: str | None = Field(default=None, min_length=1, max_length=160)
    destination: str | None = Field(default=None, min_length=1, max_length=160)
    scheduled_departure_at: datetime | None = None
    scheduled_arrival_at: datetime | None = None
    metadata: JsonObject | None = None


class PortCallCreate(BaseModel):
    port_name: str = Field(min_length=1, max_length=255)
    un_locode: str | None = Field(default=None, min_length=1, max_length=16)
    terminal_name: str | None = Field(default=None, min_length=1, max_length=160)
    berth: str | None = Field(default=None, min_length=1, max_length=160)
    eta: datetime | None = None
    etd: datetime | None = None
    link_profile: str | None = Field(default=None, min_length=1, max_length=80)
    metadata: JsonObject = Field(default_factory=dict)


class PortCallUpdate(BaseModel):
    port_name: str | None = Field(default=None, min_length=1, max_length=255)
    un_locode: str | None = Field(default=None, min_length=1, max_length=16)
    terminal_name: str | None = Field(default=None, min_length=1, max_length=160)
    berth: str | None = Field(default=None, min_length=1, max_length=160)
    eta: datetime | None = None
    etd: datetime | None = None
    link_profile: str | None = Field(default=None, min_length=1, max_length=80)
    metadata: JsonObject | None = None


@router.get("/api/v1/maritime/runtime")
async def get_maritime_runtime(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> JsonObject:
    return _runtime_payload(services)


@router.get("/api/v1/packs/maritime-fleet/runtime")
async def get_maritime_pack_runtime(
    current_user: ViewerUser,
    services: ServicesDependency,
) -> JsonObject:
    return _runtime_payload(services)


@router.get("/api/v1/maritime/vessels")
async def list_maritime_vessels(
    current_user: ViewerUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> list[JsonObject]:
    vessels = await services.maritime.alist_vessels(tenant_id=tenant_context.tenant_id)
    return [
        _vessel_payload(vessel, await _lookup_site(services, tenant_context, vessel.site_id))
        for vessel in vessels
    ]


@router.post("/api/v1/maritime/vessels", status_code=status.HTTP_201_CREATED)
async def create_maritime_vessel(
    payload: VesselCreate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        await services.maritime.aensure_vessel_identifiers_available(
            tenant_id=tenant_context.tenant_id,
            imo_number=payload.imo_number,
            mmsi=payload.mmsi,
            call_sign=payload.call_sign,
        )
        site = await _resolve_vessel_site(payload, services, tenant_context)
        try:
            vessel = await services.maritime.acreate_vessel(
                tenant_id=tenant_context.tenant_id,
                site_id=site.id,
                name=payload.name,
                imo_number=payload.imo_number,
                mmsi=payload.mmsi,
                call_sign=payload.call_sign,
                flag_state=payload.flag_state,
                vessel_type=payload.vessel_type,
                owner_label=payload.owner_label,
                manager_label=payload.manager_label,
                charterer_label=payload.charterer_label,
                metadata=payload.metadata,
            )
        except MaritimeConflictError:
            if payload.create_site is not None:
                await services.sites.delete_site(tenant_context, site.id)
            raise
        return _vessel_payload(vessel, site)
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.get("/api/v1/maritime/vessels/{vessel_id}")
async def get_maritime_vessel(
    vessel_id: UUID,
    current_user: ViewerUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        vessel = await services.maritime.aget_vessel(
            tenant_id=tenant_context.tenant_id,
            vessel_id=vessel_id,
        )
        return _vessel_payload(
            vessel,
            await _lookup_site(services, tenant_context, vessel.site_id),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.patch("/api/v1/maritime/vessels/{vessel_id}")
async def update_maritime_vessel(
    vessel_id: UUID,
    payload: VesselUpdate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        vessel = await services.maritime.aupdate_vessel(
            tenant_id=tenant_context.tenant_id,
            vessel_id=vessel_id,
            name=payload.name,
            active=payload.active,
            metadata=payload.metadata,
        )
        return _vessel_payload(
            vessel,
            await _lookup_site(services, tenant_context, vessel.site_id),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.delete("/api/v1/maritime/vessels/{vessel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_maritime_vessel(
    vessel_id: UUID,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> None:
    try:
        await services.maritime.adeactivate_vessel(
            tenant_id=tenant_context.tenant_id,
            vessel_id=vessel_id,
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.get("/api/v1/maritime/vessels/{vessel_id}/voyages")
async def list_maritime_voyages(
    vessel_id: UUID,
    current_user: ViewerUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> list[JsonObject]:
    try:
        voyages = await services.maritime.alist_voyages(
            tenant_id=tenant_context.tenant_id,
            vessel_id=vessel_id,
        )
        return [_voyage_payload(voyage) for voyage in voyages]
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post(
    "/api/v1/maritime/vessels/{vessel_id}/voyages",
    status_code=status.HTTP_201_CREATED,
)
async def create_maritime_voyage(
    vessel_id: UUID,
    payload: VoyageCreate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        voyage = await services.maritime.acreate_voyage(
            tenant_id=tenant_context.tenant_id,
            vessel_id=vessel_id,
            name=payload.name,
            voyage_number=payload.voyage_number,
            origin=payload.origin,
            destination=payload.destination,
            scheduled_departure_at=payload.scheduled_departure_at,
            scheduled_arrival_at=payload.scheduled_arrival_at,
            metadata=payload.metadata,
        )
        return _voyage_payload(voyage)
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.get("/api/v1/maritime/voyages/{voyage_id}")
async def get_maritime_voyage(
    voyage_id: UUID,
    current_user: ViewerUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _voyage_payload(
            await services.maritime.aget_voyage(
                tenant_id=tenant_context.tenant_id,
                voyage_id=voyage_id,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.patch("/api/v1/maritime/voyages/{voyage_id}")
async def update_maritime_voyage(
    voyage_id: UUID,
    payload: VoyageUpdate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _voyage_payload(
            await services.maritime.aupdate_voyage(
                tenant_id=tenant_context.tenant_id,
                voyage_id=voyage_id,
                name=payload.name,
                voyage_number=payload.voyage_number,
                origin=payload.origin,
                destination=payload.destination,
                scheduled_departure_at=payload.scheduled_departure_at,
                scheduled_arrival_at=payload.scheduled_arrival_at,
                metadata=payload.metadata,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post("/api/v1/maritime/voyages/{voyage_id}/activate")
async def activate_maritime_voyage(
    voyage_id: UUID,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _voyage_payload(
            await services.maritime.aactivate_voyage(
                tenant_id=tenant_context.tenant_id,
                voyage_id=voyage_id,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post("/api/v1/maritime/voyages/{voyage_id}/complete")
async def complete_maritime_voyage(
    voyage_id: UUID,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _voyage_payload(
            await services.maritime.acomplete_voyage(
                tenant_id=tenant_context.tenant_id,
                voyage_id=voyage_id,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.get("/api/v1/maritime/voyages/{voyage_id}/port-calls")
async def list_maritime_port_calls(
    voyage_id: UUID,
    current_user: ViewerUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> list[JsonObject]:
    try:
        port_calls = await services.maritime.alist_port_calls(
            tenant_id=tenant_context.tenant_id,
            voyage_id=voyage_id,
        )
        return [_port_call_payload(port_call) for port_call in port_calls]
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post(
    "/api/v1/maritime/voyages/{voyage_id}/port-calls",
    status_code=status.HTTP_201_CREATED,
)
async def create_maritime_port_call(
    voyage_id: UUID,
    payload: PortCallCreate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        port_call = await services.maritime.acreate_port_call(
            tenant_id=tenant_context.tenant_id,
            voyage_id=voyage_id,
            port_name=payload.port_name,
            un_locode=payload.un_locode,
            terminal_name=payload.terminal_name,
            berth=payload.berth,
            eta=payload.eta,
            etd=payload.etd,
            link_profile=payload.link_profile,
            metadata=payload.metadata,
        )
        return _port_call_payload(port_call)
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.patch("/api/v1/maritime/port-calls/{port_call_id}")
async def update_maritime_port_call(
    port_call_id: UUID,
    payload: PortCallUpdate,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _port_call_payload(
            await services.maritime.aupdate_port_call(
                tenant_id=tenant_context.tenant_id,
                port_call_id=port_call_id,
                port_name=payload.port_name,
                un_locode=payload.un_locode,
                terminal_name=payload.terminal_name,
                berth=payload.berth,
                eta=payload.eta,
                etd=payload.etd,
                link_profile=payload.link_profile,
                metadata=payload.metadata,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post("/api/v1/maritime/port-calls/{port_call_id}/arrive")
async def arrive_maritime_port_call(
    port_call_id: UUID,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _port_call_payload(
            await services.maritime.aarrive_port_call(
                tenant_id=tenant_context.tenant_id,
                port_call_id=port_call_id,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


@router.post("/api/v1/maritime/port-calls/{port_call_id}/depart")
async def depart_maritime_port_call(
    port_call_id: UUID,
    current_user: OperatorUser,
    services: ServicesDependency,
    tenant_context: TenantDependency,
) -> JsonObject:
    try:
        return _port_call_payload(
            await services.maritime.adepart_port_call(
                tenant_id=tenant_context.tenant_id,
                port_call_id=port_call_id,
            ),
        )
    except MaritimeError as exc:
        _raise_maritime_http_error(exc)


def _runtime_payload(services: AppServices) -> JsonObject:
    try:
        return services.maritime.runtime_payload()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


async def _resolve_vessel_site(
    payload: VesselCreate,
    services: AppServices,
    tenant_context: TenantContext,
) -> SiteResponse:
    if payload.create_site is not None:
        return await services.sites.create_site(tenant_context, payload.create_site)
    if payload.site_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide site_id or create_site.",
        )
    return await services.sites.get_site(tenant_context, payload.site_id)


async def _lookup_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
) -> SiteResponse | None:
    try:
        return await services.sites.get_site(tenant_context, site_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            return None
        raise


def _vessel_payload(
    vessel: MaritimeVesselRecord,
    site: SiteResponse | None,
) -> JsonObject:
    payload: JsonObject = {
        "id": str(vessel.id),
        "tenant_id": str(vessel.tenant_id),
        "site_id": str(vessel.site_id),
        "name": vessel.name,
        "imo_number": vessel.imo_number,
        "mmsi": vessel.mmsi,
        "call_sign": vessel.call_sign,
        "flag_state": vessel.flag_state,
        "vessel_type": vessel.vessel_type,
        "owner_label": vessel.owner_label,
        "manager_label": vessel.manager_label,
        "charterer_label": vessel.charterer_label,
        "active": vessel.active,
        "metadata": vessel.metadata,
        "created_at": vessel.created_at.isoformat(),
        "updated_at": vessel.updated_at.isoformat(),
    }
    if site is not None:
        payload["site"] = site.model_dump(mode="json")
    return payload


def _voyage_payload(voyage: MaritimeVoyageRecord) -> JsonObject:
    return {
        "id": str(voyage.id),
        "tenant_id": str(voyage.tenant_id),
        "vessel_id": str(voyage.vessel_id),
        "name": voyage.name,
        "voyage_number": voyage.voyage_number,
        "origin": voyage.origin,
        "destination": voyage.destination,
        "status": voyage.status,
        "scheduled_departure_at": _iso(voyage.scheduled_departure_at),
        "scheduled_arrival_at": _iso(voyage.scheduled_arrival_at),
        "actual_departure_at": _iso(voyage.actual_departure_at),
        "actual_arrival_at": _iso(voyage.actual_arrival_at),
        "metadata": voyage.metadata,
        "created_at": voyage.created_at.isoformat(),
        "updated_at": voyage.updated_at.isoformat(),
    }


def _port_call_payload(port_call: MaritimePortCallRecord) -> JsonObject:
    return {
        "id": str(port_call.id),
        "tenant_id": str(port_call.tenant_id),
        "vessel_id": str(port_call.vessel_id),
        "voyage_id": str(port_call.voyage_id),
        "port_name": port_call.port_name,
        "un_locode": port_call.un_locode,
        "terminal_name": port_call.terminal_name,
        "berth": port_call.berth,
        "status": port_call.status,
        "eta": _iso(port_call.eta),
        "ata": _iso(port_call.ata),
        "etd": _iso(port_call.etd),
        "atd": _iso(port_call.atd),
        "link_profile": port_call.link_profile,
        "metadata": port_call.metadata,
        "created_at": port_call.created_at.isoformat(),
        "updated_at": port_call.updated_at.isoformat(),
    }


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _raise_maritime_http_error(exc: MaritimeError) -> NoReturn:
    if isinstance(exc, MaritimeNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, MaritimeConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
