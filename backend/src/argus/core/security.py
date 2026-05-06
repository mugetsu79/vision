from __future__ import annotations

import base64
import hashlib
import hmac
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from fnmatch import fnmatch
from typing import Annotated, Any

import httpx
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from jose import jwt  # type: ignore[import-untyped]
from jose.exceptions import JOSEError, JWTError  # type: ignore[import-untyped]
from pydantic import BaseModel
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from argus.compat import UTC
from argus.core.config import Settings
from argus.models.enums import RoleEnum
from argus.models.tables import APIKey

ROLE_RANK = {
    RoleEnum.VIEWER: 10,
    RoleEnum.OPERATOR: 20,
    RoleEnum.ADMIN: 30,
    RoleEnum.SUPERADMIN: 40,
}


class AuthenticatedUser(BaseModel):
    subject: str
    email: str | None = None
    role: RoleEnum
    issuer: str
    realm: str
    is_superadmin: bool
    tenant_context: str | None = None
    claims: dict[str, Any]


@dataclass(slots=True)
class _CachedValue:
    value: dict[str, Any]
    expires_at: datetime


class JwksCache:
    def __init__(self, settings: Settings, http_client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.http_client = http_client
        self._discovery_cache: dict[str, _CachedValue] = {}
        self._jwks_cache: dict[str, _CachedValue] = {}

    async def get_discovery_document(self, issuer: str) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        cached = self._discovery_cache.get(issuer)
        if cached is not None and cached.expires_at > now:
            return cached.value

        response = await self.http_client.get(f"{issuer}/.well-known/openid-configuration")
        response.raise_for_status()
        payload = dict(response.json())
        self._discovery_cache[issuer] = _CachedValue(
            value=payload,
            expires_at=now + timedelta(seconds=self.settings.keycloak_jwks_cache_ttl_seconds),
        )
        return payload

    async def get_jwks(self, issuer: str) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        cached = self._jwks_cache.get(issuer)
        if cached is not None and cached.expires_at > now:
            return cached.value

        discovery_document = await self.get_discovery_document(issuer)
        response = await self.http_client.get(str(discovery_document["jwks_uri"]))
        response.raise_for_status()
        payload = dict(response.json())
        self._jwks_cache[issuer] = _CachedValue(
            value=payload,
            expires_at=now + timedelta(seconds=self.settings.keycloak_jwks_cache_ttl_seconds),
        )
        return payload


class SecurityService:
    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient,
        owns_http_client: bool = False,
    ) -> None:
        self.settings = settings
        self.http_client = http_client
        self.owns_http_client = owns_http_client
        self.jwks_cache = JwksCache(settings, http_client)

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        transport: httpx.AsyncBaseTransport
        | Callable[[httpx.Request], httpx.Response]
        | None = None,
    ) -> SecurityService:
        if callable(transport):
            transport = httpx.MockTransport(transport)
        http_client = httpx.AsyncClient(transport=transport, timeout=5.0)
        return cls(settings, http_client=http_client, owns_http_client=True)

    async def close(self) -> None:
        if self.owns_http_client:
            await self.http_client.aclose()

    async def authenticate_request(self, request: Request) -> AuthenticatedUser:
        token = _extract_bearer_token(request.headers.get("Authorization"))
        if token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token.",
            )

        return await self.validate_token(token)

    async def validate_token(self, token: str) -> AuthenticatedUser:
        try:
            unverified_header = jwt.get_unverified_header(token)
            unverified_claims = jwt.get_unverified_claims(token)
        except JWTError as exc:  # pragma: no cover - defensive branch
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token.",
            ) from exc

        issuer = str(unverified_claims.get("iss", ""))
        if not self._is_trusted_issuer(issuer):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token issuer is not trusted.",
            )

        jwks = await self.jwks_cache.get_jwks(self._resolve_internal_issuer(issuer))
        key_id = unverified_header.get("kid")
        matching_key = next(
            (candidate for candidate in jwks.get("keys", []) if candidate.get("kid") == key_id),
            None,
        )
        if matching_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to resolve signing key.",
            )

        try:
            claims = jwt.decode(
                token,
                matching_key,
                algorithms=[matching_key.get("alg", "RS256")],
                issuer=issuer,
                options={"verify_aud": False},
            )
        except JOSEError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token verification failed.",
            ) from exc

        roles = self._extract_roles(claims)
        if not roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token does not include a recognized role.",
            )

        role = max(roles, key=lambda candidate: ROLE_RANK[candidate])
        realm = issuer.rstrip("/").rsplit("/", 1)[-1]
        is_superadmin = (
            realm == self.settings.keycloak_platform_realm
            and role == RoleEnum.SUPERADMIN
        )

        return AuthenticatedUser(
            subject=str(claims["sub"]),
            email=claims.get("email"),
            role=role,
            issuer=issuer,
            realm=realm,
            is_superadmin=is_superadmin,
            tenant_context=claims.get("tenant_id") or claims.get("tenant"),
            claims=claims,
        )

    def validate_edge_key(self, supplied_key: str | None, path: str) -> bool:
        if not supplied_key:
            return False

        for configured_key, scopes in self.settings.edge_api_keys.items():
            if not hmac.compare_digest(configured_key, supplied_key):
                continue

            if any(fnmatch(path, scope) for scope in scopes):
                return True

        return False

    def _extract_roles(self, claims: dict[str, Any]) -> list[RoleEnum]:
        raw_roles = list(claims.get("realm_access", {}).get("roles", []))
        raw_roles.extend(claims.get("roles", []))

        resolved_roles: list[RoleEnum] = []
        for role_name in raw_roles:
            try:
                resolved_roles.append(RoleEnum(role_name))
            except ValueError:
                continue
        return resolved_roles

    def _is_trusted_issuer(self, issuer: str) -> bool:
        return any(
            issuer.startswith(f"{realms_base_url}/")
            for realms_base_url in self.settings.keycloak_trusted_realms_base_urls
        )

    def _resolve_internal_issuer(self, issuer: str) -> str:
        realm = issuer.rstrip("/").rsplit("/", 1)[-1]
        return f"{self.settings.keycloak_realms_base_url}/{realm}"


async def get_current_user(request: Request) -> AuthenticatedUser:
    security_service: SecurityService = request.app.state.security
    return await security_service.authenticate_request(request)


CurrentUserDependency = Annotated[AuthenticatedUser, Depends(get_current_user)]


async def get_current_media_user(request: Request) -> AuthenticatedUser:
    security_service: SecurityService = request.app.state.security
    token = _extract_bearer_token(request.headers.get("Authorization"))
    if token is None:
        token = request.query_params.get("access_token")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )
    return await security_service.validate_token(token)


CurrentMediaUserDependency = Annotated[AuthenticatedUser, Depends(get_current_media_user)]


async def get_current_websocket_user(websocket: WebSocket) -> AuthenticatedUser:
    security_service: SecurityService = websocket.app.state.security
    authorization_header = websocket.headers.get("Authorization")
    token = None
    if authorization_header and authorization_header.startswith("Bearer "):
        token = authorization_header.removeprefix("Bearer ").strip()
    if token is None:
        token = websocket.query_params.get("access_token")
    if token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    try:
        return await security_service.validate_token(token)
    except HTTPException as exc:  # pragma: no cover - websocket-only branch
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from exc


def require(required_role: RoleEnum) -> Callable[[AuthenticatedUser], Any]:
    async def dependency(
        current_user: CurrentUserDependency,
    ) -> AuthenticatedUser:
        return enforce_role(current_user, required_role)

    return dependency


def enforce_role(current_user: AuthenticatedUser, required_role: RoleEnum) -> AuthenticatedUser:
    if ROLE_RANK[current_user.role] < ROLE_RANK[required_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role.",
        )
    return current_user


class EdgeKeyMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: Any,
        security_service: SecurityService | None = None,
    ) -> None:
        super().__init__(app)
        self.security_service = security_service

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> JSONResponse | Any:
        if not _requires_edge_key(request.url.path):
            return await call_next(request)

        security_service = self.security_service or request.app.state.security
        supplied_key = request.headers.get("X-Edge-Key")
        if supplied_key is None:
            authorization_header = request.headers.get("Authorization")
            supplied_key = _extract_edge_key_from_authorization(authorization_header)

        if not await _validate_edge_key_request(request, security_service, supplied_key):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing edge API key."},
            )

        return await call_next(request)


def encrypt_rtsp_url(plaintext: str, settings: Settings) -> str:
    key = _derive_encryption_key(settings.rtsp_encryption_key.get_secret_value())
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_rtsp_url(ciphertext: str, settings: Settings) -> str:
    key = _derive_encryption_key(settings.rtsp_encryption_key.get_secret_value())
    decoded = base64.urlsafe_b64decode(ciphertext.encode("utf-8"))
    nonce = decoded[:12]
    encrypted_payload = decoded[12:]
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, encrypted_payload, None)
    except (InvalidTag, ValueError, TypeError) as exc:
        raise ValueError("Unable to decrypt RTSP URL.") from exc

    return plaintext.decode("utf-8")


def _derive_encryption_key(secret: str) -> bytes:
    try:
        decoded = base64.urlsafe_b64decode(secret.encode("utf-8"))
    except Exception:  # pragma: no cover - best effort path
        decoded = b""

    if len(decoded) in {16, 24, 32}:
        return decoded

    return hashlib.sha256(secret.encode("utf-8")).digest()


def _extract_edge_key_from_authorization(header_value: str | None) -> str | None:
    if header_value is None or not header_value.startswith("EdgeKey "):
        return None
    return header_value.removeprefix("EdgeKey ").strip()


def _extract_bearer_token(header_value: str | None) -> str | None:
    if header_value is None or not header_value.startswith("Bearer "):
        return None
    return header_value.removeprefix("Bearer ").strip()


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _requires_edge_key(path: str) -> bool:
    return path in {
        "/api/v1/edge/telemetry",
        "/api/v1/edge/heartbeat",
        "/api/v1/edge/ping",
    }


async def _validate_edge_key_request(
    request: Request,
    security_service: SecurityService,
    supplied_key: str | None,
) -> bool:
    if security_service.validate_edge_key(supplied_key, request.url.path):
        return True
    if supplied_key is None:
        return False

    database_manager = getattr(request.app.state, "db", None)
    if database_manager is None:
        return False

    async with database_manager.session_factory() as session:
        statement = select(APIKey).where(APIKey.hashed_key == hash_api_key(supplied_key))
        api_key = (await session.execute(statement)).scalar_one_or_none()

    if api_key is None:
        return False
    if api_key.expires_at is not None and api_key.expires_at <= datetime.now(tz=UTC):
        return False

    paths = api_key.scope.get("paths", []) if isinstance(api_key.scope, dict) else []
    return any(fnmatch(request.url.path, str(path)) for path in paths)
