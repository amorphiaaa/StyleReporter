import asyncio
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.manual_reports import (
    ManualReportImage,
    ManualStyleReportContent,
    ManualStyleReportResponse,
)
from app.core.config import get_settings
from app.domain.contracts import ManualStyleReport
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemyManualStyleReportRepository,
    SqlAlchemySubmissionRepository,
)
from app.services.manual_report_assets import (
    SUPPORTED_IMAGE_TYPES,
    find_manual_report_image,
    manual_report_image_directory,
)

router = APIRouter(prefix="/clients", tags=["manual-reports"])
db_session_dependency = Depends(get_db_session)


@router.get(
    "/{client_id}/submissions/{submission_id}/manual-report",
    response_model=ManualStyleReportResponse | None,
)
async def get_manual_style_report(
    client_id: UUID,
    submission_id: UUID,
    session: AsyncSession = db_session_dependency,
) -> ManualStyleReportResponse | None:
    await _require_submission(session, client_id, submission_id)
    report = await SqlAlchemyManualStyleReportRepository(session).get_by_submission_id(
        str(submission_id)
    )
    return _to_response(report) if report else None


@router.put(
    "/{client_id}/submissions/{submission_id}/manual-report",
    response_model=ManualStyleReportResponse,
)
async def save_manual_style_report(
    client_id: UUID,
    submission_id: UUID,
    payload: ManualStyleReportContent,
    session: AsyncSession = db_session_dependency,
) -> ManualStyleReportResponse:
    await _require_submission(session, client_id, submission_id)
    repository = SqlAlchemyManualStyleReportRepository(session)
    existing = await repository.get_by_submission_id(str(submission_id))
    report = ManualStyleReport(
        id=existing.id if existing else str(uuid4()),
        client_id=str(client_id),
        submission_id=str(submission_id),
        content=payload.model_dump(mode="json"),
        created_at=existing.created_at if existing else None,
        updated_at=existing.updated_at if existing else None,
    )
    try:
        saved = await repository.save(report)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return _to_response(saved)


@router.post(
    "/{client_id}/submissions/{submission_id}/manual-report/images",
    response_model=ManualReportImage,
)
async def upload_manual_report_image(
    client_id: UUID,
    submission_id: UUID,
    request: Request,
    filename: str = Query(min_length=1, max_length=255),
    session: AsyncSession = db_session_dependency,
) -> ManualReportImage:
    await _require_submission(session, client_id, submission_id)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    suffix = SUPPORTED_IMAGE_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only JPEG, PNG, WebP, and GIF images are supported.",
        )
    content = await request.body()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is empty.")
    if len(content) > get_settings().asset_download_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image is too large.",
        )

    asset_key = f"manual-{uuid4().hex}"
    directory = manual_report_image_directory(
        get_settings().asset_storage_root,
        str(client_id),
        str(submission_id),
    )
    path = directory / f"{asset_key}{suffix}"
    await asyncio.to_thread(_write_image, path, content)
    return ManualReportImage(
        asset_key=asset_key,
        filename=filename,
        url=(
            f"/api/v1/clients/{client_id}/submissions/{submission_id}/manual-report/images/"
            f"{asset_key}"
        ),
    )


@router.get(
    "/{client_id}/submissions/{submission_id}/manual-report/images/{asset_key}",
    response_class=FileResponse,
    include_in_schema=False,
)
async def get_manual_report_image(
    client_id: UUID,
    submission_id: UUID,
    asset_key: str,
) -> FileResponse:
    path = await asyncio.to_thread(
        find_manual_report_image,
        get_settings().asset_storage_root,
        client_id=str(client_id),
        submission_id=str(submission_id),
        asset_key=asset_key,
    )
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image was not found.")
    return FileResponse(path)


async def _require_submission(
    session: AsyncSession,
    client_id: UUID,
    submission_id: UUID,
) -> None:
    client = await SqlAlchemyClientRepository(session).get_by_id(str(client_id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} was not found.",
        )
    submission = await SqlAlchemySubmissionRepository(session).get_by_id(str(submission_id))
    if submission is None or submission.client_id != str(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} was not found for this client.",
        )


def _to_response(report: ManualStyleReport) -> ManualStyleReportResponse:
    return ManualStyleReportResponse(
        id=UUID(report.id),
        client_id=UUID(report.client_id),
        submission_id=UUID(report.submission_id),
        content=dict(report.content),
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


def _write_image(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
