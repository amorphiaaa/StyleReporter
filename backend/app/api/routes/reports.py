from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import AgentsSdkStyleReportRuntime
from app.agents.style_methodologist import StubStyleReportRuntime
from app.api.dependencies import get_db_session
from app.api.schemas.reports import GenerateStyleReportRequest, StyleReportResponse
from app.core.config import get_settings
from app.domain.contracts import StyleReportRequest, StyleReportRun
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemyStyleReportRunRepository,
    SqlAlchemySubmissionRepository,
)

router = APIRouter(tags=["reports"])
db_session_dependency = Depends(get_db_session)


@router.post(
    "/clients/{client_id}/reports",
    response_model=StyleReportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_style_report(
    client_id: UUID,
    payload: GenerateStyleReportRequest,
    session: AsyncSession = db_session_dependency,
) -> StyleReportResponse:
    client = await SqlAlchemyClientRepository(session).get_by_id(str(client_id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} was not found.",
        )

    submission = await SqlAlchemySubmissionRepository(session).get_by_id(str(payload.submission_id))
    if submission is None or submission.client_id != str(client_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {payload.submission_id} was not found for this client.",
        )

    now = datetime.now(UTC)
    report_run = StyleReportRun(
        id=str(uuid4()),
        client_id=str(client_id),
        submission_id=str(payload.submission_id),
        status="running",
        runtime_type=payload.runtime,
        report_version="pending",
        started_at=now,
    )
    repository = SqlAlchemyStyleReportRunRepository(session)

    try:
        await repository.save(report_run)
        generated = await _build_runtime(payload.runtime).generate(
            StyleReportRequest(
                client_id=str(client_id),
                submission_id=str(payload.submission_id),
                raw_payload=submission.raw_payload,
            )
        )
        completed_at = datetime.now(UTC)
        report_run = StyleReportRun(
            id=report_run.id,
            client_id=report_run.client_id,
            submission_id=report_run.submission_id,
            status="completed",
            runtime_type=generated.runtime_type,
            report_version=generated.report_version,
            report=generated.content,
            created_at=report_run.created_at,
            started_at=now,
            completed_at=completed_at,
        )
        await repository.save(report_run)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    persisted = await repository.get_by_id(report_run.id)
    if persisted is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated report could not be loaded after persistence.",
        )
    return _to_response(persisted)


@router.get("/reports/{report_run_id}", response_model=StyleReportResponse)
async def get_style_report(
    report_run_id: UUID,
    session: AsyncSession = db_session_dependency,
) -> StyleReportResponse:
    report_run = await SqlAlchemyStyleReportRunRepository(session).get_by_id(str(report_run_id))
    if report_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Style report run {report_run_id} was not found.",
        )
    return _to_response(report_run)


def _build_runtime(runtime_type: str):
    if runtime_type == "agents_sdk_dry_run":
        settings = get_settings()
        return AgentsSdkStyleReportRuntime(
            model=settings.openai_model,
            api_key_configured=bool(settings.openai_api_key),
            dry_run=True,
        )
    return StubStyleReportRuntime()


@router.get("/clients/{client_id}/reports", response_model=list[StyleReportResponse])
async def list_client_style_reports(
    client_id: UUID,
    session: AsyncSession = db_session_dependency,
) -> list[StyleReportResponse]:
    client = await SqlAlchemyClientRepository(session).get_by_id(str(client_id))
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client {client_id} was not found.",
        )

    report_runs = await SqlAlchemyStyleReportRunRepository(session).list_by_client_id(
        str(client_id)
    )
    return [_to_response(report_run) for report_run in report_runs]


def _to_response(report_run: StyleReportRun) -> StyleReportResponse:
    return StyleReportResponse(
        id=UUID(report_run.id),
        client_id=UUID(report_run.client_id),
        submission_id=UUID(report_run.submission_id),
        status=report_run.status,
        runtime_type=report_run.runtime_type,
        report_version=report_run.report_version,
        report=dict(report_run.report) if report_run.report is not None else None,
        error_message=report_run.error_message,
        created_at=report_run.created_at,
        started_at=report_run.started_at,
        completed_at=report_run.completed_at,
    )
