import asyncio
from collections.abc import Mapping
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_canva_provider, get_db_session, get_report_placement_agent
from app.api.schemas.canva import CanvaReportRequest, CanvaReportResponse
from app.core.config import get_settings
from app.domain.contracts import CanvaDesignProvider, CanvaTemplateDefinition, ReportPlacementAgent
from app.integrations.canva_connect import CanvaConnectError
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemyManualStyleReportRepository,
    SqlAlchemySubmissionRepository,
)
from app.services.canva_template_mapping import (
    build_canva_payload,
    build_sequential_placement_plan,
    template_definition_from_dataset,
)
from app.services.client_assets import list_downloaded_assets
from app.services.manual_report_assets import find_manual_report_image
from app.services.report_placement_agent import ReportPlacementError

router = APIRouter(prefix="/clients", tags=["canva-reports"])
db_session_dependency = Depends(get_db_session)
canva_provider_dependency = Depends(get_canva_provider)
placement_agent_dependency = Depends(get_report_placement_agent)


@router.post(
    "/{client_id}/submissions/{submission_id}/canva-report",
    response_model=CanvaReportResponse,
)
async def create_canva_report(
    client_id: UUID,
    submission_id: UUID,
    payload: CanvaReportRequest,
    session: AsyncSession = db_session_dependency,
    provider: CanvaDesignProvider = canva_provider_dependency,
    placement_agent: ReportPlacementAgent | None = placement_agent_dependency,
) -> CanvaReportResponse:
    client = await SqlAlchemyClientRepository(session).get_by_id(str(client_id))
    submission = await SqlAlchemySubmissionRepository(session).get_by_id(str(submission_id))
    if client is None or submission is None or submission.client_id != str(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission was not found.",
        )

    report = await SqlAlchemyManualStyleReportRepository(session).get_by_submission_id(
        str(submission_id)
    )
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Write the manual report first.",
        )

    settings = get_settings()
    template_id = settings.canva_template_id
    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CANVA_TEMPLATE_ID is not configured.",
        )

    local_assets = await asyncio.to_thread(
        list_downloaded_assets,
        settings.asset_storage_root,
        str(client_id),
    )
    local_asset_paths = [
        asset.path for asset in local_assets if asset.submission_id == str(submission_id)
    ]

    try:
        dataset = await provider.get_template_dataset(template_id)
        template = template_definition_from_dataset(
            template_id,
            dataset,
            source_type=settings.canva_source_type,
        )
        assets_by_key = (
            {
                f"{asset.field_key}:{asset.ordinal}": asset.path
                for asset in local_assets
                if asset.submission_id == str(submission_id)
            }
            if placement_agent is None
            else {}
        )
        for group in _mapping_list(report.content.get("image_groups")):
            selected_keys = group.get("asset_keys", [])
            if not isinstance(selected_keys, list):
                continue
            for asset_key in selected_keys:
                if not isinstance(asset_key, str):
                    continue
                path = await asyncio.to_thread(
                    find_manual_report_image,
                    settings.asset_storage_root,
                    client_id=str(client_id),
                    submission_id=str(submission_id),
                    asset_key=asset_key,
                )
                if path is not None:
                    assets_by_key[asset_key] = path
        if placement_agent is not None:
            plan = await placement_agent.create_plan(
                source_text=_report_source_text(report.content),
                image_groups=_mapping_list(report.content.get("image_groups")),
                template=template,
                assets=assets_by_key,
            )
        else:
            plan = build_sequential_placement_plan(report.content, template, local_asset_paths)
        selected_assets = {
            assignment.field_key: Path(assignment.source_path)
            for assignment in plan.assignments
            if template_field_type(template, assignment.field_key) == "image"
        }
        canva_payload = build_canva_payload(
            report.content,
            template,
            plan,
            asset_paths=selected_assets,
        )
        asset_ids: dict[str, str] = {}
        for field_key, asset_path in canva_payload.asset_paths.items():
            asset_ids[field_key] = await provider.upload_asset(
                local_path=asset_path,
                name=f"{client.id}-{asset_path.name}",
            )
        autofill = await provider.create_autofill_job(
            template=template,
            values=canva_payload.values,
            asset_ids=asset_ids,
        )
        autofill = await _wait_for_autofill(
            provider,
            autofill,
            settings.canva_poll_attempts,
            settings.canva_poll_interval_seconds,
        )
        if autofill.status != "success" or not autofill.design_id:
            raise CanvaConnectError(autofill.error or "Canva could not create the design.")

        export_job_id = None
        pdf_url = None
        if payload.export_pdf:
            export = await provider.create_export_job(design_id=autofill.design_id)
            export = await _wait_for_export(
                provider,
                export,
                settings.canva_poll_attempts,
                settings.canva_poll_interval_seconds,
            )
            if export.status != "success":
                raise CanvaConnectError(export.error or "Canva could not export the PDF.")
            export_job_id = export.job_id
            pdf_url = export.download_url
    except (CanvaConnectError, ReportPlacementError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return CanvaReportResponse(
        status="success",
        autofill_job_id=autofill.job_id,
        design_id=autofill.design_id,
        design_url=autofill.design_url,
        export_job_id=export_job_id,
        pdf_url=pdf_url,
        text_fields_filled=len(canva_payload.values),
        image_fields_filled=len(asset_ids),
    )


async def _wait_for_autofill(
    provider: CanvaDesignProvider,
    job,
    attempts: int,
    interval: float,
):
    for attempt in range(attempts):
        if job.status in {"success", "succeeded", "failed"}:
            return job
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)
            job = await provider.get_autofill_job(job_id=job.job_id)
    return job


async def _wait_for_export(provider: CanvaDesignProvider, job, attempts: int, interval: float):
    for attempt in range(attempts):
        if job.status in {"success", "succeeded", "failed"}:
            return job
        if attempt + 1 < attempts:
            await asyncio.sleep(interval)
            job = await provider.get_export_job(job_id=job.job_id)
    return job


def template_field_type(template: CanvaTemplateDefinition, field_key: str) -> str | None:
    field = next((item for item in template.fields if item.key == field_key), None)
    return field.field_type if field else None


def _string_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def _report_source_text(content: Mapping[str, object]) -> str:
    blocks = _mapping_list(content.get("content_blocks"))
    block_text = "\n\n".join(
        f"{_string_value(block.get('title'))}\n{_string_value(block.get('text'))}".strip()
        for block in blocks
        if _string_value(block.get("text")).strip()
    )
    return block_text or _string_value(content.get("source_text"))


def _mapping_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
