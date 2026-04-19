from __future__ import annotations

from io import BytesIO
from typing import Any, Protocol, cast

from argus.core.config import Settings


class _MinioClient(Protocol):
    def bucket_exists(self, bucket_name: str) -> bool: ...

    def make_bucket(self, bucket_name: str) -> None: ...

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BytesIO,
        *,
        length: int,
        content_type: str,
    ) -> Any: ...

    def presigned_get_object(self, bucket_name: str, object_name: str) -> str: ...


class MinioObjectStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client: _MinioClient | None = None

    async def put_object(self, *, key: str, data: bytes, content_type: str) -> str:
        client = self._get_client()
        bucket = self.settings.minio_incidents_bucket
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        payload = BytesIO(data)
        client.put_object(
            bucket,
            key,
            payload,
            length=len(data),
            content_type=content_type,
        )
        return client.presigned_get_object(bucket, key)

    def _get_client(self) -> _MinioClient:
        if self._client is None:
            from minio import Minio

            self._client = cast(
                _MinioClient,
                Minio(
                    self.settings.minio_endpoint,
                    access_key=self.settings.minio_access_key,
                    secret_key=self.settings.minio_secret_key.get_secret_value(),
                    secure=self.settings.minio_secure,
                ),
            )
        return self._client
