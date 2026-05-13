from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from argus.api.contracts import (
    EdgeNodeHardwareReportCreate,
    EdgeNodeHardwareReportResponse,
    FleetBootstrapRequest,
    FleetBootstrapResponse,
    FleetOverviewResponse,
    LifecycleRequestClaim,
    LifecycleRequestCompletion,
    OperationalMemoryPatternResponse,
    OperationsLifecycleRequestCreate,
    OperationsLifecycleRequestResponse,
    SupervisorPollRequest,
    SupervisorPollResponse,
    SupervisorRuntimeReportCreate,
    SupervisorRuntimeReportResponse,
    TenantContext,
    WorkerAssignmentCreate,
    WorkerAssignmentResponse,
    WorkerModelAdmissionRequest,
    WorkerModelAdmissionResponse,
)
from argus.api.dependencies import get_app_services, get_tenant_context
from argus.core.security import AuthenticatedUser, enforce_role, require
from argus.models.enums import RoleEnum
from argus.services.app import AppServices

router = APIRouter(prefix="/api/v1/operations", tags=["operations"])
AdminUser = Annotated[AuthenticatedUser, Depends(require(RoleEnum.ADMIN))]
TenantDependency = Annotated[TenantContext, Depends(get_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_app_services)]


async def get_supervisor_or_admin_tenant_context(
    request: Request,
    services: ServicesDependency,
    x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    supervisor_id: str | None = None,
) -> TenantContext:
    token = _bearer_token(request.headers.get("Authorization"))
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    try:
        user = await request.app.state.security.authenticate_request(request)
    except HTTPException as exc:
        if exc.status_code != status.HTTP_401_UNAUTHORIZED:
            raise
    else:
        enforce_role(user, RoleEnum.ADMIN)
        return await services.tenancy.resolve_context(
            user=user,
            explicit_tenant_id=_parse_optional_uuid(x_tenant_id),
        )

    try:
        return await services.deployment.authenticate_supervisor_credential(
            credential_material=token,
            supervisor_id=supervisor_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid supervisor credential.",
        ) from exc


SupervisorOrAdminTenantDependency = Annotated[
    TenantContext,
    Depends(get_supervisor_or_admin_tenant_context),
]


@router.get("/fleet", response_model=FleetOverviewResponse)
async def get_fleet_overview(
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> FleetOverviewResponse:
    return await services.operations.get_fleet_overview(tenant_context)


@router.get("/memory-patterns", response_model=list[OperationalMemoryPatternResponse])
async def list_operational_memory_patterns(
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
    incident_id: UUID | None = None,
    camera_id: UUID | None = None,
    site_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[OperationalMemoryPatternResponse]:
    return await services.operations.list_memory_patterns(
        tenant_context,
        incident_id=incident_id,
        camera_id=camera_id,
        site_id=site_id,
        limit=limit,
    )


@router.post(
    "/bootstrap",
    response_model=FleetBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bootstrap_material(
    payload: FleetBootstrapRequest,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> FleetBootstrapResponse:
    return await services.operations.create_bootstrap_material(tenant_context, payload)


@router.post(
    "/worker-assignments",
    response_model=WorkerAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_worker_assignment(
    payload: WorkerAssignmentCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> WorkerAssignmentResponse:
    return await services.operations.create_worker_assignment(tenant_context, payload)


@router.post(
    "/runtime-reports",
    response_model=SupervisorRuntimeReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_worker_runtime_report(
    payload: SupervisorRuntimeReportCreate,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> SupervisorRuntimeReportResponse:
    return await services.operations.record_worker_runtime_report(
        tenant_context,
        payload,
    )


@router.post(
    "/lifecycle-requests",
    response_model=OperationsLifecycleRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lifecycle_request(
    payload: OperationsLifecycleRequestCreate,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> OperationsLifecycleRequestResponse:
    return await services.operations.create_lifecycle_request(tenant_context, payload)


@router.post(
    "/supervisors/{supervisor_id}/poll",
    response_model=SupervisorPollResponse,
)
async def poll_supervisor_lifecycle_requests(
    supervisor_id: str,
    payload: SupervisorPollRequest,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> SupervisorPollResponse:
    return await services.operations.poll_supervisor_lifecycle_requests(
        tenant_context,
        supervisor_id,
        payload,
    )


@router.post(
    "/lifecycle-requests/{request_id}/claim",
    response_model=OperationsLifecycleRequestResponse,
)
async def claim_lifecycle_request(
    request_id: UUID,
    payload: LifecycleRequestClaim,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> OperationsLifecycleRequestResponse:
    _assert_supervisor_identity(tenant_context, payload.supervisor_id)
    return await services.operations.claim_lifecycle_request(
        tenant_context,
        request_id,
        payload,
    )


@router.post(
    "/lifecycle-requests/{request_id}/complete",
    response_model=OperationsLifecycleRequestResponse,
)
async def complete_lifecycle_request(
    request_id: UUID,
    payload: LifecycleRequestCompletion,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> OperationsLifecycleRequestResponse:
    _assert_supervisor_identity(tenant_context, payload.supervisor_id)
    return await services.operations.complete_lifecycle_request(
        tenant_context,
        request_id,
        payload,
    )


@router.post(
    "/supervisors/{supervisor_id}/hardware-reports",
    response_model=EdgeNodeHardwareReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_hardware_report(
    supervisor_id: str,
    payload: EdgeNodeHardwareReportCreate,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> EdgeNodeHardwareReportResponse:
    return await services.operations.record_hardware_report(
        tenant_context,
        supervisor_id,
        payload,
    )


@router.get(
    "/supervisors/{supervisor_id}/hardware-reports/latest",
    response_model=EdgeNodeHardwareReportResponse | None,
)
async def get_latest_supervisor_hardware_report(
    supervisor_id: str,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> EdgeNodeHardwareReportResponse | None:
    return await services.operations.latest_hardware_report_for_supervisor(
        tenant_context,
        supervisor_id,
    )


@router.get(
    "/edge-nodes/{edge_node_id}/hardware-reports/latest",
    response_model=EdgeNodeHardwareReportResponse | None,
)
async def get_latest_edge_hardware_report(
    edge_node_id: UUID,
    current_user: AdminUser,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> EdgeNodeHardwareReportResponse | None:
    return await services.operations.latest_hardware_report_for_edge_node(
        tenant_context,
        edge_node_id,
    )


@router.post(
    "/workers/{camera_id}/model-admission/evaluate",
    response_model=WorkerModelAdmissionResponse,
)
async def evaluate_worker_model_admission(
    camera_id: UUID,
    payload: WorkerModelAdmissionRequest,
    tenant_context: SupervisorOrAdminTenantDependency,
    services: ServicesDependency,
) -> WorkerModelAdmissionResponse:
    return await services.operations.evaluate_worker_model_admission(
        tenant_context,
        camera_id,
        payload,
    )


def _bearer_token(authorization_header: str | None) -> str | None:
    if authorization_header is None:
        return None
    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _parse_optional_uuid(raw_value: str | None) -> UUID | None:
    if raw_value is None:
        return None
    try:
        return UUID(raw_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-ID must be a UUID.",
        ) from exc


def _assert_supervisor_identity(tenant_context: TenantContext, supervisor_id: str) -> None:
    if tenant_context.user.claims.get("auth_type") != "supervisor_node_credential":
        return
    if tenant_context.user.subject != f"supervisor:{supervisor_id}":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor credential cannot act for another supervisor.",
        )
