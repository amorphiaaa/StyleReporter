from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.imports import (
    ImportErrorResponse,
    ImportResponse,
    ImportRunResponse,
    ManualImportRequest,
)
from app.db.models import ImportRun
from app.domain.contracts import ImportResult
from app.integrations.inline_rows import InlineRowsSource
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemySubmissionRepository,
)
from app.services.questionnaire_importer import QuestionnaireImportService

router = APIRouter(prefix="/imports", tags=["imports"])
db_session_dependency = Depends(get_db_session)


@router.post("/manual", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
async def manual_import(
    payload: ManualImportRequest,
    session: AsyncSession = db_session_dependency,
) -> ImportResponse:
    import_id = uuid4()
    import_run = ImportRun(
        id=import_id,
        source_type=payload.source_type,
        source_spreadsheet_id=payload.spreadsheet_id,
        source_sheet_name=payload.sheet_name,
        status="running",
        row_errors=[],
    )
    session.add(import_run)

    try:
        await session.flush()
        importer = QuestionnaireImportService(
            source=InlineRowsSource(payload.rows_to_domain()),
            clients=SqlAlchemyClientRepository(session),
            submissions=SqlAlchemySubmissionRepository(session),
        )
        result = await importer.import_rows(payload.to_domain(import_id))
        import_run.status = "completed"
        import_run.rows_seen = result.rows_seen
        import_run.created_clients = result.created_clients
        import_run.updated_clients = result.updated_clients
        import_run.created_submissions = result.created_submissions
        import_run.rejected_rows = result.rejected_rows
        import_run.skipped_duplicates = result.skipped_duplicates
        import_run.row_errors = [
            {
                "row_number": error.row_number,
                "code": error.code,
                "message": error.message,
            }
            for error in result.errors
        ]
        import_run.completed_at = datetime.now(UTC)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    return _to_import_response(result)


@router.post("/google-sheets/sync")
async def sync_google_sheets() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Google Sheets import is not implemented in the scaffold.",
    )


@router.get("/{import_id}", response_model=ImportRunResponse)
async def get_import(
    import_id: UUID,
    session: AsyncSession = db_session_dependency,
) -> ImportRunResponse:
    import_run = await session.get(ImportRun, import_id)
    if import_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import run {import_id} was not found.",
        )

    return ImportRunResponse(
        import_id=import_run.id,
        source_type=import_run.source_type,
        spreadsheet_id=import_run.source_spreadsheet_id,
        sheet_name=import_run.source_sheet_name,
        status=import_run.status,
        rows_seen=import_run.rows_seen,
        created_clients=import_run.created_clients,
        updated_clients=import_run.updated_clients,
        created_submissions=import_run.created_submissions,
        rejected_rows=import_run.rejected_rows,
        skipped_duplicates=import_run.skipped_duplicates,
        row_errors=[ImportErrorResponse(**error) for error in (import_run.row_errors or [])],
        started_at=import_run.started_at,
        completed_at=import_run.completed_at,
    )


def _to_import_response(result: ImportResult) -> ImportResponse:
    return ImportResponse(
        import_id=UUID(result.import_id),
        rows_seen=result.rows_seen,
        created_clients=result.created_clients,
        updated_clients=result.updated_clients,
        created_submissions=result.created_submissions,
        rejected_rows=result.rejected_rows,
        skipped_duplicates=result.skipped_duplicates,
        errors=[
            ImportErrorResponse(
                row_number=error.row_number,
                code=error.code,
                message=error.message,
            )
            for error in result.errors
        ],
    )
