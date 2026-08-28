from pathlib import Path

import httpx
import pytest

from app.domain.contracts import CanvaTemplateDefinition
from app.integrations.canva_connect import CanvaConnectProvider


@pytest.mark.asyncio
async def test_canva_connect_provider_runs_dataset_upload_autofill_and_export(
    tmp_path: Path,
) -> None:
    asset = tmp_path / "portrait.jpg"
    asset.write_bytes(b"image-bytes")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path.endswith("/brand-templates/template-1/dataset"):
            return httpx.Response(
                200,
                json={
                    "dataset": {
                        "field_001": {"type": "text"},
                        "image_001": {"type": "image"},
                    }
                },
                request=request,
            )
        if request.method == "POST" and path.endswith("/asset-uploads"):
            return httpx.Response(
                200,
                json={"job": {"id": "upload-1", "status": "in_progress"}},
                request=request,
            )
        if request.method == "GET" and path.endswith("/asset-uploads/upload-1"):
            return httpx.Response(
                200,
                json={
                    "job": {
                        "id": "upload-1",
                        "status": "success",
                        "asset": {"id": "asset-1"},
                    }
                },
                request=request,
            )
        if request.method == "POST" and path.endswith("/autofills"):
            return httpx.Response(
                200,
                json={"job": {"id": "autofill-1", "status": "in_progress"}},
                request=request,
            )
        if request.method == "GET" and path.endswith("/autofills/autofill-1"):
            return httpx.Response(
                200,
                json={
                    "job": {
                        "id": "autofill-1",
                        "status": "success",
                        "result": {
                            "design": {
                                "id": "design-1",
                                "url": "https://canva.example/design-1/edit",
                            }
                        },
                    }
                },
                request=request,
            )
        if request.method == "POST" and path.endswith("/exports"):
            return httpx.Response(
                200,
                json={"job": {"id": "export-1", "status": "in_progress"}},
                request=request,
            )
        if request.method == "GET" and path.endswith("/exports/export-1"):
            return httpx.Response(
                200,
                json={
                    "job": {
                        "id": "export-1",
                        "status": "success",
                        "urls": ["https://canva.example/export.pdf"],
                    }
                },
                request=request,
            )
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider = CanvaConnectProvider(
            access_token="test-token",
            base_url="https://api.canva.test/rest/v1",
            poll_interval_seconds=0,
            poll_attempts=2,
            client=client,
        )
        dataset = await provider.get_template_dataset("template-1")
        asset_id = await provider.upload_asset(local_path=asset, name="portrait.jpg")
        job = await provider.create_autofill_job(
            template=CanvaTemplateDefinition(
                key="template-1",
                version="live",
                brand_template_id="template-1",
                pages=(),
                fields=(),
            ),
            values={"field_001": "Report"},
            asset_ids={"image_001": asset_id},
        )
        job = await provider.get_autofill_job(job_id=job.job_id)
        export = await provider.create_export_job(design_id=job.design_id or "")
        export = await provider.get_export_job(job_id=export.job_id)

    assert dataset == {"field_001": "text", "image_001": "image"}
    assert asset_id == "asset-1"
    assert job.design_url == "https://canva.example/design-1/edit"
    assert export.download_url == "https://canva.example/export.pdf"
