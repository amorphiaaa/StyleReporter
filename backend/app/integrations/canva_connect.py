"""HTTP adapter for the Canva Connect Autofill APIs."""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import httpx

from app.domain.contracts import (
    CanvaAutofillJob,
    CanvaDesignProvider,
    CanvaExportJob,
    CanvaFieldType,
    CanvaTemplateDefinition,
)


class CanvaConnectError(RuntimeError):
    """A provider error that is safe to expose as an API failure."""


class CanvaConnectProvider(CanvaDesignProvider):
    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.canva.com/rest/v1",
        timeout_seconds: float = 60.0,
        poll_interval_seconds: float = 1.0,
        poll_attempts: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._access_token = access_token
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._poll_attempts = poll_attempts
        self._client = client

    async def get_template_dataset(self, template_id: str) -> Mapping[str, CanvaFieldType]:
        payload = await self._request("GET", f"/brand-templates/{template_id}/dataset")
        dataset = payload.get("dataset")
        if not isinstance(dataset, Mapping):
            raise CanvaConnectError("Canva returned an invalid template dataset.")
        result: dict[str, CanvaFieldType] = {}
        for key, value in dataset.items():
            if not isinstance(key, str) or not isinstance(value, Mapping):
                continue
            field_type = value.get("type")
            if field_type in ("text", "image"):
                result[key] = field_type
        return result

    async def upload_asset(self, *, local_path: Path, name: str) -> str:
        try:
            content = await asyncio.to_thread(local_path.read_bytes)
        except OSError as exc:
            raise CanvaConnectError(f"Could not read asset {local_path.name}.") from exc

        metadata = {"name_base64": base64.b64encode(name[:50].encode("utf-8")).decode("ascii")}
        payload = await self._request(
            "POST",
            "/asset-uploads",
            content=content,
            headers={
                "Content-Type": "application/octet-stream",
                "Asset-Upload-Metadata": json.dumps(metadata),
            },
        )
        job = _mapping(payload.get("job"))
        job_id = _required_string(job, "id")
        result = await self._poll(
            lambda: self._request("GET", f"/asset-uploads/{job_id}"),
            job_key="job",
        )
        asset = _mapping(result.get("asset"))
        return _required_string(asset, "id")

    async def create_autofill_job(
        self,
        *,
        template: CanvaTemplateDefinition,
        values: Mapping[str, str],
        asset_ids: Mapping[str, str],
    ) -> CanvaAutofillJob:
        if not template.brand_template_id:
            raise CanvaConnectError("CANVA_TEMPLATE_ID is not configured.")
        data: dict[str, dict[str, str]] = {
            key: {"type": "text", "text": value} for key, value in values.items()
        }
        data.update(
            {key: {"type": "image", "asset_id": asset_id} for key, asset_id in asset_ids.items()}
        )
        payload = await self._request(
            "POST",
            "/autofills",
            json={
                "type": "create_from_brand_template",
                "brand_template_id": template.brand_template_id,
                "data": data,
            },
        )
        return _autofill_job(_mapping(payload.get("job")))

    async def get_autofill_job(self, *, job_id: str) -> CanvaAutofillJob:
        payload = await self._request("GET", f"/autofills/{job_id}")
        return _autofill_job(_mapping(payload.get("job")))

    async def create_export_job(self, *, design_id: str, file_type: str = "pdf") -> CanvaExportJob:
        payload = await self._request(
            "POST",
            "/exports",
            json={"design_id": design_id, "format": {"type": file_type}},
        )
        return _export_job(_mapping(payload.get("job")))

    async def get_export_job(self, *, job_id: str) -> CanvaExportJob:
        payload = await self._request("GET", f"/exports/{job_id}")
        return _export_job(_mapping(payload.get("job")))

    async def _poll(self, operation: Any, *, job_key: str) -> Mapping[str, Any]:
        for attempt in range(self._poll_attempts):
            payload = await operation()
            job = _mapping(payload.get(job_key))
            status = job.get("status")
            if status == "success":
                return job
            if status == "failed":
                error = _mapping(job.get("error"))
                raise CanvaConnectError(str(error.get("message") or "Canva job failed."))
            if attempt + 1 < self._poll_attempts:
                await asyncio.sleep(self._poll_interval_seconds)
        raise CanvaConnectError("Canva job did not finish before the timeout.")

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self._access_token}", **kwargs.pop("headers", {})}
        client = self._client
        if client is None:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client_http:
                response = await client_http.request(
                    method, self._base_url + path, headers=headers, **kwargs
                )
        else:
            response = await client.request(
                method, self._base_url + path, headers=headers, **kwargs
            )
        if response.is_error:
            detail = _mapping(response.json()).get("message") if response.content else None
            raise CanvaConnectError(
                detail or f"Canva request failed with HTTP {response.status_code}."
            )
        body = response.json()
        if not isinstance(body, dict):
            raise CanvaConnectError("Canva returned an invalid response.")
        return body


def _autofill_job(job: Mapping[str, Any]) -> CanvaAutofillJob:
    result = _mapping(job.get("result"))
    design = _mapping(result.get("design"))
    urls = _mapping(design.get("urls"))
    design_url = design.get("url") or urls.get("edit_url") or urls.get("view_url")
    error = _mapping(job.get("error"))
    return CanvaAutofillJob(
        job_id=_required_string(job, "id"),
        status=str(job.get("status") or "unknown"),
        design_id=design.get("id") if isinstance(design.get("id"), str) else None,
        design_url=design_url if isinstance(design_url, str) else None,
        error=error.get("message") if isinstance(error.get("message"), str) else None,
    )


def _export_job(job: Mapping[str, Any]) -> CanvaExportJob:
    urls = job.get("urls")
    download_url = urls[0] if isinstance(urls, list) and urls and isinstance(urls[0], str) else None
    error = _mapping(job.get("error"))
    return CanvaExportJob(
        job_id=_required_string(job, "id"),
        status=str(job.get("status") or "unknown"),
        download_url=download_url,
        error=error.get("message") if isinstance(error.get("message"), str) else None,
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _required_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise CanvaConnectError(f"Canva response did not include {key}.")
    return item
