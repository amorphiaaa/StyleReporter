from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.manual_reports import ManualStyleReportContent, ManualStyleReportResponse
from app.domain.contracts import ManualStyleReport
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemyManualStyleReportRepository,
    SqlAlchemySubmissionRepository,
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
