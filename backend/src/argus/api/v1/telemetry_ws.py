from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_websocket_services, get_websocket_tenant_context
from argus.services.app import AppServices

router = APIRouter(tags=["telemetry"])
TenantDependency = Annotated[TenantContext, Depends(get_websocket_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_websocket_services)]


@router.websocket("/ws/telemetry")
async def telemetry_websocket(
    websocket: WebSocket,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> None:
    await websocket.accept()
    subscription = await services.telemetry.subscribe(tenant_context)
    try:
        while True:
            payload = await subscription.receive()
            await websocket.send_json(payload.model_dump(mode="json"))
    except WebSocketDisconnect:
        return
    finally:
        await subscription.close()
