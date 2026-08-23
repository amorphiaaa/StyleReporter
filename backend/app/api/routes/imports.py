from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session
from app.api.schemas.imports import (
    GoogleSheetsSyncRequest,
    ImportErrorResponse,
    ImportHistoryItem,
    ImportResponse,
    ImportRunResponse,
    ManualImportRequest,
)
from app.core.config import get_settings
from app.db.models import ImportRun
from app.domain.contracts import GoogleSheetsSource, ImportRequest, ImportResult, SheetReadRequest
from app.integrations.asset_downloader import HttpAssetDownloader
from app.integrations.google_drive import GoogleDriveAssetDownloader
from app.integrations.google_drive_storage import (
    GoogleDriveStorageConfigurationError,
    GoogleDriveStorageError,
    GoogleDriveWorkspacePublisher,
)
from app.integrations.google_sheets import (
    GoogleSheetsApiError,
    GoogleSheetsApiSource,
    GoogleSheetsAuthenticationError,
    GoogleSheetsConfigurationError,
)
from app.integrations.inline_rows import InlineRowsSource
from app.repositories.sqlalchemy import (
    SqlAlchemyClientRepository,
    SqlAlchemySubmissionRepository,
)
from app.services.asset_workspace import LocalAssetWorkspace
from app.services.questionnaire_importer import QuestionnaireImportService

router = APIRouter(prefix="/imports", tags=["imports"])
db_session_dependency = Depends(get_db_session)


@router.get("", response_model=list[ImportHistoryItem])
async def list_imports(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = db_session_dependency,
) -> list[ImportHistoryItem]:
    result = await session.execute(
        select(ImportRun).order_by(ImportRun.started_at.desc()).limit(limit)
    )
    return [_to_import_history_item(import_run) for import_run in result.scalars().all()]


@router.post("/manual", response_model=ImportResponse, status_code=status.HTTP_201_CREATED)
async def manual_import(
    payload: ManualImportRequest,
    session: AsyncSession = db_session_dependency,
) -> ImportResponse:
    import_id = uuid4()
    return await _run_import(
        request=payload.to_domain(import_id),
        source=InlineRowsSource(payload.rows_to_domain()),
        session=session,
    )


@router.post(
    "/google-sheets/sync",
    response_model=ImportResponse,
    status_code=status.HTTP_201_CREATED,
)
async def sync_google_sheets(
    payload: GoogleSheetsSyncRequest | None = None,
    session: AsyncSession = db_session_dependency,
) -> ImportResponse:
    settings = get_settings()
    if not settings.google_sheets_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Google Sheets sync is disabled. Set GOOGLE_SHEETS_ENABLED=true "
                "after configuring service-account credentials."
            ),
        )
    if not settings.google_service_account_json:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sheets sync requires GOOGLE_SERVICE_ACCOUNT_JSON.",
        )

    request_payload = payload or GoogleSheetsSyncRequest()
    spreadsheet_id = request_payload.spreadsheet_id or settings.google_spreadsheet_id
    if not spreadsheet_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sheets sync requires GOOGLE_SPREADSHEET_ID.",
        )
    sheet_name = request_payload.sheet_name or settings.google_sheet_name
    try:
        source = GoogleSheetsApiSource.from_service_account_json(
            settings.google_service_account_json,
            timeout_seconds=settings.google_sheets_timeout_seconds,
        )
    except GoogleSheetsConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    import_id = uuid4()
    return await _run_import(
        request=ImportRequest(
            source=SheetReadRequest(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name,
                cell_range=request_payload.cell_range or settings.google_sheet_range,
            ),
            email_header=request_payload.email_header,
            display_name_header=request_payload.display_name_header,
            timestamp_header=request_payload.timestamp_header,
            source_type=request_payload.source_type,
            questionnaire_version=(
                request_payload.questionnaire_version or settings.google_questionnaire_version
            ),
            refresh_existing=request_payload.refresh_existing or settings.google_refresh_existing,
            import_id=str(import_id),
        ),
        source=source,
        session=session,
    )


async def _run_import(
    *,
    request: ImportRequest,
    source: GoogleSheetsSource,
    session: AsyncSession,
) -> ImportResponse:
    settings = get_settings()
    import_id = UUID(request.import_id) if request.import_id else uuid4()
    import_run = ImportRun(
        id=import_id,
        source_type=request.source_type,
        source_spreadsheet_id=request.source.spreadsheet_id,
        source_sheet_name=request.source.sheet_name,
        status="running",
        row_errors=[],
    )
    session.add(import_run)

    try:
        await session.flush()
        importer = QuestionnaireImportService(
            source=source,
            clients=SqlAlchemyClientRepository(session),
            submissions=SqlAlchemySubmissionRepository(session),
            assets=(
                LocalAssetWorkspace(
                    settings.asset_storage_root,
                    downloader=_build_asset_downloader(settings),
                )
                if settings.asset_storage_enabled
                else None
            ),
            publisher=_build_asset_publisher(settings),
        )
        result = await importer.import_rows(request)
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
    except GoogleSheetsAuthenticationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleSheetsApiError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Sheets API request failed: {exc.detail}",
        ) from exc
    except GoogleDriveStorageConfigurationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except GoogleDriveStorageError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except Exception:
        await session.rollback()
        raise

    return _to_import_response(result)


def _build_asset_downloader(settings):
    if not settings.asset_download_enabled:
        return None

    fallback = HttpAssetDownloader(
        timeout_seconds=settings.asset_download_timeout_seconds,
        max_bytes=settings.asset_download_max_bytes,
    )
    oauth_values = (
        settings.google_drive_oauth_client_json,
        settings.google_drive_oauth_refresh_token,
    )
    if any(oauth_values) and not all(oauth_values):
        raise GoogleDriveStorageConfigurationError(
            "Google Drive downloads require both GOOGLE_DRIVE_OAUTH_CLIENT_JSON "
            "and GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN."
        )
    if all(oauth_values):
        return GoogleDriveAssetDownloader.from_oauth(
            settings.google_drive_oauth_client_json,
            settings.google_drive_oauth_refresh_token,
            timeout_seconds=settings.asset_download_timeout_seconds,
            max_bytes=settings.asset_download_max_bytes,
        )
    if not settings.google_service_account_json:
        return fallback

    try:
        return GoogleDriveAssetDownloader.from_service_account_json(
            settings.google_service_account_json,
            timeout_seconds=settings.asset_download_timeout_seconds,
            max_bytes=settings.asset_download_max_bytes,
        )
    except GoogleSheetsConfigurationError:
        return fallback


def _build_asset_publisher(settings):
    if not settings.google_drive_storage_enabled:
        return None
    if not settings.asset_storage_enabled:
        raise GoogleDriveStorageConfigurationError(
            "Google Drive storage requires ASSET_STORAGE_ENABLED=true."
        )
    if not settings.google_drive_root_folder_id:
        raise GoogleDriveStorageConfigurationError(
            "Google Drive storage requires GOOGLE_DRIVE_ROOT_FOLDER_ID."
        )
    oauth_values = (
        settings.google_drive_oauth_client_json,
        settings.google_drive_oauth_refresh_token,
    )
    if any(oauth_values) and not all(oauth_values):
        raise GoogleDriveStorageConfigurationError(
            "Google Drive storage requires both GOOGLE_DRIVE_OAUTH_CLIENT_JSON "
            "and GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN."
        )
    if all(oauth_values):
        return GoogleDriveWorkspacePublisher.from_oauth(
            settings.google_drive_oauth_client_json,
            settings.google_drive_oauth_refresh_token,
            root_folder_id=settings.google_drive_root_folder_id,
            local_root=settings.asset_storage_root,
            timeout_seconds=settings.google_drive_timeout_seconds,
        )
    if not settings.google_service_account_json:
        raise GoogleDriveStorageConfigurationError(
            "Google Drive storage requires OAuth credentials. Set "
            "GOOGLE_DRIVE_OAUTH_CLIENT_JSON and GOOGLE_DRIVE_OAUTH_REFRESH_TOKEN."
        )
    return GoogleDriveWorkspacePublisher.from_service_account_json(
        settings.google_service_account_json,
        root_folder_id=settings.google_drive_root_folder_id,
        local_root=settings.asset_storage_root,
        timeout_seconds=settings.google_drive_timeout_seconds,
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

    return _to_import_run_response(import_run)


def _to_import_run_response(import_run: ImportRun) -> ImportRunResponse:
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


def _to_import_history_item(import_run: ImportRun) -> ImportHistoryItem:
    return ImportHistoryItem(
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
        row_errors_count=len(import_run.row_errors or []),
        started_at=import_run.started_at,
        completed_at=import_run.completed_at,
    )
