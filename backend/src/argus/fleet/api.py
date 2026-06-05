from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, require
from argus.fleet.contracts import (
    FleetException,
    JsonObject,
    RotationGroup,
    SiteAssignment,
    SiteGroup,
    SiteHierarchy,
    SiteState,
)
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet"])

ViewerUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.VIEWER))]
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]


class SiteGroupCreate(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    kind: str = Field(min_length=1, max_length=64)
    pack_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, object] = Field(default_factory=dict)


class HierarchyNodeUpdate(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    parent_id: str | None = Field(default=None, max_length=128)
    site_id: UUID | None = None
    label: str | None = Field(default=None, max_length=160)
    kind: str = Field(min_length=1, max_length=64)
    pack_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, object] = Field(default_factory=dict)


class HierarchyReplace(BaseModel):
    nodes: list[HierarchyNodeUpdate] = Field(default_factory=list)


class RotationGroupCreate(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    member_user_ids: list[str] = Field(default_factory=list)
    pack_labels: dict[str, str] = Field(default_factory=dict)
    attributes: dict[str, object] = Field(default_factory=dict)


class SiteAssignmentCreate(BaseModel):
    site_id: UUID
    assignee_type: str = Field(min_length=1, max_length=32)
    assignee_id: str = Field(min_length=1, max_length=160)
    rotation_group_id: UUID | None = None
    pack_id: str | None = Field(default=None, max_length=128)
    attributes: dict[str, object] = Field(default_factory=dict)


@router.get("/site-groups")
async def get_site_groups(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    groups = await services.fleet.alist_site_groups(tenant_id=tenant_context.tenant_id)
    return {"items": [_site_group_payload(group) for group in groups]}


@router.post("/site-groups", status_code=status.HTTP_201_CREATED)
async def post_site_group(
    payload: SiteGroupCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    group = await services.fleet.acreate_site_group(
        tenant_id=tenant_context.tenant_id,
        label=payload.label,
        kind=payload.kind,
        pack_id=payload.pack_id,
        attributes=payload.attributes,
    )
    return _site_group_payload(group)


@router.get("/hierarchy")
async def get_hierarchy(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    return _hierarchy_payload(
        await services.fleet.aget_hierarchy(tenant_id=tenant_context.tenant_id)
    )


@router.put("/hierarchy")
async def put_hierarchy(
    payload: HierarchyReplace,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    for node in payload.nodes:
        if node.site_id is not None:
            await _ensure_tenant_site(services, tenant_context, node.site_id)
    try:
        hierarchy = await services.fleet.areplace_hierarchy(
            tenant_id=tenant_context.tenant_id,
            nodes=[node.model_dump() for node in payload.nodes],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _hierarchy_payload(hierarchy)


@router.get("/sites/{site_id}/state")
async def get_site_state(
    site_id: UUID,
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, site_id)
    state_record = await services.fleet.aget_site_state(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
    )
    if state_record is None:
        state_record = services.fleet.default_site_state(
            tenant_id=tenant_context.tenant_id,
            site_id=site_id,
        )
    return _site_state_payload(state_record)


@router.get("/exceptions")
async def get_exceptions(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    items = await services.fleet.alist_exceptions(tenant_id=tenant_context.tenant_id)
    return {"items": [_exception_payload(item) for item in items]}


@router.get("/rotation-groups")
async def get_rotation_groups(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    rotations = await services.fleet.alist_rotation_groups(tenant_id=tenant_context.tenant_id)
    return {"items": [_rotation_group_payload(rotation) for rotation in rotations]}


@router.post("/rotation-groups", status_code=status.HTTP_201_CREATED)
async def post_rotation_group(
    payload: RotationGroupCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    rotation = await services.fleet.acreate_rotation_group(
        tenant_id=tenant_context.tenant_id,
        label=payload.label,
        member_user_ids=payload.member_user_ids,
        pack_labels=payload.pack_labels,
        attributes=payload.attributes,
    )
    return _rotation_group_payload(rotation)


@router.get("/site-assignments")
async def get_site_assignments(
    current_user: ViewerUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    site_id: Annotated[UUID | None, Query()] = None,
) -> JsonObject:
    assignments = await services.fleet.alist_site_assignments(
        tenant_id=tenant_context.tenant_id,
        site_id=site_id,
    )
    return {"items": [_site_assignment_payload(assignment) for assignment in assignments]}


@router.post("/site-assignments", status_code=status.HTTP_201_CREATED)
async def post_site_assignment(
    payload: SiteAssignmentCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> JsonObject:
    await _ensure_tenant_site(services, tenant_context, payload.site_id)
    try:
        assignment = await services.fleet.acreate_site_assignment(
            tenant_id=tenant_context.tenant_id,
            site_id=payload.site_id,
            assignee_type=payload.assignee_type,
            assignee_id=payload.assignee_id,
            rotation_group_id=payload.rotation_group_id,
            pack_id=payload.pack_id,
            attributes=payload.attributes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _site_assignment_payload(assignment)


async def _ensure_tenant_site(
    services: AppServices,
    tenant_context: TenantContext,
    site_id: UUID,
) -> None:
    try:
        await services.sites.get_site(tenant_context, site_id)
    except HTTPException:
        raise


def _site_group_payload(group: SiteGroup) -> JsonObject:
    return {
        "id": str(group.id),
        "tenant_id": str(group.tenant_id),
        "label": group.label,
        "kind": group.kind,
        "pack_id": group.pack_id,
        "attributes": group.attributes,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }


def _hierarchy_payload(hierarchy: SiteHierarchy) -> JsonObject:
    return {
        "tenant_id": str(hierarchy.tenant_id),
        "nodes": [
            {
                "id": node.id,
                "tenant_id": str(node.tenant_id),
                "parent_id": node.parent_id,
                "site_id": str(node.site_id) if node.site_id is not None else None,
                "label": node.label,
                "kind": node.kind,
                "sort_order": node.sort_order,
                "pack_id": node.pack_id,
                "attributes": node.attributes,
            }
            for node in hierarchy.nodes
        ],
    }


def _site_state_payload(state_record: SiteState) -> JsonObject:
    return {
        "id": str(state_record.id),
        "tenant_id": str(state_record.tenant_id),
        "site_id": str(state_record.site_id),
        "heartbeat_status": state_record.heartbeat_status,
        "link_state": state_record.link_state,
        "runtime_status": state_record.runtime_status,
        "evidence_backlog_count": state_record.evidence_backlog_count,
        "active_incident_count": state_record.active_incident_count,
        "privacy_status": state_record.privacy_status,
        "model_artifact_status": state_record.model_artifact_status,
        "last_heartbeat_at": (
            state_record.last_heartbeat_at.isoformat()
            if state_record.last_heartbeat_at is not None
            else None
        ),
        "pack_id": state_record.pack_id,
        "attributes": state_record.attributes,
        "created_at": state_record.created_at.isoformat(),
        "updated_at": state_record.updated_at.isoformat(),
    }


def _rotation_group_payload(rotation: RotationGroup) -> JsonObject:
    return {
        "id": str(rotation.id),
        "tenant_id": str(rotation.tenant_id),
        "label": rotation.label,
        "member_user_ids": rotation.member_user_ids,
        "pack_labels": rotation.pack_labels,
        "attributes": rotation.attributes,
        "created_at": rotation.created_at.isoformat(),
        "updated_at": rotation.updated_at.isoformat(),
    }


def _site_assignment_payload(assignment: SiteAssignment) -> JsonObject:
    return {
        "id": str(assignment.id),
        "tenant_id": str(assignment.tenant_id),
        "site_id": str(assignment.site_id),
        "assignee_type": assignment.assignee_type,
        "assignee_id": assignment.assignee_id,
        "rotation_group_id": (
            str(assignment.rotation_group_id)
            if assignment.rotation_group_id is not None
            else None
        ),
        "pack_id": assignment.pack_id,
        "attributes": assignment.attributes,
        "created_at": assignment.created_at.isoformat(),
        "updated_at": assignment.updated_at.isoformat(),
    }


def _exception_payload(item: FleetException) -> JsonObject:
    return {
        "id": item.id,
        "tenant_id": str(item.tenant_id) if item.tenant_id is not None else None,
        "site_id": str(item.site_id) if item.site_id is not None else None,
        "kind": item.kind,
        "attention_rank": item.attention_rank,
        "count": item.count,
        "pack_id": item.pack_id,
        "attributes": item.attributes,
    }
