"""Provider-neutral HTTP image downloader used by the local asset workspace."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.domain.contracts import AssetDownloader, AssetDownloadResult

MAX_DEFAULT_BYTES = 20 * 1024 * 1024
_CONTENT_TYPE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/heic": ".heic",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
_ALLOWED_EXTENSIONS = frozenset(_CONTENT_TYPE_EXTENSIONS.values())


class HttpAssetDownloader(AssetDownloader):
    """Download public image URLs with size and content-type validation."""

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        max_bytes: int = MAX_DEFAULT_BYTES,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.client = client

    async def download(
        self,
        *,
        source_url: str,
        destination_stem: Path,
    ) -> AssetDownloadResult:
        parsed = urlparse(source_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return _failed("Asset URL must be an absolute HTTP(S) URL.")

        try:
            if self.client is not None:
                response = await self.client.get(
                    source_url,
                    follow_redirects=True,
                    timeout=self.timeout_seconds,
                )
                return await _save_response(
                    response,
                    destination_stem=destination_stem,
                    max_bytes=self.max_bytes,
                )

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(source_url, follow_redirects=True)
            return await _save_response(
                response,
                destination_stem=destination_stem,
                max_bytes=self.max_bytes,
            )
        except httpx.HTTPError as exc:
            return _failed(f"HTTP download failed: {type(exc).__name__}.")


async def _save_response(
    response: httpx.Response,
    *,
    destination_stem: Path,
    max_bytes: int,
) -> AssetDownloadResult:
    if response.is_error:
        return _failed(f"HTTP download returned status {response.status_code}.")

    content = response.content
    if not content:
        return _failed("Downloaded asset is empty.")
    if len(content) > max_bytes:
        return _failed(f"Downloaded asset exceeds the {max_bytes} byte limit.")

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    extension = _extension_for(content_type, response.url.path)
    if extension is None:
        return _failed("Downloaded response is not a supported image type.")

    destination = destination_stem.with_suffix(extension)
    destination.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(destination.write_bytes, content)
    return AssetDownloadResult(
        status="downloaded",
        filename=destination.name,
        content_type=content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _extension_for(content_type: str, path: str) -> str | None:
    if content_type in _CONTENT_TYPE_EXTENSIONS:
        return _CONTENT_TYPE_EXTENSIONS[content_type]
    suffix = Path(urlparse(path).path).suffix.lower()
    return suffix if suffix in _ALLOWED_EXTENSIONS else None


def _failed(message: str) -> AssetDownloadResult:
    return AssetDownloadResult(status="download_failed", error=message)
