from __future__ import annotations

from typing import Any

import httpx


class InstallerHttpError(RuntimeError):
    pass


class InstallerHttpClient:
    def __init__(self, api_url: str, *, timeout_seconds: float = 10.0) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def bootstrap_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/v1/deployment/bootstrap/status")

    def rotate_local_bootstrap_token(self) -> dict[str, Any]:
        return self._request("POST", "/api/v1/deployment/bootstrap/rotate-local-token")

    def claim_pairing_session(
        self,
        *,
        session_id: str,
        pairing_code: str,
        supervisor_id: str,
        hostname: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/v1/deployment/pairing-sessions/{session_id}/claim",
            json={
                "pairing_code": pairing_code,
                "supervisor_id": supervisor_id,
                "hostname": hostname,
            },
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_url}{path}"
        try:
            response = httpx.request(
                method,
                url,
                json=json,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = _response_detail(exc.response)
            msg = f"{method} {path} failed with {exc.response.status_code}: {detail}"
            raise InstallerHttpError(msg) from exc
        except httpx.HTTPError as exc:
            msg = f"{method} {path} failed: {exc}"
            raise InstallerHttpError(msg) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            msg = f"{method} {path} returned a non-object response."
            raise InstallerHttpError(msg)
        return payload


def _response_detail(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"]
    return response.text
