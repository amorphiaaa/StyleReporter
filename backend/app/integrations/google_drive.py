"""Read-only Google Drive downloader for Form upload URLs."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import httpx

from app.domain.contracts import AssetDownloader, AssetDownloadResult
from app.integrations.asset_downloader import (
    MAX_DEFAULT_BYTES,
    HttpAssetDownloader,
    _failed,
    _save_response,
)
from app.integrations.google_sheets import (
    GoogleAccessTokenProvider,
    GoogleSheetsConfigurationError,
    ServiceAccountAccessTokenProvider,
)

GOOGLE_DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
_DRIVE_FILE_ID_PATTERN = re.compile(r"/file/d/([A-Za-z0-9_-]+)")


class GoogleDriveAssetDownloader(AssetDownloader):
    """Download Drive file IDs with a service-account token.

    Non-Drive URLs are delegated to the public HTTP downloader, which keeps
    direct image links useful without coupling the workspace to Google.
    """

    def __init__(
        self,
        *,
        access_token_provider: GoogleAccessTokenProvider,
        fallback: HttpAssetDownloader | None = None,
        timeout_seconds: float = 30.0,
        max_bytes: int = MAX_DEFAULT_BYTES,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token_provider = access_token_provider
        self.fallback = fallback or HttpAssetDownloader(
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.client = client

    @classmethod
    def from_service_account_json(
        cls,
        service_account_json: str,
        *,
        timeout_seconds: float = 30.0,
        max_bytes: int = MAX_DEFAULT_BYTES,
    ) -> GoogleDriveAssetDownloader:
        try:
            provider = ServiceAccountAccessTokenProvider(
                service_account_json,
                scopes=(GOOGLE_DRIVE_READONLY_SCOPE,),
            )
        except GoogleSheetsConfigurationError:
            raise
        return cls(
            access_token_provider=provider,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )

    async def download(
        self,
        *,
        source_url: str,
        destination_stem: Path,
    ) -> AssetDownloadResult:
        file_id = extract_google_drive_file_id(source_url)
        if file_id is None:
            return await self.fallback.download(
                source_url=source_url,
                destination_stem=destination_stem,
            )

        try:
            token = await self.access_token_provider.get_access_token()
            url = f"{GOOGLE_DRIVE_FILES_URL}/{quote(file_id, safe='')}"
            headers = {"Authorization": f"Bearer {token}"}
            if self.client is not None:
                response = await self.client.get(
                    url,
                    headers=headers,
                    params={"alt": "media"},
                    follow_redirects=True,
                    timeout=self.timeout_seconds,
                )
                return await _save_response(
                    response,
                    destination_stem=destination_stem,
                    max_bytes=self.max_bytes,
                )

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    url,
                    headers=headers,
                    params={"alt": "media"},
                    follow_redirects=True,
                )
            return await _save_response(
                response,
                destination_stem=destination_stem,
                max_bytes=self.max_bytes,
            )
        except httpx.HTTPError as exc:
            return _failed(f"Google Drive download failed: {type(exc).__name__}.")
        except Exception:
            return _failed("Google Drive authentication failed.")


def extract_google_drive_file_id(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        return None

    match = _DRIVE_FILE_ID_PATTERN.search(parsed.path)
    if match:
        return match.group(1)

    query_id = parse_qs(parsed.query).get("id", [None])[0]
    if query_id and parsed.netloc.endswith("google.com"):
        return query_id
    return None
