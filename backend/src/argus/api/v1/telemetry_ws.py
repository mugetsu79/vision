from __future__ import annotations

import asyncio
from typing import Annotated, Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from argus.api.contracts import TenantContext
from argus.api.dependencies import get_websocket_services, get_websocket_tenant_context
from argus.core.metrics import WEBSOCKET_CONNECTIONS, WEBSOCKET_DISCONNECTS_TOTAL
from argus.services.app import AppServices

router = APIRouter(tags=["telemetry"])
TenantDependency = Annotated[TenantContext, Depends(get_websocket_tenant_context)]
ServicesDependency = Annotated[AppServices, Depends(get_websocket_services)]


async def _receive_telemetry_or_disconnect(
    websocket: WebSocket,
    subscription: Any,
    disconnect_task: asyncio.Task[Any] | None = None,
) -> Any:
    telemetry_task = asyncio.create_task(subscription.receive())
    owns_disconnect_task = disconnect_task is None
    disconnect_task = disconnect_task or asyncio.create_task(websocket.receive())
    try:
        while True:
            done, _pending = await asyncio.wait(
                {telemetry_task, disconnect_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if disconnect_task in done:
                message = disconnect_task.result()
                if message.get("type") == "websocket.disconnect" or not owns_disconnect_task:
                    raise WebSocketDisconnect
                disconnect_task = asyncio.create_task(websocket.receive())
                continue

            return telemetry_task.result()
    finally:
        if not telemetry_task.done():
            telemetry_task.cancel()
            await asyncio.gather(telemetry_task, return_exceptions=True)
        if owns_disconnect_task and not disconnect_task.done():
            disconnect_task.cancel()
            await asyncio.gather(disconnect_task, return_exceptions=True)


@router.websocket("/ws/telemetry")
async def telemetry_websocket(
    websocket: WebSocket,
    tenant_context: TenantDependency,
    services: ServicesDependency,
) -> None:
    tenant_label = str(tenant_context.tenant_id)
    await websocket.accept()
    WEBSOCKET_CONNECTIONS.labels(tenant=tenant_label).inc()
    subscription = await services.telemetry.subscribe(tenant_context)
    disconnect_task = asyncio.create_task(websocket.receive())
    try:
        while True:
            payload = await _receive_telemetry_or_disconnect(
                websocket,
                subscription,
                disconnect_task,
            )
            await websocket.send_json(payload.model_dump(mode="json"))
    except WebSocketDisconnect:
        WEBSOCKET_DISCONNECTS_TOTAL.labels(tenant=tenant_label).inc()
        return
    except asyncio.CancelledError:
        return
    finally:
        if not disconnect_task.done():
            disconnect_task.cancel()
            await asyncio.gather(disconnect_task, return_exceptions=True)
        WEBSOCKET_CONNECTIONS.labels(tenant=tenant_label).dec()
        await subscription.close()
