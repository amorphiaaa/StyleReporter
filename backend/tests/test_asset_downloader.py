from pathlib import Path

import httpx
import pytest

from app.integrations.asset_downloader import HttpAssetDownloader
from app.integrations.google_drive import (
    GoogleDriveAssetDownloader,
    extract_google_drive_file_id,
)


@pytest.mark.asyncio
async def test_http_asset_downloader_writes_image_and_checksum(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "image/jpeg"},
            content=b"synthetic-jpeg",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await HttpAssetDownloader(client=client).download(
            source_url="https://example.test/photo",
            destination_stem=tmp_path / "01",
        )

    assert result.status == "downloaded"
    assert result.filename == "01.jpg"
    assert result.content_type == "image/jpeg"
    assert result.size_bytes == len(b"synthetic-jpeg")
    assert (tmp_path / "01.jpg").read_bytes() == b"synthetic-jpeg"
    assert result.sha256


@pytest.mark.asyncio
async def test_http_asset_downloader_rejects_non_image_response(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            content=b"not an image",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await HttpAssetDownloader(client=client).download(
            source_url="https://example.test/photo",
            destination_stem=tmp_path / "01",
        )

    assert result.status == "download_failed"
    assert "supported image" in (result.error or "")
    assert not (tmp_path / "01.jpg").exists()


def test_google_drive_file_id_parser_supports_common_form_upload_links() -> None:
    assert extract_google_drive_file_id(
        "https://drive.google.com/file/d/file-123/view"
    ) == "file-123"
    assert extract_google_drive_file_id("https://drive.google.com/open?id=file-456") == "file-456"
    assert extract_google_drive_file_id("https://example.test/photo.jpg") is None


@pytest.mark.asyncio
async def test_google_drive_downloader_uses_read_only_token(tmp_path: Path) -> None:
    class TokenProvider:
        async def get_access_token(self) -> str:
            return "synthetic-token"

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        assert request.url.path.endswith("/file-789")
        assert request.url.params["alt"] == "media"
        return httpx.Response(
            200,
            headers={"content-type": "image/png"},
            content=b"synthetic-png",
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await GoogleDriveAssetDownloader(
            access_token_provider=TokenProvider(),
            client=client,
        ).download(
            source_url="https://drive.google.com/file/d/file-789/view",
            destination_stem=tmp_path / "01",
        )

    assert result.status == "downloaded"
    assert (tmp_path / "01.png").read_bytes() == b"synthetic-png"
