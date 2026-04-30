from __future__ import annotations

import asyncio

import pytest
from fastapi import WebSocketDisconnect

from argus.api.v1.telemetry_ws import _receive_telemetry_or_disconnect


class BlockingTelemetrySubscription:
    def __init__(self) -> None:
        self.cancelled = False

    async def receive(self) -> object:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise


class DisconnectingWebSocket:
    async def receive(self) -> dict[str, str]:
        return {"type": "websocket.disconnect"}


@pytest.mark.asyncio
async def test_receive_telemetry_or_disconnect_exits_on_client_disconnect() -> None:
    subscription = BlockingTelemetrySubscription()

    with pytest.raises(WebSocketDisconnect):
        await _receive_telemetry_or_disconnect(DisconnectingWebSocket(), subscription)

    assert subscription.cancelled is True
