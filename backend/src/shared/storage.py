"""Pluggable blob storage — filesystem (default) or S3-compatible.

Generated documents (and avatars) used to be written straight to the local
filesystem inside the renderer / photo module, which meant they were lost on
every redeploy of an ephemeral container. This module puts a small async port
in front of that so the backend can target durable object storage in prod
(`STORAGE_PROVIDER=s3`) while staying on the local disk for dev/tests.

Keys are relative POSIX-ish paths like ``"<user_id>/<uuid>.pdf"``. The
filesystem adapter also accepts *absolute* paths so documents rendered before
this refactor (whose `pdf_path` is an absolute filesystem path) keep working.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Protocol

import structlog

from src.shared.config import get_settings

logger = structlog.get_logger(__name__)


class StoragePort(Protocol):
    async def save(self, key: str, content: bytes, *, content_type: str | None = None) -> None: ...
    async def read(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def exists(self, key: str) -> bool: ...


class FilesystemStorageAdapter:
    """Stores blobs under ``storage_root``. Backward-compatible with absolute
    paths persisted before the storage abstraction existed."""

    def __init__(self, root: Path) -> None:
        self._root = Path(root)

    def _resolve(self, key: str) -> Path:
        p = Path(key)
        return p if p.is_absolute() else self._root / key

    async def save(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
        path = self._resolve(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        await asyncio.to_thread(_write)

    async def read(self, key: str) -> bytes:
        return await asyncio.to_thread(self._resolve(key).read_bytes)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(lambda: self._resolve(key).unlink(missing_ok=True))

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._resolve(key).exists)


class S3StorageAdapter:
    """S3-compatible object storage via aioboto3 (lazy-imported so the wheel is
    only required when ``storage_provider=s3``)."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        prefix: str = "",
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._prefix = prefix.strip("/")
        self._endpoint_url = endpoint_url
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key

    def _full_key(self, key: str) -> str:
        key = key.lstrip("/")
        return f"{self._prefix}/{key}" if self._prefix else key

    def _client(self):  # type: ignore[no-untyped-def]
        import aioboto3

        session = aioboto3.Session()
        return session.client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
            aws_access_key_id=self._access_key_id,
            aws_secret_access_key=self._secret_access_key,
        )

    async def save(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
        async with self._client() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=self._full_key(key),
                Body=content,
                ContentType=content_type or "application/octet-stream",
            )

    async def read(self, key: str) -> bytes:
        from botocore.exceptions import ClientError

        async with self._client() as s3:
            try:
                obj = await s3.get_object(Bucket=self._bucket, Key=self._full_key(key))
            except ClientError as exc:
                err = exc.response.get("Error", {})
                status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if err.get("Code") in ("404", "NoSuchKey", "NotFound") or status == 404:
                    # Port contract: missing key -> FileNotFoundError, same as
                    # the filesystem adapter, so callers map it to a 404.
                    raise FileNotFoundError(key) from exc
                raise
            async with obj["Body"] as stream:
                return await stream.read()

    async def delete(self, key: str) -> None:
        async with self._client() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=self._full_key(key))

    async def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        async with self._client() as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=self._full_key(key))
                return True
            except ClientError as exc:
                err = exc.response.get("Error", {})
                code = err.get("Code")
                status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
                if code in ("404", "NoSuchKey", "NotFound") or status == 404:
                    return False
                # A 403/AccessDenied, wrong bucket, throttle or 5xx is NOT a
                # "missing object" — re-raise (and log) so the failure is
                # visible instead of masquerading as a 404 / empty avatar.
                logger.error(
                    "s3_head_object_failed",
                    bucket=self._bucket,
                    key=self._full_key(key),
                    code=code,
                    status=status,
                )
                raise


@lru_cache(maxsize=1)
def get_storage() -> StoragePort:
    """Pick the storage backend from settings (cached for the process)."""
    settings = get_settings()
    if settings.storage_provider == "s3":
        if not settings.s3_bucket:
            # Fail loud at first use rather than silently writing nowhere.
            raise RuntimeError(
                "storage_provider=s3 but S3_BUCKET is not configured"
            )
        logger.info("storage_backend", provider="s3", bucket=settings.s3_bucket)
        return S3StorageAdapter(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            prefix=settings.s3_prefix,
            endpoint_url=settings.s3_endpoint_url,
            access_key_id=settings.s3_access_key_id,
            secret_access_key=settings.s3_secret_access_key,
        )
    return FilesystemStorageAdapter(settings.storage_root)
